"""Caching service for frequently accessed repository data.

Implements a simple LRU cache with TTL support for search results,
graph queries, and symbol lookups to improve retrieval performance.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Simple LRU cache with time-to-live expiration."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300) -> None:
        self._cache: OrderedDict[str, tuple[T, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> T | None:
        """Get value if it exists and hasn't expired."""
        if key not in self._cache:
            self._misses += 1
            return None

        value, timestamp = self._cache[key]
        if time.time() - timestamp > self._ttl_seconds:
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        return value

    def set(self, key: str, value: T) -> None:
        """Set value and update timestamp."""
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self._max_size:
            # Evict oldest
            self._cache.popitem(last=False)

        self._cache[key] = (value, time.time())
        self._cache.move_to_end(key)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict:
        """Return cache hit/miss statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": round(hit_rate, 3),
        }


class CacheService:
    """Repository-level cache for search results and graph data."""

    def __init__(self) -> None:
        # Per-repo caches
        self._search_cache: dict[str, TTLCache] = {}
        self._symbol_cache: dict[str, TTLCache] = {}
        self._graph_cache: dict[str, TTLCache] = {}

    def get_search_cache(self, repo_id: str) -> TTLCache:
        """Get or create search result cache for a repository."""
        if repo_id not in self._search_cache:
            self._search_cache[repo_id] = TTLCache(max_size=500, ttl_seconds=600)
        return self._search_cache[repo_id]

    def get_symbol_cache(self, repo_id: str) -> TTLCache:
        """Get or create symbol lookup cache for a repository."""
        if repo_id not in self._symbol_cache:
            self._symbol_cache[repo_id] = TTLCache(max_size=200, ttl_seconds=1800)
        return self._symbol_cache[repo_id]

    def get_graph_cache(self, repo_id: str) -> TTLCache:
        """Get or create graph query cache for a repository."""
        if repo_id not in self._graph_cache:
            self._graph_cache[repo_id] = TTLCache(max_size=100, ttl_seconds=900)
        return self._graph_cache[repo_id]

    def invalidate_repo(self, repo_id: str) -> None:
        """Clear all caches for a repository (e.g., after re-indexing)."""
        self._search_cache.pop(repo_id, None).clear() if repo_id in self._search_cache else None
        self._symbol_cache.pop(repo_id, None).clear() if repo_id in self._symbol_cache else None
        self._graph_cache.pop(repo_id, None).clear() if repo_id in self._graph_cache else None

    def stats(self) -> dict:
        """Return cache statistics across all repositories."""
        return {
            "search_caches": len(self._search_cache),
            "symbol_caches": len(self._symbol_cache),
            "graph_caches": len(self._graph_cache),
        }


cache_service = CacheService()
