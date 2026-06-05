"""Comprehensive test suite for Engineering Brain core functionality."""

import pytest
from app.models.schemas import SourceFile, Chunk, Symbol, GraphEdge, Citation
from app.retrieval.chunker import chunk_files, chunk_source_file
from app.retrieval.ranking import (
    tokenize,
    cosine_similarity,
    _keyword_score,
    hybrid_rank_chunks,
)
from app.graph.extractor import extract_symbols_and_edges
from app.services.cache_service import TTLCache
import time


class TestChunking:
    """Test code and document chunking."""

    def test_markdown_chunks_by_heading(self) -> None:
        file = SourceFile(
            path="docs/README.md",
            language="markdown",
            content="# Title\nContent here.\n## Section\nMore content.",
            size_bytes=100,
        )
        chunks = chunk_source_file("repo1", file)
        assert len(chunks) >= 1
        assert all(c.file_path == "docs/README.md" for c in chunks)
        assert all(c.chunk_type == "docs" for c in chunks)

    def test_python_chunks_by_function(self) -> None:
        file = SourceFile(
            path="src/main.py",
            language="python",
            content="def hello():\n    print('hello')\n\ndef world():\n    print('world')",
            size_bytes=100,
        )
        chunks = chunk_source_file("repo1", file)
        assert len(chunks) >= 1
        assert all(c.chunk_type == "code" for c in chunks)
        assert all(c.file_path == "src/main.py" for c in chunks)

    def test_code_chunks_minimum_size(self) -> None:
        file = SourceFile(
            path="src/empty.py",
            language="python",
            content="",
            size_bytes=0,
        )
        chunks = chunk_source_file("repo1", file)
        assert len(chunks) == 0  # Empty files shouldn't produce chunks

    def test_multiple_files_chunking(self) -> None:
        files = [
            SourceFile(
                path="file1.py",
                language="python",
                content="def foo():\n    pass",
                size_bytes=20,
            ),
            SourceFile(
                path="file2.md",
                language="markdown",
                content="# Doc",
                size_bytes=10,
            ),
        ]
        chunks = chunk_files("repo1", files)
        assert len(chunks) >= 2
        assert any(c.file_path == "file1.py" for c in chunks)
        assert any(c.file_path == "file2.md" for c in chunks)


class TestRanking:
    """Test search ranking and scoring."""

    def test_tokenize_extracts_words(self) -> None:
        tokens = tokenize("def hello_world():")
        assert "def" in tokens
        assert "hello_world" in tokens

    def test_cosine_similarity_identical_vectors(self) -> None:
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        sim = cosine_similarity(v1, v2)
        assert abs(sim - 1.0) < 0.001

    def test_cosine_similarity_orthogonal_vectors(self) -> None:
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        sim = cosine_similarity(v1, v2)
        assert abs(sim) < 0.001

    def test_keyword_score_exact_match(self) -> None:
        chunk = Chunk(
            id="c1",
            repo_id="repo1",
            file_path="auth.py",
            language="python",
            chunk_type="code",
            title="authenticate",
            content="def authenticate(user): pass",
            start_line=1,
            end_line=1,
            token_estimate=10,
        )
        score = _keyword_score("authenticate", chunk)
        assert score > 0

    def test_keyword_score_no_match(self) -> None:
        chunk = Chunk(
            id="c1",
            repo_id="repo1",
            file_path="auth.py",
            language="python",
            chunk_type="code",
            title="authenticate",
            content="def authenticate(user): pass",
            start_line=1,
            end_line=1,
            token_estimate=10,
        )
        score = _keyword_score("unrelated_term_xyz", chunk)
        assert score == 0

    def test_hybrid_ranking_returns_citations(self) -> None:
        chunks = [
            Chunk(
                id="c1",
                repo_id="repo1",
                file_path="file1.py",
                language="python",
                chunk_type="code",
                title="func1",
                content="def authenticate(): pass",
                start_line=1,
                end_line=1,
                token_estimate=10,
                embedding=[0.1, 0.2, 0.3],
            ),
            Chunk(
                id="c2",
                repo_id="repo1",
                file_path="file2.py",
                language="python",
                chunk_type="code",
                title="func2",
                content="def database_query(): pass",
                start_line=10,
                end_line=10,
                token_estimate=10,
                embedding=[0.2, 0.3, 0.4],
            ),
        ]
        results = hybrid_rank_chunks(
            "authenticate", [0.1, 0.2, 0.3], chunks, limit=5
        )
        assert len(results) > 0
        assert all(isinstance(r, Citation) for r in results)


class TestGraphExtraction:
    """Test symbol and import graph extraction."""

    def test_python_symbol_extraction(self) -> None:
        file = SourceFile(
            path="src/main.py",
            language="python",
            content="class MyClass:\n    def method(self):\n        pass",
            size_bytes=100,
        )
        symbols, edges = extract_symbols_and_edges("repo1", [file])
        assert len(symbols) > 0
        assert any(s.name == "MyClass" for s in symbols)

    def test_python_import_extraction(self) -> None:
        files = [
            SourceFile(
                path="src/a.py",
                language="python",
                content="from src.b import func",
                size_bytes=30,
            ),
            SourceFile(
                path="src/b.py",
                language="python",
                content="def func(): pass",
                size_bytes=20,
            ),
        ]
        symbols, edges = extract_symbols_and_edges("repo1", files)
        assert len(edges) > 0


class TestCaching:
    """Test cache service functionality."""

    def test_cache_hit(self) -> None:
        cache: TTLCache[str] = TTLCache(max_size=10, ttl_seconds=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_miss(self) -> None:
        cache: TTLCache[str] = TTLCache(max_size=10, ttl_seconds=10)
        cache.set("key1", "value1")
        assert cache.get("key2") is None

    def test_cache_expiration(self) -> None:
        cache: TTLCache[str] = TTLCache(max_size=10, ttl_seconds=1)
        cache.set("key1", "value1")
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_cache_lru_eviction(self) -> None:
        cache: TTLCache[str] = TTLCache(max_size=2, ttl_seconds=100)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict key1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_cache_stats(self) -> None:
        cache: TTLCache[str] = TTLCache(max_size=10, ttl_seconds=10)
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
