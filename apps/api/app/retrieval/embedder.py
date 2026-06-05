"""Embedding service — attaches vector embeddings to chunks using Ollama.

Embeddings are stored as list[float] directly on each Chunk object.
If Ollama is unavailable all chunks keep embedding=None and the system
falls back to keyword-only retrieval transparently.

Optimization: uses asyncio.gather with a semaphore to embed up to
CONCURRENT_EMBED requests in parallel instead of purely sequential.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.llm.ollama_adapter import OllamaAdapter
from app.models.schemas import Chunk

logger = logging.getLogger(__name__)

# Max concurrent embed requests to Ollama (avoids overwhelming it)
_MAX_CONCURRENT = 1


def _chunk_to_embed_text(chunk: Chunk) -> str:
    """Build the text to embed for a chunk.

    Concatenate file path, title (which may include symbol name), and a
    truncated content window so the embedding captures location + semantics.
    """
    symbol_hint = ""
    if chunk.symbol_name and chunk.symbol_kind:
        symbol_hint = f"\nSymbol: {chunk.symbol_kind} {chunk.symbol_name}"

    header = f"{chunk.file_path} — {chunk.title}{symbol_hint}"
    body = chunk.content[:1200]  # Keep embed input within ~300 tokens
    return f"{header}\n\n{body}"


async def embed_chunks(
    chunks: list[Chunk],
    adapter: OllamaAdapter,
    *,
    on_progress: None | object = None,
) -> int:
    """Embed all chunks with bounded parallelism and attach vectors in-place.

    Returns the number of chunks that received an embedding.
    """
    if not settings.enable_embeddings or not chunks:
        return 0

    sem = asyncio.Semaphore(_MAX_CONCURRENT)
    embedded = 0
    failed_streak = 0

    async def _embed_one(chunk: Chunk) -> bool:
        async with sem:
            text = _chunk_to_embed_text(chunk)
            vec = await adapter.embed(text)
            if vec is not None:
                chunk.embedding = vec
                return True
            return False

    # Process in batches to report progress and detect early Ollama failure
    batch_size = settings.embed_batch_size
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start : batch_start + batch_size]
        results = await asyncio.gather(*[_embed_one(c) for c in batch])

        batch_embedded = sum(results)
        embedded += batch_embedded

        if batch_embedded == 0:
            failed_streak += 1
            if failed_streak >= 2:
                logger.warning(
                    "Ollama embed returned None for 2 consecutive batches — stopping embedding pass"
                )
                break
        else:
            failed_streak = 0

        if on_progress is not None:
            on_progress(batch_start + len(batch), len(chunks))

    logger.info("Embedded %d / %d chunks", embedded, len(chunks))
    return embedded
