"""Retrieval ranking — keyword BM25-lite, semantic cosine, hybrid fusion,
and Phase 2 graph-neighbor expansion.

Four modes:
  1. keyword only   — when no embeddings are present
  2. semantic only  — cosine similarity on pre-computed vectors
  3. hybrid         — linear interpolation: 0.4 * keyword + 0.6 * semantic
  4. graph-expanded — hybrid + boost chunks whose file is a graph neighbor
                      of a highly-scored chunk's file

The caller picks the right entry point; all return the same Citation list.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from app.models.schemas import Chunk, Citation

WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")

# Hybrid blend weights
_KEYWORD_WEIGHT = 0.4
_SEMANTIC_WEIGHT = 0.6

# Graph neighbor boost added to score of neighbor files
_GRAPH_NEIGHBOR_BOOST = 0.12


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def tokenize(text: str) -> list[str]:
    return [word.lower() for word in WORD_RE.findall(text)]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two equal-length float vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def to_citation(chunk: Chunk, score: float) -> Citation:
    excerpt = chunk.content.strip().replace("\n", " ")
    if len(excerpt) > 320:
        excerpt = excerpt[:317].rstrip() + "..."
    return Citation(
        chunk_id=chunk.id,
        file_path=chunk.file_path,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        title=chunk.title,
        excerpt=excerpt,
        score=round(score, 4),
    )


# ---------------------------------------------------------------------------
# Keyword scoring (TF + path/title/symbol bonuses)
# ---------------------------------------------------------------------------


def _keyword_score(query: str, chunk: Chunk) -> float:
    query_terms = tokenize(query)
    if not query_terms:
        return 0.0

    # Include symbol name and kind in scoring text if available
    symbol_text = f"{chunk.symbol_name or ''} {chunk.symbol_kind or ''}"
    content_terms = Counter(
        tokenize(f"{chunk.file_path} {chunk.title} {symbol_text} {chunk.content}")
    )
    score = 0.0
    for term in query_terms:
        frequency = content_terms.get(term, 0)
        if frequency:
            score += 1.0 + math.log(frequency)

    path_bonus = sum(1.5 for term in query_terms if term in chunk.file_path.lower())
    title_bonus = sum(1.0 for term in query_terms if term in chunk.title.lower())
    symbol_bonus = sum(
        2.0 for term in query_terms
        if chunk.symbol_name and term in chunk.symbol_name.lower()
    )
    docs_bonus = 0.4 if chunk.chunk_type == "docs" else 0.0

    authority_bonus = 0.0
    lower_path = chunk.file_path.lower()
    if "readme" in lower_path or "architecture" in lower_path or "adr" in lower_path or "index" in lower_path:
        authority_bonus += 1.0

    return score + path_bonus + title_bonus + symbol_bonus + docs_bonus + authority_bonus


def _normalize(scores: list[float]) -> list[float]:
    """Min-max normalize a list of scores to [0, 1]."""
    if not scores:
        return scores
    lo, hi = min(scores), max(scores)
    if hi == lo:
        return [1.0 if s > 0 else 0.0 for s in scores]
    return [(s - lo) / (hi - lo) for s in scores]


# ---------------------------------------------------------------------------
# Public ranking entry points
# ---------------------------------------------------------------------------


def rank_chunks(query: str, chunks: list[Chunk], limit: int) -> list[Citation]:
    """Pure keyword ranking — used as fallback when no embeddings exist."""
    scored = [(chunk, _keyword_score(query, chunk)) for chunk in chunks]
    filtered = [(c, s) for c, s in scored if s > 0]
    filtered.sort(key=lambda item: item[1], reverse=True)
    return [to_citation(c, s) for c, s in filtered[:limit]]


def hybrid_rank_chunks(
    query: str,
    query_embedding: list[float] | None,
    chunks: list[Chunk],
    limit: int,
    *,
    graph_neighbors: set[str] | None = None,
) -> list[Citation]:
    """Hybrid keyword + semantic ranking with optional graph-neighbor boost.

    If no embeddings are available (either query or chunks), falls back
    to pure keyword ranking automatically.

    Args:
        graph_neighbors: set of file paths that are graph neighbors of
            highly-ranked results. These get a score boost.
    """
    # Check if we can do semantic search
    embedded_chunks = [c for c in chunks if c.embedding is not None]
    use_semantic = query_embedding is not None and len(embedded_chunks) > 0

    if not use_semantic:
        return rank_chunks(query, chunks, limit)

    # Compute raw scores
    keyword_scores = [_keyword_score(query, c) for c in chunks]
    semantic_scores = [
        cosine_similarity(query_embedding, c.embedding) if c.embedding is not None else 0.0
        for c in chunks
    ]

    # Normalize both to [0, 1]
    kw_norm = _normalize(keyword_scores)
    sem_norm = _normalize(semantic_scores)

    # Blend + graph neighbor boost
    blended = []
    for _i, (chunk, kw, sem) in enumerate(zip(chunks, kw_norm, sem_norm, strict=True)):
        score = _KEYWORD_WEIGHT * kw + _SEMANTIC_WEIGHT * sem
        if graph_neighbors and chunk.file_path in graph_neighbors:
            score += _GRAPH_NEIGHBOR_BOOST
        blended.append(score)

    # Filter zero-score, sort, take top-K
    scored = [(chunk, score) for chunk, score in zip(chunks, blended, strict=True) if score > 0]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [to_citation(c, s) for c, s in scored[:limit]]


def expand_graph_neighbors(
    top_citations: list[Citation],
    file_neighbor_fn,  # callable(file_path) -> list[str]
    depth: int = 1,
) -> set[str]:
    """Given top citations, return the set of file paths that are direct
    graph neighbors (importers/importees) of the cited files.

    Used to generate the graph_neighbors boost set for a second-pass ranking.
    """
    neighbors: set[str] = set()
    for citation in top_citations[:4]:  # Only expand top 4 to keep it fast
        for neighbor_path in file_neighbor_fn(citation.file_path):
            neighbors.add(neighbor_path)
    return neighbors


# Keep legacy name for backwards compat
score_chunk = _keyword_score
