"""Symbol and import graph extractor.

Extracts:
  - Symbols (functions, classes, methods) from Python (ast) and JS/TS (regex)
  - Import edges: which files import which other files

All operations are pure CPU — no I/O, no LLM calls.
Returns lists of Symbol and GraphEdge Pydantic models.
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import PurePosixPath

from app.models.schemas import GraphEdge, SourceFile, Symbol

# ─── Utilities ────────────────────────────────────────────────────────────────

def _symbol_id(repo_id: str, file_path: str, name: str, start_line: int) -> str:
    key = f"{repo_id}:{file_path}:{name}:{start_line}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def _relative_import_to_path(importing_file: str, module: str, repo_root: str = "") -> str | None:
    """Convert a Python relative import to a file path best-guess."""
    if not module:
        return None
    parts = module.split(".")
    base = PurePosixPath(importing_file).parent
    candidate = base / PurePosixPath(*parts)
    return str(candidate) + ".py"


# ─── Python extractor ─────────────────────────────────────────────────────────

def _extract_python(repo_id: str, file: SourceFile) -> tuple[list[Symbol], list[GraphEdge]]:
    symbols: list[Symbol] = []
    edges: list[GraphEdge] = []

    try:
        tree = ast.parse(file.content, filename=file.path)
    except SyntaxError:
        return symbols, edges

    # --- Symbols ---
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = (
                "class" if isinstance(node, ast.ClassDef)
                else "async_function" if isinstance(node, ast.AsyncFunctionDef)
                else "function"
            )
            # Build a simple signature for functions
            signature: str | None = None
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = []
                for arg in node.args.args:
                    args.append(arg.arg)
                prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                signature = f"{prefix} {node.name}({', '.join(args)})"
            elif isinstance(node, ast.ClassDef):
                bases = [ast.unparse(b) for b in node.bases] if node.bases else []
                signature = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"

            sym = Symbol(
                id=_symbol_id(repo_id, file.path, node.name, node.lineno),
                repo_id=repo_id,
                file_path=file.path,
                name=node.name,
                qualified_name=f"{file.path}::{node.name}",
                kind=kind,
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                signature=signature,
                language="python",
            )
            symbols.append(sym)

    # --- Imports (edges) ---
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Absolute import — map to a plausible path
                parts = alias.name.split(".")
                target = "/".join(parts) + ".py"
                edges.append(GraphEdge(
                    source_path=file.path,
                    target_path=target,
                    relationship="imports",
                    line=node.lineno,
                ))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                if node.level and node.level > 0:
                    # Relative import
                    target = _relative_import_to_path(file.path, node.module) or node.module
                else:
                    parts = node.module.split(".")
                    target = "/".join(parts) + ".py"
                edges.append(GraphEdge(
                    source_path=file.path,
                    target_path=target,
                    relationship="imports",
                    line=node.lineno,
                ))

    return symbols, edges


# ─── JavaScript/TypeScript extractor ──────────────────────────────────────────

# Symbol patterns — ordered from most-specific to least-specific
_JS_FUNCTION_PATTERNS = [
    # export default function name(...) / async function name(...)
    re.compile(r"^(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", re.M),
    # export const/let/var name = (...) => / name = function(...)
    re.compile(r"^(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?\(", re.M),
    # shorthand method: name(...) { (inside class bodies)
    re.compile(r"^\s+(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{", re.M),
]

_JS_CLASS_PATTERN = re.compile(
    r"^(?:export\s+(?:default\s+)?)?class\s+([A-Za-z_$][\w$]*)(?:\s+extends\s+\S+)?", re.M
)

# Import patterns for edges
_JS_IMPORT_PATTERNS = [
    # ES module: import ... from '...'
    re.compile(r"""^import\s+.*?from\s+['"]([^'"]+)['"]""", re.M),
    # Dynamic: import('...')
    re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
    # CommonJS: require('...')
    re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
]


def _resolve_js_import(importing_file: str, module_path: str) -> str | None:
    """Resolve a JS/TS import to a relative file path."""
    if not module_path.startswith("."):
        # Node module — keep as-is for graph context
        return module_path
    base = PurePosixPath(importing_file).parent
    resolved = base / module_path
    # Try to add extension if missing
    path_str = str(resolved)
    if not any(path_str.endswith(ext) for ext in (".ts", ".tsx", ".js", ".jsx")):
        # Try .ts first (TypeScript preference)
        return path_str + ".ts"
    return path_str


def _extract_js_ts(repo_id: str, file: SourceFile) -> tuple[list[Symbol], list[GraphEdge]]:
    symbols: list[Symbol] = []
    edges: list[GraphEdge] = []
    file.content.splitlines()

    # --- Classes ---
    for m in _JS_CLASS_PATTERN.finditer(file.content):
        name = m.group(1)
        line_no = file.content[:m.start()].count("\n") + 1
        symbols.append(Symbol(
            id=_symbol_id(repo_id, file.path, name, line_no),
            repo_id=repo_id,
            file_path=file.path,
            name=name,
            qualified_name=f"{file.path}::{name}",
            kind="class",
            start_line=line_no,
            end_line=line_no,
            signature=m.group(0).strip()[:120],
            language=file.language,
        ))

    # --- Functions ---
    seen_names: set[str] = set()
    for pattern in _JS_FUNCTION_PATTERNS:
        for m in pattern.finditer(file.content):
            name = m.group(1)
            if name in seen_names:
                continue
            seen_names.add(name)
            line_no = file.content[:m.start()].count("\n") + 1
            symbols.append(Symbol(
                id=_symbol_id(repo_id, file.path, name, line_no),
                repo_id=repo_id,
                file_path=file.path,
                name=name,
                qualified_name=f"{file.path}::{name}",
                kind="function",
                start_line=line_no,
                end_line=line_no,
                signature=m.group(0).strip()[:120],
                language=file.language,
            ))

    # --- Import edges ---
    for pattern in _JS_IMPORT_PATTERNS:
        for m in pattern.finditer(file.content):
            module_path = m.group(1)
            target = _resolve_js_import(file.path, module_path)
            if target:
                line_no = file.content[:m.start()].count("\n") + 1
                edges.append(GraphEdge(
                    source_path=file.path,
                    target_path=target,
                    relationship="imports",
                    line=line_no,
                ))

    return symbols, edges


# ─── Dispatch ─────────────────────────────────────────────────────────────────

def extract_symbols_and_edges(
    repo_id: str,
    files: list[SourceFile],
) -> tuple[list[Symbol], list[GraphEdge]]:
    """Extract all symbols and import edges from a list of source files.

    Returns (symbols, edges) for the entire repository.
    """
    all_symbols: list[Symbol] = []
    all_edges: list[GraphEdge] = []

    for file in files:
        if file.language == "python":
            syms, eds = _extract_python(repo_id, file)
        elif file.language in ("javascript", "typescript"):
            syms, eds = _extract_js_ts(repo_id, file)
        else:
            syms, eds = [], []

        all_symbols.extend(syms)
        all_edges.extend(eds)

    return all_symbols, all_edges
