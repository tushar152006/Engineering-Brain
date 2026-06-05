"""Architecture service — generates repository architecture summaries.

Phase 1: static heuristic summary (frameworks, entrypoints, directories)
Phase 2: LLM-powered narrative synthesis using Ollama

When Ollama is available, the service calls `summarize_with_llm()` which
sends a structured evidence pack and asks for a senior-architect-level
architecture overview with citations.
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import PurePosixPath

from fastapi import HTTPException

from app.llm.ollama_adapter import ollama_adapter
from app.models.schemas import (
    ArchitectureSummaryRequest,
    ArchitectureSummaryResponse,
    DirectorySummary,
    FrameworkSignal,
    Symbol,
)
from app.services.analysis_service import (
    detect_entrypoints,
    detect_frameworks,
    summarize_directories,
)
from app.services.index_store import index_store

logger = logging.getLogger(__name__)

IMPORTANT_FILES = {
    "readme.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "dockerfile",
    "docker-compose.yml",
    "compose.yml",
    "next.config.js",
    "vite.config.ts",
    "main.py",
    "app.py",
    "index.ts",
    "index.js",
    "tsconfig.json",
    ".env.example",
}

_ARCH_SYSTEM_PROMPT = """\
You are a staff software architect reviewing a codebase.
Produce a concise, grounded architecture overview.

Rules:
- Use only the supplied evidence (file list, symbols, frameworks, entrypoints).
- For every major claim, cite a file path or module name.
- Describe: (1) primary purpose, (2) main modules, (3) key technologies,
  (4) entry points and request flow, (5) notable patterns or risks.
- Write in clear technical prose, max 400 words.
- Do not invent services or dependencies not mentioned in the evidence.
"""


def _build_arch_evidence(
    repo_name: str,
    languages: list[str],
    file_count: int,
    chunk_count: int,
    frameworks: list[dict],
    entrypoints: list[str],
    top_dirs: list[dict],
    important_files: list[str],
    top_symbols: list[Symbol],
) -> str:
    lines = [
        f"Repository: {repo_name}",
        f"Languages: {', '.join(languages) or 'unknown'}",
        f"Files: {file_count} | Chunks: {chunk_count}",
        "",
        "Detected Frameworks:",
    ]
    for fw in frameworks:
        files_str = ", ".join(fw["evidence_files"][:3])
        lines.append(f"  - {fw['name']}: {files_str}")

    lines += ["", "Entrypoints:"]
    for ep in entrypoints:
        lines.append(f"  - {ep}")

    lines += ["", "Top Directories (by chunk count):"]
    for d in top_dirs[:6]:
        lines.append(f"  - {d['name']}: {d['chunk_count']} chunks")

    lines += ["", "Important Files:"]
    for f in important_files[:10]:
        lines.append(f"  - {f}")

    if top_symbols:
        lines += ["", "Top-Level Symbols (sample):"]
        for s in top_symbols[:15]:
            lines.append(f"  - {s.kind} {s.qualified_name} ({s.file_path}:{s.start_line})")

    return "\n".join(lines)


def _dynamic_next_steps(
    has_embeddings: bool,
    has_symbols: bool,
    has_edges: bool,
    framework_names: list[str],
) -> list[str]:
    """Generate context-aware next steps based on what's already been indexed."""
    steps = []
    if not has_embeddings:
        steps.append("Start Ollama and re-index to enable semantic search and LLM answers.")
    if not has_symbols:
        steps.append("Re-index — symbol extraction should now run automatically.")
    if not has_edges:
        steps.append("Re-index to generate import dependency graph for graph-expanded retrieval.")
    if "FastAPI" in framework_names or "Flask" in framework_names or "Django" in framework_names:
        steps.append("Ask: 'How does request routing work?' to explore the API layer.")
    if "React" in framework_names or "Next.js" in framework_names:
        steps.append("Ask: 'What are the main React components and their responsibilities?'")
    if "SQLAlchemy" in framework_names or "Prisma" in framework_names:
        steps.append("Ask: 'How is the database schema defined?'")
    if not steps:
        steps.append("Ask an engineering question to start exploring the codebase.")
    return steps[:5]


