"""Persistent PostgreSQL index store with connection pooling.

This replaces the in-memory store for production. It uses psycopg connection pool
for efficient database access and implements the same interface as InMemoryIndexStore
for easy migration.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional
from contextlib import asynccontextmanager

import psycopg
from psycopg import sql
from psycopg_pool import AsyncConnectionPool

from app.core.config import settings
from app.models.schemas import (
    Chunk,
    FeedbackLabel,
    FeedbackRecord,
    GraphEdge,
    IndexingStatus,
    RepositoryRecord,
    RepositorySource,
    Symbol,
    AgentRun,
    AgentRunStatus,
)

logger = logging.getLogger(__name__)


class PersistentIndexStore:
    """PostgreSQL-backed index store with connection pooling."""

    def __init__(self, connection_string: str | None = None) -> None:
        self._connection_string = connection_string or settings.database_url
        self._pool: AsyncConnectionPool | None = None

    async def initialize(self) -> None:
        """Initialize connection pool. Call on app startup."""
        if not self._connection_string:
            raise ValueError("DATABASE_URL not set in environment")

        self._pool = AsyncConnectionPool(
            self._connection_string,
            min_size=5,
            max_size=20,
            timeout=30,
        )
        await self._pool.open()
        logger.info("Database connection pool initialized")

    async def shutdown(self) -> None:
        """Close connection pool. Call on app shutdown."""
        if self._pool:
            await self._pool.close()
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def _get_connection(self):
        """Get a connection from the pool."""
        if not self._pool:
            raise RuntimeError("Pool not initialized")
        async with self._pool.connection() as conn:
            yield conn

    # ─── Repository CRUD ──────────────────────────────────────────────────────

    async def create_repository(
        self,
        repo_id: str,
        name: str,
        source: RepositorySource,
        source_url: str | None,
    ) -> RepositoryRecord:
        """Create a repository record."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                # Get default organization
                await cur.execute(
                    "SELECT id FROM organizations WHERE slug = %s",
                    ("default",)
                )
                org_row = await cur.fetchone()
                org_id = org_row[0] if org_row else None

                if not org_id:
                    # Create default org
                    await cur.execute(
                        "INSERT INTO organizations (name, slug) VALUES (%s, %s) "
                        "RETURNING id",
                        ("Default", "default")
                    )
                    org_id = (await cur.fetchone())[0]

                # Create repository
                await cur.execute(
                    """INSERT INTO repositories
                       (id, organization_id, full_name, visibility, indexing_status)
                       VALUES (%s, %s, %s, %s, %s)
                       RETURNING id, full_name, indexing_status, created_at""",
                    (repo_id, org_id, name, source.value, IndexingStatus.indexing.value)
                )
                row = await cur.fetchone()
                await conn.commit()

        return RepositoryRecord(
            id=repo_id,
            name=name,
            source=source,
            source_url=source_url,
            status=IndexingStatus.indexing,
            indexed_at=row[3].isoformat(),
        )

    async def get_repository(self, repo_id: str) -> RepositoryRecord | None:
        """Get repository record."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT id, full_name, visibility, indexing_status,
                              file_count, chunk_count, embedded_chunk_count,
                              symbol_count, edge_count, languages, indexed_at
                       FROM repositories WHERE id = %s""",
                    (repo_id,)
                )
                row = await cur.fetchone()

        if not row:
            return None

        return RepositoryRecord(
            id=row[0],
            name=row[1],
            source=RepositorySource.github if "github" in str(row[2]) else RepositorySource.local,
            status=IndexingStatus(row[3]),
            file_count=row[4],
            chunk_count=row[5],
            embedded_chunk_count=row[6],
            symbol_count=row[7],
            edge_count=row[8],
            languages=row[9] or [],
            indexed_at=(row[10] or datetime.now(UTC)).isoformat(),
        )

    async def list_repositories(self) -> list[RepositoryRecord]:
        """List all repositories."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT id, full_name, visibility, indexing_status,
                              file_count, chunk_count, embedded_chunk_count,
                              symbol_count, edge_count, languages, indexed_at
                       FROM repositories ORDER BY updated_at DESC LIMIT 100"""
                )
                rows = await cur.fetchall()

        return [
            RepositoryRecord(
                id=row[0],
                name=row[1],
                source=RepositorySource.github,
                status=IndexingStatus(row[3]),
                file_count=row[4],
                chunk_count=row[5],
                embedded_chunk_count=row[6],
                symbol_count=row[7],
                edge_count=row[8],
                languages=row[9] or [],
                indexed_at=(row[10] or datetime.now(UTC)).isoformat(),
            )
            for row in rows
        ]

    async def set_repository_status(
        self,
        repo_id: str,
        status: IndexingStatus,
        error: str | None = None,
    ) -> None:
        """Update repository status."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """UPDATE repositories
                       SET indexing_status = %s, error = %s, updated_at = NOW()
                       WHERE id = %s""",
                    (status.value, error, repo_id)
                )
                await conn.commit()

    async def upsert_repository(
        self,
        repo_id: str,
        name: str,
        source: RepositorySource,
        source_url: str | None,
        chunks: list[Chunk] | None = None,
        symbols: list[Symbol] | None = None,
        edges: list[GraphEdge] | None = None,
        languages: list[str] | None = None,
        file_count: int = 0,
        status: IndexingStatus = IndexingStatus.ready,
    ) -> None:
        """Upsert repository with data."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                # Update repository
                await cur.execute(
                    """UPDATE repositories
                       SET indexing_status = %s, file_count = %s,
                           chunk_count = %s, symbol_count = %s,
                           edge_count = %s, languages = %s,
                           indexed_at = NOW(), updated_at = NOW()
                       WHERE id = %s""",
                    (
                        status.value,
                        file_count,
                        len(chunks) if chunks else 0,
                        len(symbols) if symbols else 0,
                        len(edges) if edges else 0,
                        languages or [],
                        repo_id,
                    )
                )

                # Insert chunks if provided
                if chunks:
                    chunk_data = [
                        (
                            c.id, repo_id, c.file_path, c.language,
                            c.chunk_type, c.content, c.title,
                            c.start_line, c.end_line, c.token_estimate,
                            c.symbol_name, c.symbol_kind,
                        )
                        for c in chunks
                    ]
                    await cur.executemany(
                        """INSERT INTO chunks
                           (id, repository_id, path, language, chunk_type,
                            content, title, start_line, end_line,
                            token_estimate, symbol_name, symbol_kind)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT DO NOTHING""",
                        chunk_data
                    )

                # Insert symbols if provided
                if symbols:
                    symbol_data = [
                        (
                            s.id, repo_id, s.file_path, s.name,
                            s.qualified_name, s.kind, s.start_line,
                            s.end_line, s.signature, s.language,
                        )
                        for s in symbols
                    ]
                    await cur.executemany(
                        """INSERT INTO symbols
                           (id, repository_id, file_path, name, qualified_name,
                            kind, start_line, end_line, signature, language)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT DO NOTHING""",
                        symbol_data
                    )

                # Insert edges if provided
                if edges:
                    edge_data = [
                        (
                            e.source_path, repo_id, "file", e.source_path,
                            e.relationship, "file", e.target_path,
                        )
                        for e in edges
                    ]
                    await cur.executemany(
                        """INSERT INTO graph_edges
                           (source_id, repository_id, source_type, source_id,
                            relationship, target_type, target_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT DO NOTHING""",
                        edge_data
                    )

                await conn.commit()

    async def delete_repository(self, repo_id: str) -> bool:
        """Delete repository and all data."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM repositories WHERE id = %s RETURNING id",
                    (repo_id,)
                )
                found = await cur.fetchone()
                await conn.commit()

        return found is not None

    # ─── Chunks ───────────────────────────────────────────────────────────────

    async def get_chunks(self, repo_id: str, limit: int = 10000) -> list[Chunk]:
        """Get chunks for repository."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT id, repository_id, file_path, language, chunk_type,
                              content, title, start_line, end_line, token_estimate,
                              symbol_name, symbol_kind, embedding
                       FROM chunks LEFT JOIN chunk_embeddings USING (id)
                       WHERE repository_id = %s LIMIT %s""",
                    (repo_id, limit)
                )
                rows = await cur.fetchall()

        return [
            Chunk(
                id=row[0],
                repo_id=row[1],
                file_path=row[2],
                language=row[3],
                chunk_type=row[4],
                content=row[5],
                title=row[6],
                start_line=row[7],
                end_line=row[8],
                token_estimate=row[9],
                symbol_name=row[10],
                symbol_kind=row[11],
                embedding=row[12],
            )
            for row in rows
        ]

    async def update_embedded_count(self, repo_id: str, count: int) -> None:
        """Update embedded chunk count."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """UPDATE repositories
                       SET embedded_chunk_count = %s, updated_at = NOW()
                       WHERE id = %s""",
                    (count, repo_id)
                )
                await conn.commit()

    # ─── Symbols ──────────────────────────────────────────────────────────────

    async def get_symbols(self, repo_id: str) -> list[Symbol]:
        """Get symbols for repository."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT id, repository_id, file_path, name, qualified_name,
                              kind, start_line, end_line, signature, language
                       FROM symbols WHERE repository_id = %s""",
                    (repo_id,)
                )
                rows = await cur.fetchall()

        return [
            Symbol(
                id=row[0],
                repo_id=row[1],
                file_path=row[2],
                name=row[3],
                qualified_name=row[4],
                kind=row[5],
                start_line=row[6],
                end_line=row[7],
                signature=row[8],
                language=row[9],
            )
            for row in rows
        ]

    # ─── Graph Edges ──────────────────────────────────────────────────────────

    async def get_edges(self, repo_id: str) -> list[GraphEdge]:
        """Get graph edges for repository."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT source_id, target_id, relationship
                       FROM graph_edges WHERE repository_id = %s""",
                    (repo_id,)
                )
                rows = await cur.fetchall()

        return [
            GraphEdge(
                source_path=str(row[0]),
                target_path=str(row[1]),
                relationship=row[2],
            )
            for row in rows
        ]

    async def get_file_neighbors(self, repo_id: str, file_path: str) -> list[str]:
        """Get files that import or are imported by the given file."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT DISTINCT target_id FROM graph_edges
                       WHERE repository_id = %s AND source_id = %s
                       UNION
                       SELECT DISTINCT source_id FROM graph_edges
                       WHERE repository_id = %s AND target_id = %s""",
                    (repo_id, file_path, repo_id, file_path)
                )
                rows = await cur.fetchall()

        return [str(row[0]) for row in rows]

    # ─── Agent Runs ───────────────────────────────────────────────────────────

    async def save_agent_run(self, run: AgentRun) -> None:
        """Save agent run."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO agent_runs
                       (id, repository_id, agent_type, input, output,
                        status, model, error, started_at, completed_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET
                       output = EXCLUDED.output,
                       status = EXCLUDED.status,
                       error = EXCLUDED.error,
                       completed_at = EXCLUDED.completed_at""",
                    (
                        run.id, run.repo_id, run.agent_type,
                        run.input, run.output, run.status.value,
                        run.model, run.error, run.started_at, run.completed_at
                    )
                )
                await conn.commit()

    async def get_agent_run(self, run_id: str) -> AgentRun | None:
        """Get agent run."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT id, repository_id, agent_type, input, output,
                              status, model, error, started_at, completed_at
                       FROM agent_runs WHERE id = %s""",
                    (run_id,)
                )
                row = await cur.fetchone()

        if not row:
            return None

        return AgentRun(
            id=row[0],
            repo_id=row[1],
            agent_type=row[2],
            input=row[3],
            output=row[4],
            status=AgentRunStatus(row[5]),
            model=row[6],
            error=row[7],
            started_at=row[8].isoformat() if row[8] else None,
            completed_at=row[9].isoformat() if row[9] else None,
        )

    async def get_agent_runs(self, repo_id: str) -> list[AgentRun]:
        """Get all agent runs for a repository, sorted by started_at DESC."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT id, repository_id, agent_type, input, output,
                              status, model, error, started_at, completed_at
                       FROM agent_runs WHERE repository_id = %s
                       ORDER BY started_at DESC""",
                    (repo_id,)
                )
                rows = await cur.fetchall()

        return [
            AgentRun(
                id=row[0],
                repo_id=row[1],
                agent_type=row[2],
                input=row[3],
                output=row[4],
                status=AgentRunStatus(row[5]),
                model=row[6],
                error=row[7],
                started_at=row[8].isoformat() if row[8] else None,
                completed_at=row[9].isoformat() if row[9] else None,
            )
            for row in rows
        ]

    async def save_feedback(
        self,
        run_id: str,
        rating: int,
        label: FeedbackLabel | None,
        comment: str | None,
    ) -> FeedbackRecord:
        """Save feedback to the database."""
        import uuid
        feedback_id = str(uuid.uuid4())
        created_at = datetime.now(UTC)
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO feedback
                       (id, agent_run_id, rating, label, comment, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        feedback_id, run_id, rating,
                        label.value if label else None,
                        comment, created_at
                    )
                )
                await conn.commit()

        return FeedbackRecord(
            id=feedback_id,
            run_id=run_id,
            rating=rating,
            label=label,
            comment=comment,
            created_at=created_at.isoformat(),
        )

    async def get_feedback(self) -> list[FeedbackRecord]:
        """Get all feedback records."""
        async with self._get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT id, agent_run_id, rating, label, comment, created_at
                       FROM feedback ORDER BY created_at DESC"""
                )
                rows = await cur.fetchall()

        return [
            FeedbackRecord(
                id=row[0],
                run_id=row[1],
                rating=row[2],
                label=FeedbackLabel(row[3]) if row[3] else None,
                comment=row[4],
                created_at=row[5].isoformat() if row[5] else None,
            )
            for row in rows
        ]



# Global instance
persistent_store: PersistentIndexStore | None = None


def get_persistent_store() -> PersistentIndexStore:
    """Get global persistent store instance."""
    global persistent_store
    if persistent_store is None:
        persistent_store = PersistentIndexStore()
    return persistent_store
