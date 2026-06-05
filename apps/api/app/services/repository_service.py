"""Repository service — orchestrates load → chunk → extract symbols → embed → store.

Indexing runs as a FastAPI BackgroundTask so the HTTP response returns
immediately with status=indexing. The client polls /api/repositories/{id}/status.

Phase 2 additions:
  - Symbol extraction (Python ast + JS/TS regex) runs after chunking
  - Import graph edges are extracted simultaneously
  - Chunk objects are enriched with symbol_name/symbol_kind metadata
  - All data persisted to index_store
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import BackgroundTasks, HTTPException

from app.graph.extractor import extract_symbols_and_edges
from app.llm.ollama_adapter import ollama_adapter
from app.models.schemas import (
    Chunk,
    IndexingStatus,
    IndexRepositoryRequest,
    RepositoryIndexResponse,
    RepositoryRecord,
    RepositorySource,
    Symbol,
)
from app.retrieval.chunker import chunk_files
from app.retrieval.embedder import embed_chunks
from app.services.index_store import index_store
from app.services.repository_loader import repository_loader

logger = logging.getLogger(__name__)


def _repo_id(source: RepositorySource, identifier: str) -> str:
    return hashlib.sha1(f"{source}:{identifier}".encode()).hexdigest()[:12]


def _enrich_chunks_with_symbols(chunks: list[Chunk], symbols: list[Symbol]) -> None:
    """Attach symbol_name and symbol_kind to chunks that overlap a known symbol."""
    # Build a fast lookup: (file_path, line) -> symbol
    sym_map: dict[tuple[str, int], Symbol] = {}
    for sym in symbols:
        for line in range(sym.start_line, sym.end_line + 1):
            sym_map[(sym.file_path, line)] = sym

    for chunk in chunks:
        # Check if any line of this chunk falls in a symbol range
        for line in range(chunk.start_line, min(chunk.start_line + 5, chunk.end_line + 1)):
            sym = sym_map.get((chunk.file_path, line))
            if sym:
                chunk.symbol_name = sym.name
                chunk.symbol_kind = sym.kind
                break


async def _run_indexing(
    repo_id: str,
    name: str,
    source: RepositorySource,
    source_url: str,
    payload: IndexRepositoryRequest,
) -> None:
    """Background task: load → chunk → extract graph → embed → persist."""
    try:
        # 1. Load files
        if payload.source == RepositorySource.github:
            logger.info("Loading GitHub repository from %s", payload.url)
            _, files, skipped_files = await repository_loader.load_github_zip(str(payload.url))
        else:
            logger.info("Loading local repository from %s", payload.local_path)
            _, files, skipped_files = repository_loader.load_local_path(
                payload.local_path,
                payload.name,
            )

        if not files:
            raise ValueError(f"No valid source files found in {name}")

        logger.info("Loaded %d files, skipped %d", len(files), skipped_files)

        # 2. Chunk
        logger.info("Chunking %d files", len(files))
        chunks = chunk_files(repo_id, files)

        if not chunks:
            raise ValueError(f"Failed to create chunks from {len(files)} files")

        logger.info("Created %d chunks from %d files", len(chunks), len(files))
        languages = sorted({file.language for file in files})

        # 3. Extract symbols and import graph (Phase 2)
        logger.info("Extracting symbols and import graph for %s", name)
        try:
            symbols, edges = extract_symbols_and_edges(repo_id, files)
            logger.info("Extracted %d symbols, %d import edges", len(symbols), len(edges))
        except Exception as sym_err:
            logger.warning("Symbol extraction failed (non-critical): %s", sym_err)
            symbols, edges = [], []

        # 4. Enrich chunks with symbol metadata
        _enrich_chunks_with_symbols(chunks, symbols)

        # 5. Store with status=embedding so UI shows progress
        index_store.upsert_repository(
            repo_id=repo_id,
            name=name,
            source=source,
            source_url=source_url,
            chunks=chunks,
            languages=languages,
            file_count=len(files),
            status=IndexingStatus.embedding,
            symbols=symbols,
            edges=edges,
        )

        # 6. Embed (skipped gracefully if Ollama unavailable)
        embedded = await embed_chunks(chunks, ollama_adapter)

        # 7. Update embed count live
        index_store.update_embedded_count(repo_id, embedded)

        # 8. Final persist with ready status
        index_store.upsert_repository(
            repo_id=repo_id,
            name=name,
            source=source,
            source_url=source_url,
            chunks=chunks,
            languages=languages,
            file_count=len(files),
            status=IndexingStatus.ready,
            symbols=symbols,
            edges=edges,
        )
        logger.info(
            "Indexing complete for %s: %d files, %d chunks, %d embedded, %d symbols, %d edges",
            name,
            len(files),
            len(chunks),
            embedded,
            len(symbols),
            len(edges),
        )

    except Exception as exc:
        logger.exception("Indexing failed for repo_id=%s: %s", repo_id, exc)
        index_store.set_repository_status(
            repo_id, IndexingStatus.failed, error=str(exc)
        )


class RepositoryService:
    async def index_repository(
        self,
        payload: IndexRepositoryRequest,
        background_tasks: BackgroundTasks,
    ) -> RepositoryIndexResponse:
        """Create a repository record and schedule indexing as a background task."""
        if payload.source == RepositorySource.github:
            if payload.url is None:
                raise HTTPException(status_code=400, detail="url is required for GitHub indexing")
            source_url = str(payload.url)
            from app.services.repository_loader import normalize_github_url
            name = payload.name or normalize_github_url(source_url)[0]
        else:
            if not payload.local_path:
                raise HTTPException(
                    status_code=400,
                    detail="local_path is required for local indexing",
                )
            from pathlib import Path
            source_url = payload.local_path
            name = payload.name or Path(payload.local_path).expanduser().resolve().name

        repo_id = _repo_id(payload.source, source_url)

        # Create placeholder record immediately so polling works
        record: RepositoryRecord = index_store.create_repository(
            repo_id=repo_id,
            name=name,
            source=payload.source,
            source_url=source_url,
        )

        # Schedule the real work
        background_tasks.add_task(
            _run_indexing,
            repo_id=repo_id,
            name=name,
            source=payload.source,
            source_url=source_url,
            payload=payload,
        )

        return RepositoryIndexResponse(
            repository=record,
            indexed_files=0,
            indexed_chunks=0,
            skipped_files=0,
        )


repository_service = RepositoryService()