class ArchitectureService:
    async def summarize(self, payload: ArchitectureSummaryRequest) -> ArchitectureSummaryResponse:
        """Synchronous architecture summary (used by the route handler)."""
        repository = await index_store.get_repository(payload.repo_id)
        if repository is None:
            raise HTTPException(status_code=404, detail="Repository not found")

        chunks = await index_store.get_chunks(payload.repo_id)
        symbols = await index_store.get_symbols(payload.repo_id)
        edges = await index_store.get_edges(payload.repo_id)

        # --- Important files ---
        important: list[str] = []
        for chunk in chunks:
            path = PurePosixPath(chunk.file_path)
            if path.name.lower() in IMPORTANT_FILES and chunk.file_path not in important:
                important.append(chunk.file_path)

        # --- Framework detection ---
        raw_frameworks = detect_frameworks(chunks)
        frameworks = [
            FrameworkSignal(name=fw["name"], evidence_files=fw["evidence_files"])
            for fw in raw_frameworks
        ]
        framework_names = [fw.name for fw in frameworks]

        # --- Directories ---
        raw_dirs = summarize_directories(chunks)
        top_dirs = [
            DirectorySummary(name=d["name"], chunk_count=d["chunk_count"])
            for d in raw_dirs
        ]

        # --- Entrypoints ---
        entrypoints = detect_entrypoints(chunks)

        # --- Top symbols (sample for display) ---
        kind_priority = {"class": 0, "function": 1, "async_function": 1, "method": 2}
        sorted_symbols = sorted(symbols, key=lambda s: kind_priority.get(s.kind, 3))
        top_symbols = sorted_symbols[:20]

        # --- Dependency summary ---
        dep_summary: dict = {}
        if edges:
            src_counts = Counter(e.source_path for e in edges)
            dep_summary = {
                "total_edges": len(edges),
                "most_imported": sorted(
                    Counter(e.target_path for e in edges).items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5],
                "most_importing": sorted(
                    src_counts.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5],
            }

        # --- Static summary sentence ---
        code_chunks = sum(1 for c in chunks if c.chunk_type == "code")
        doc_chunks = len(chunks) - code_chunks
        fw_sentence = (
            f" Technology signals: {', '.join(framework_names[:5])}."
            if framework_names
            else " No strong framework signals detected yet."
        )
        static_summary = (
            f"{repository.name} contains {repository.file_count} indexed files, "
            f"{repository.chunk_count} searchable chunks "
            f"({code_chunks} code, {doc_chunks} docs), "
            f"and {len(symbols)} extracted symbols across "
            f"{', '.join(repository.languages) or 'unknown languages'}."
            f"{fw_sentence}"
        )

        # --- Dynamic next steps ---
        next_steps = _dynamic_next_steps(
            has_embeddings=repository.embedded_chunk_count > 0,
            has_symbols=len(symbols) > 0,
            has_edges=len(edges) > 0,
            framework_names=framework_names,
        )

        # --- Docs Gap Report ---
        doc_files = {c.file_path for c in chunks if c.chunk_type == "docs"}
        gap_lines = []
        if not doc_files:
            gap_lines.append("No documentation files found.")
        else:
            if not any("readme" in f.lower() for f in doc_files):
                gap_lines.append("Missing root README.")
            if not any("arch" in f.lower() or "design" in f.lower() or "adr" in f.lower() for f in doc_files):
                gap_lines.append("Missing architecture or design documents.")
        
        undoc_dirs = []
        for d in raw_dirs[:5]:
            d_name = d["name"]
            if d_name != "." and not any(f.startswith(d_name + "/") for f in doc_files):
                undoc_dirs.append(d_name)
        if undoc_dirs:
            gap_lines.append(f"Top directories missing documentation: {', '.join(undoc_dirs)}.")
        
        docs_gap_report = " ".join(gap_lines) if gap_lines else "No major documentation gaps detected."

        return ArchitectureSummaryResponse(
            repository=repository,
            summary=static_summary,
            top_directories=top_dirs,
            important_files=important[:12],
            entrypoints=entrypoints,
            frameworks=frameworks,
            next_steps=next_steps,
            llm_narrative=None,  # populated by /deep endpoint
            docs_gap_report=docs_gap_report,
            symbol_count=len(symbols),
            top_symbols=[
                {
                    "name": s.name,
                    "kind": s.kind,
                    "file": s.file_path,
                    "line": s.start_line,
                    "signature": s.signature,
                }
                for s in top_symbols
            ],
            dependency_summary=dep_summary,
        )

    async def summarize_deep(self, payload: ArchitectureSummaryRequest) -> ArchitectureSummaryResponse:
        """Architecture summary with LLM-generated narrative (async, uses Ollama)."""
        # Get base summary first
        base = await self.summarize(payload)

        repository = await index_store.get_repository(payload.repo_id)
        symbols = await index_store.get_symbols(payload.repo_id)

        # Build evidence for LLM
        evidence = _build_arch_evidence(
            repo_name=repository.name,
            languages=list(repository.languages),
            file_count=repository.file_count,
            chunk_count=repository.chunk_count,
            frameworks=[fw.model_dump() for fw in base.frameworks],
            entrypoints=base.entrypoints,
            top_dirs=[d.model_dump() for d in base.top_directories],
            important_files=base.important_files,
            top_symbols=symbols[:20],
        )

        prompt = f"Based on this repository evidence, write an architecture overview:\n\n{evidence}"

        llm_narrative = await ollama_adapter.generate(
            prompt,
            system=_ARCH_SYSTEM_PROMPT,
            temperature=0.1,
        )

        # Return base summary enriched with LLM narrative
        return ArchitectureSummaryResponse(
            **{
                **base.model_dump(),
                "llm_narrative": llm_narrative or "Ollama is unavailable — narrative synthesis skipped.",
            }
        )


architecture_service = ArchitectureService()
