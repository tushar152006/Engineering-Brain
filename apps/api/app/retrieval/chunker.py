"""Code chunker — fixed sliding window for most languages; AST-aware for Python.

Python files are split at function and class definition boundaries using the
built-in `ast` module. Each top-level symbol (and class method) becomes its
own chunk. Files that fail to parse fall back to the sliding window.

All other supported file types continue to use a fixed 80-line sliding window
which is simple, language-agnostic, and handles edge cases gracefully.
"""

import ast
import hashlib
import re

from app.models.schemas import Chunk, SourceFile

MAX_CHUNK_LINES = 80
MIN_CHUNK_CHARS = 1


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _stable_chunk_id(repo_id: str, path: str, start_line: int, content: str) -> str:
    digest = hashlib.sha1(f"{repo_id}:{path}:{start_line}:{content}".encode()).hexdigest()
    return digest[:16]


def _title_for_chunk(file: SourceFile, text: str, start_line: int) -> str:
    if file.language == "markdown":
        for line in text.splitlines():
            if line.lstrip().startswith("#"):
                return line.lstrip("# ").strip()[:120]
    match = re.search(
        r"^\s*(?:export\s+)?(?:async\s+)?(?:def|function|class|interface|type)\s+([A-Za-z_][\w]*)",
        text,
        re.MULTILINE,
    )
    if match:
        return match.group(1)
    return f"{file.path}:{start_line}"


def _make_chunk(
    repo_id: str,
    file: SourceFile,
    lines: list[str],
    start_line: int,  # 1-indexed
    title: str,
) -> Chunk | None:
    text = "\n".join(lines).strip()
    if len(text) < MIN_CHUNK_CHARS:
        return None
    end_line = start_line + len(lines) - 1
    chunk_type = "docs" if file.language in {"markdown", "text"} else "code"
    return Chunk(
        id=_stable_chunk_id(repo_id, file.path, start_line, text),
        repo_id=repo_id,
        file_path=file.path,
        language=file.language,
        chunk_type=chunk_type,
        title=title,
        content=text,
        start_line=start_line,
        end_line=end_line,
        token_estimate=_estimate_tokens(text),
    )


# ---------------------------------------------------------------------------
# Python AST-aware chunker
# ---------------------------------------------------------------------------

def _python_chunks(repo_id: str, file: SourceFile) -> list[Chunk] | None:
    """Parse the file with ast.parse and create one chunk per top-level symbol.

    Returns None if parsing fails so the caller can fall back to sliding window.
    """
    try:
        tree = ast.parse(file.content, filename=file.path)
    except SyntaxError:
        return None

    all_lines = file.content.splitlines()
    chunks: list[Chunk] = []

    # Collect top-level definitions (functions and classes)
    top_level: list[ast.stmt] = [
        node for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]

    if not top_level:
        # Module has no top-level definitions (e.g. pure script) — sliding window
        return None

    for node in top_level:
        start = node.lineno  # 1-indexed
        end = node.end_lineno or start  # type: ignore[attr-defined]
        node_lines = all_lines[start - 1 : end]

        if isinstance(node, ast.ClassDef):
            title = f"class {node.name}"
        elif isinstance(node, ast.AsyncFunctionDef):
            title = f"async def {node.name}"
        else:
            title = f"def {node.name}"

        # If the symbol is too large, split it into MAX_CHUNK_LINES sub-chunks
        if len(node_lines) <= MAX_CHUNK_LINES:
            chunk = _make_chunk(repo_id, file, node_lines, start, title)
            if chunk:
                chunks.append(chunk)
        else:
            cursor = 0
            part = 1
            while cursor < len(node_lines):
                sub = node_lines[cursor : cursor + MAX_CHUNK_LINES]
                sub_start = start + cursor
                chunk = _make_chunk(repo_id, file, sub, sub_start, f"{title} (part {part})")
                if chunk:
                    chunks.append(chunk)
                cursor += MAX_CHUNK_LINES
                part += 1

    # Capture any module-level code between / before top-level definitions
    # by collecting lines that fall outside any top-level node's range.
    covered: set[int] = set()
    for node in top_level:
        covered.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))  # type: ignore[attr-defined]

    module_lines: list[tuple[int, str]] = []
    for i, line in enumerate(all_lines, start=1):
        if i not in covered:
            module_lines.append((i, line))

    if module_lines:
        # Group consecutive module-level lines into windows
        group_start = module_lines[0][0]
        group: list[str] = [module_lines[0][1]]
        for prev, (lineno, text_line) in zip(module_lines, module_lines[1:], strict=False):
            if lineno == prev[0] + 1:
                group.append(text_line)
            else:
                chunk = _make_chunk(repo_id, file, group, group_start, f"{file.path}:{group_start}")
                if chunk:
                    chunks.append(chunk)
                group_start = lineno
                group = [text_line]
        chunk = _make_chunk(repo_id, file, group, group_start, f"{file.path}:{group_start}")
        if chunk:
            chunks.append(chunk)

    return chunks if chunks else None


# ---------------------------------------------------------------------------
# Sliding-window chunker (default for non-Python)
# ---------------------------------------------------------------------------

def chunk_source_file(repo_id: str, file: SourceFile) -> list[Chunk]:
    # Try AST chunking for Python first
    if file.language == "python":
        ast_chunks = _python_chunks(repo_id, file)
        if ast_chunks is not None:
            return ast_chunks

    # Fallback: fixed sliding window
    lines = file.content.splitlines()
    chunks: list[Chunk] = []
    cursor = 0

    while cursor < len(lines):
        end = min(cursor + MAX_CHUNK_LINES, len(lines))
        chunk_lines = lines[cursor:end]
        text = "\n".join(chunk_lines).strip()

        if len(text) >= MIN_CHUNK_CHARS:
            start_line = cursor + 1
            title = _title_for_chunk(file, text, start_line)
            chunk_type = "docs" if file.language in {"markdown", "text"} else "code"
            chunks.append(
                Chunk(
                    id=_stable_chunk_id(repo_id, file.path, start_line, text),
                    repo_id=repo_id,
                    file_path=file.path,
                    language=file.language,
                    chunk_type=chunk_type,
                    title=title,
                    content=text,
                    start_line=start_line,
                    end_line=end,
                    token_estimate=_estimate_tokens(text),
                )
            )

        cursor = end

    return chunks


def chunk_files(repo_id: str, files: list[SourceFile]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for file in files:
        chunks.extend(chunk_source_file(repo_id, file))
    return chunks
