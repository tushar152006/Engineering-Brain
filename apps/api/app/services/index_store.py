"""In-memory and Persistent index store interface supporting PostgreSQL transition.

This class acts as a transparent async interface for both in-memory JSON storage
and PostgreSQL persistence. It switches dynamically based on settings.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

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


class InMemoryIndexStore:
    """Thread-safe index store with local JSON persistence and dynamic PostgreSQL routing."""

    def __init__(self, storage_path: str | None = None) -> None:
        self._lock = RLock()
        self._repositories: dict[str, RepositoryRecord] = {}
        self._chunks_by_repo: dict[str, list[Chunk]] = {}
        self._symbols_by_repo: dict[str, list[Symbol]] = {}
        self._edges_by_repo: dict[str, list[GraphEdge]] = {}
        self._feedback: dict[str, FeedbackRecord] = {}
        self._agent_runs: dict[str, AgentRun] = {}
        self._storage_path = Path(storage_path or settings.index_store_path)
        self._load()

    def _is_db(self) -> bool:
        return bool(settings.use_persistent_store and settings.database_url)

    async def create_repository(
        self,
        repo_id: str,
        name: str,
        source: RepositorySource,
        source_url: str | None,
    ) -> RepositoryRecord:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().create_repository(repo_id, name, source, source_url)

        record = RepositoryRecord(
            id=repo_id,
            name=name,
            source=source,
            source_url=source_url,
            indexed_at=datetime.now(UTC).isoformat(),
            status=IndexingStatus.indexing,
        )
        with self._lock:
            self._repositories[repo_id] = record
            self._chunks_by_repo.setdefault(repo_id, [])
            self._symbols_by_repo.setdefault(repo_id, [])
            self._edges_by_repo.setdefault(repo_id, [])
            self._save()
        return record

    async def upsert_repository(
        self,
        repo_id: str,
        name: str,
        source: RepositorySource,
        source_url: str | None,
        chunks: list[Chunk],
        languages: list[str],
        file_count: int,
        status: IndexingStatus = IndexingStatus.ready,
        symbols: list[Symbol] | None = None,
        edges: list[GraphEdge] | None = None,
    ) -> RepositoryRecord:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            await get_persistent_store().upsert_repository(
                repo_id=repo_id,
                name=name,
                source=source,
                source_url=source_url,
                chunks=chunks,
                symbols=symbols,
                edges=edges,
                languages=languages,
                file_count=file_count,
                status=status,
            )
            record = await get_persistent_store().get_repository(repo_id)
            if record:
                return record

        embedded_count = sum(1 for c in chunks if c.embedding is not None)
        sym_list = symbols or []
        edge_list = edges or []
        record = RepositoryRecord(
            id=repo_id,
            name=name,
            source=source,
            source_url=source_url,
            file_count=file_count,
            chunk_count=len(chunks),
            embedded_chunk_count=embedded_count,
            symbol_count=len(sym_list),
            edge_count=len(edge_list),
            languages=languages,
            indexed_at=datetime.now(UTC).isoformat(),
            status=status,
        )
        with self._lock:
            self._repositories[repo_id] = record
            self._chunks_by_repo[repo_id] = chunks
            if symbols is not None:
                self._symbols_by_repo[repo_id] = sym_list
            if edges is not None:
                self._edges_by_repo[repo_id] = edge_list
            self._save()
        return record

    async def set_repository_status(
        self,
        repo_id: str,
        status: IndexingStatus,
        *,
        error: str | None = None,
    ) -> None:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            await get_persistent_store().set_repository_status(repo_id, status, error=error)
            return

        with self._lock:
            repo = self._repositories.get(repo_id)
            if repo is None:
                return
            self._repositories[repo_id] = repo.model_copy(
                update={"status": status, "error": error}
            )
            self._save()

    async def update_embedded_count(self, repo_id: str, count: int) -> None:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            await get_persistent_store().update_embedded_count(repo_id, count)
            return

        with self._lock:
            repo = self._repositories.get(repo_id)
            if repo is None:
                return
            self._repositories[repo_id] = repo.model_copy(
                update={"embedded_chunk_count": count}
            )

    async def list_repositories(self) -> list[RepositoryRecord]:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().list_repositories()

        with self._lock:
            return sorted(
                self._repositories.values(),
                key=lambda repo: repo.indexed_at,
                reverse=True,
            )

    async def get_repository(self, repo_id: str) -> RepositoryRecord | None:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().get_repository(repo_id)

        with self._lock:
            return self._repositories.get(repo_id)

    async def get_chunks(self, repo_id: str) -> list[Chunk]:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().get_chunks(repo_id)

        with self._lock:
            return list(self._chunks_by_repo.get(repo_id, []))

    async def get_symbols(self, repo_id: str) -> list[Symbol]:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().get_symbols(repo_id)

        with self._lock:
            return list(self._symbols_by_repo.get(repo_id, []))

    async def get_edges(self, repo_id: str) -> list[GraphEdge]:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().get_edges(repo_id)

        with self._lock:
            return list(self._edges_by_repo.get(repo_id, []))

    async def delete_repository(self, repo_id: str) -> bool:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().delete_repository(repo_id)

        with self._lock:
            if repo_id not in self._repositories:
                return False
            del self._repositories[repo_id]
            self._chunks_by_repo.pop(repo_id, None)
            self._symbols_by_repo.pop(repo_id, None)
            self._edges_by_repo.pop(repo_id, None)
            self._save()
        return True

    async def get_file_neighbors(self, repo_id: str, file_path: str) -> list[str]:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().get_file_neighbors(repo_id, file_path)

        edges = await self.get_edges(repo_id)
        neighbors: set[str] = set()
        for edge in edges:
            if edge.source_path == file_path:
                neighbors.add(edge.target_path)
            elif edge.target_path == file_path:
                neighbors.add(edge.source_path)
        return sorted(neighbors)

    async def get_symbols_for_file(self, repo_id: str, file_path: str) -> list[Symbol]:
        symbols = await self.get_symbols(repo_id)
        return [s for s in symbols if s.file_path == file_path]

    async def save_feedback(self, run_id: str, rating: int, label: FeedbackLabel | None, comment: str | None) -> FeedbackRecord:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().save_feedback(run_id, rating, label, comment)

        import uuid
        record = FeedbackRecord(
            id=str(uuid.uuid4()),
            run_id=run_id,
            rating=rating,
            label=label,
            comment=comment,
            created_at=datetime.now(UTC).isoformat(),
        )
        with self._lock:
            self._feedback[record.id] = record
            self._save()
        return record

    async def get_feedback(self) -> list[FeedbackRecord]:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().get_feedback()

        with self._lock:
            return list(self._feedback.values())

    async def save_agent_run(self, run: AgentRun) -> None:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            await get_persistent_store().save_agent_run(run)
            return

        with self._lock:
            self._agent_runs[run.id] = run
            self._save()

    async def get_agent_runs(self, repo_id: str) -> list[AgentRun]:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().get_agent_runs(repo_id)

        with self._lock:
            return sorted(
                [run for run in self._agent_runs.values() if run.repo_id == repo_id],
                key=lambda run: run.started_at,
                reverse=True,
            )

    async def get_agent_run(self, run_id: str) -> AgentRun | None:
        if self._is_db():
            from app.db.persistent_store import get_persistent_store
            return await get_persistent_store().get_agent_run(run_id)

        with self._lock:
            return self._agent_runs.get(run_id)

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._repositories = {
                item["id"]: RepositoryRecord.model_validate(item)
                for item in data.get("repositories", [])
            }
            self._chunks_by_repo = {
                repo_id: [Chunk.model_validate(chunk) for chunk in chunks]
                for repo_id, chunks in data.get("chunks_by_repo", {}).items()
            }
            self._symbols_by_repo = {
                repo_id: [Symbol.model_validate(s) for s in syms]
                for repo_id, syms in data.get("symbols_by_repo", {}).items()
            }
            self._edges_by_repo = {
                repo_id: [GraphEdge.model_validate(e) for e in edges]
                for repo_id, edges in data.get("edges_by_repo", {}).items()
            }
            self._feedback = {
                item["id"]: FeedbackRecord.model_validate(item)
                for item in data.get("feedback", [])
            }
            self._agent_runs = {
                item["id"]: AgentRun.model_validate(item)
                for item in data.get("agent_runs", [])
            }
        except Exception:
            self._repositories = {}
            self._chunks_by_repo = {}
            self._symbols_by_repo = {}
            self._edges_by_repo = {}
            self._feedback = {}
            self._agent_runs = {}

    def _save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "repositories": [
                repo.model_dump(mode="json") for repo in self._repositories.values()
            ],
            "chunks_by_repo": {
                repo_id: [chunk.model_dump(mode="json") for chunk in chunks]
                for repo_id, chunks in self._chunks_by_repo.items()
            },
            "symbols_by_repo": {
                repo_id: [sym.model_dump(mode="json") for sym in syms]
                for repo_id, syms in self._symbols_by_repo.items()
            },
            "edges_by_repo": {
                repo_id: [edge.model_dump(mode="json") for edge in edges]
                for repo_id, edges in self._edges_by_repo.items()
            },
            "feedback": [
                f.model_dump(mode="json") for f in self._feedback.values()
            ],
            "agent_runs": [
                run.model_dump(mode="json") for run in self._agent_runs.values()
            ],
        }
        tmp_path = self._storage_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self._storage_path)


index_store = InMemoryIndexStore()
