"""API routes — all HTTP endpoints for Engineering Brain.

Phase 1 routes:
  GET  /health
  POST /api/repositories/index
  GET  /api/repositories
  GET  /api/repositories/{repo_id}
  GET  /api/repositories/{repo_id}/status
  DELETE /api/repositories/{repo_id}
  POST /api/search
  POST /api/chat
  POST /api/chat/stream
  POST /api/architecture-summary
  GET  /api/llm/status

Phase 2 routes:
  GET  /api/repositories/{repo_id}/symbols   — list extracted symbols
  GET  /api/repositories/{repo_id}/graph     — file dependency graph
  POST /api/architecture-summary/deep        — LLM-powered architecture narrative
"""

import json
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    ArchitectureSummaryRequest,
    ArchitectureSummaryResponse,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    GraphResponse,
    IndexJobStatusResponse,
    IndexRepositoryRequest,
    RepositoryIndexResponse,
    RepositoryRecord,
    SearchRequest,
    SearchResponse,
    SymbolListResponse,
    AgentRun,
    AgentRunStatus,
    PRReviewRequest,
)
from app.services.architecture_service import architecture_service
from app.services.chat_service import chat_service
from app.services.index_store import index_store
from app.services.repository_service import repository_service
from app.services.search_service import search_service
from app.agents.code_review_agent import code_review_agent

router = APIRouter()


# ─── Health ──────────────────────────────────────────────────────────────────

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ─── Repository management ───────────────────────────────────────────────────

@router.post("/api/repositories/index", response_model=RepositoryIndexResponse)
async def index_repository(
    payload: IndexRepositoryRequest,
    background_tasks: BackgroundTasks,
) -> RepositoryIndexResponse:
    return await repository_service.index_repository(payload, background_tasks)


@router.get("/api/repositories", response_model=list[RepositoryRecord])
async def list_repositories() -> list[RepositoryRecord]:
    return await index_store.list_repositories()


@router.get("/api/repositories/{repo_id}", response_model=RepositoryRecord)
async def get_repository(repo_id: str) -> RepositoryRecord:
    repository = await index_store.get_repository(repo_id)
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repository


@router.get("/api/repositories/{repo_id}/status", response_model=IndexJobStatusResponse)
async def get_repository_status(repo_id: str) -> IndexJobStatusResponse:
    """Poll indexing progress. Returns current status and embedded chunk count."""
    repository = await index_store.get_repository(repo_id)
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return IndexJobStatusResponse(
        repo_id=repo_id,
        status=repository.status,
        file_count=repository.file_count,
        chunk_count=repository.chunk_count,
        embedded_chunk_count=repository.embedded_chunk_count,
        symbol_count=repository.symbol_count,
        error=repository.error,
    )


@router.delete("/api/repositories/{repo_id}", status_code=204)
async def delete_repository(repo_id: str) -> None:
    """Permanently delete a repository record and all its indexed data."""
    found = await index_store.delete_repository(repo_id)
    if not found:
        raise HTTPException(status_code=404, detail="Repository not found")


# ─── Phase 2: Symbol & Graph endpoints ───────────────────────────────────────

@router.get("/api/repositories/{repo_id}/symbols", response_model=SymbolListResponse)
async def get_symbols(
    repo_id: str,
    kind: str | None = None,
    language: str | None = None,
    q: str | None = None,
    limit: int = 100,
) -> SymbolListResponse:
    """List extracted symbols for a repository.

    Query params:
      kind     — filter by symbol kind (function, class, method, etc.)
      language — filter by language (python, typescript, etc.)
      q        — search by symbol name (case-insensitive substring)
      limit    — max results (default 100)
    """
    if await index_store.get_repository(repo_id) is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    symbols = await index_store.get_symbols(repo_id)

    if kind:
        symbols = [s for s in symbols if s.kind == kind]
    if language:
        symbols = [s for s in symbols if s.language == language]
    if q:
        q_lower = q.lower()
        symbols = [s for s in symbols if q_lower in s.name.lower()]

    total = len(symbols)
    return SymbolListResponse(
        repo_id=repo_id,
        symbols=symbols[:limit],
        total=total,
    )


@router.get("/api/repositories/{repo_id}/graph", response_model=GraphResponse)
async def get_graph(repo_id: str, max_nodes: int = 80) -> GraphResponse:
    """Return the file dependency graph for visualization.

    Returns nodes (files) and edges (import relationships).
    Large graphs are trimmed to max_nodes most-connected files.
    """
    if await index_store.get_repository(repo_id) is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    edges = await index_store.get_edges(repo_id)
    chunks = await index_store.get_chunks(repo_id)

    # Build node set from edges
    file_paths: set[str] = set()
    for edge in edges:
        file_paths.add(edge.source_path)
        file_paths.add(edge.target_path)

    # Count chunks per file for node sizing
    chunk_counts: dict[str, int] = {}
    lang_map: dict[str, str] = {}
    for chunk in chunks:
        chunk_counts[chunk.file_path] = chunk_counts.get(chunk.file_path, 0) + 1
        if chunk.file_path not in lang_map:
            lang_map[chunk.file_path] = chunk.language

    # Trim to most-connected files
    from collections import Counter
    degree = Counter()
    for edge in edges:
        degree[edge.source_path] += 1
        degree[edge.target_path] += 1

    top_files = {fp for fp, _ in degree.most_common(max_nodes)}
    # Always include files present in our index even if not in edges
    if len(top_files) < max_nodes:
        for fp in list(file_paths)[:max_nodes - len(top_files)]:
            top_files.add(fp)

    nodes = [
        {
            "id": fp,
            "label": fp.split("/")[-1],
            "language": lang_map.get(fp, "unknown"),
            "chunk_count": chunk_counts.get(fp, 0),
            "degree": degree.get(fp, 0),
        }
        for fp in sorted(top_files)
    ]

    filtered_edges = [
        {
            "source": e.source_path,
            "target": e.target_path,
            "relationship": e.relationship,
        }
        for e in edges
        if e.source_path in top_files and e.target_path in top_files
    ]

    return GraphResponse(
        repo_id=repo_id,
        nodes=nodes,
        edges=filtered_edges,
        total_nodes=len(file_paths),
        total_edges=len(edges),
    )


# ─── Search ──────────────────────────────────────────────────────────────────

@router.post("/api/search", response_model=SearchResponse)
async def search(payload: SearchRequest) -> SearchResponse:
    return await search_service.search(payload)


# ─── Chat ────────────────────────────────────────────────────────────────────

@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    return await chat_service.answer(payload)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest) -> StreamingResponse:
    """SSE streaming chat. Yields token events then a final done event."""

    async def _generate():
        async for event in chat_service.answer_stream(payload):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/chat/feedback", response_model=FeedbackResponse)
async def submit_feedback(payload: FeedbackRequest) -> FeedbackResponse:
    """Submit user feedback for an agent run or chat session."""
    record = await index_store.save_feedback(
        run_id=payload.run_id,
        rating=payload.rating,
        label=payload.label,
        comment=payload.comment,
    )
    return FeedbackResponse(feedback=record)


# ─── Architecture Summary ─────────────────────────────────────────────────────

@router.post("/api/architecture-summary", response_model=ArchitectureSummaryResponse)
async def architecture_summary(payload: ArchitectureSummaryRequest) -> ArchitectureSummaryResponse:
    """Static architecture summary — instant, no LLM required."""
    return await architecture_service.summarize(payload)


@router.post("/api/architecture-summary/deep", response_model=ArchitectureSummaryResponse)
async def architecture_summary_deep(
    payload: ArchitectureSummaryRequest,
) -> ArchitectureSummaryResponse:
    """LLM-powered architecture narrative (async — uses Ollama).

    Falls back to static summary if Ollama is unavailable.
    """
    return await architecture_service.summarize_deep(payload)


# ─── LLM status ──────────────────────────────────────────────────────────────

@router.get("/api/llm/status")
async def llm_status() -> dict[str, object]:
    """Check if Ollama is available and return model config."""
    from app.core.config import settings
    from app.llm.ollama_adapter import ollama_adapter

    available = await ollama_adapter.is_available()
    return {
        "ollama_available": available,
        "chat_model": settings.ollama_chat_model,
        "embed_model": settings.ollama_embed_model,
        "llm_enabled": settings.enable_llm,
        "embeddings_enabled": settings.enable_embeddings,
    }


# ─── Phase 3: PR Review Agent endpoints ───────────────────────────────────────

@router.post("/api/repositories/{repo_id}/pr-reviews", response_model=AgentRun)
async def trigger_pr_review(
    repo_id: str,
    payload: PRReviewRequest,
    background_tasks: BackgroundTasks,
) -> AgentRun:
    """Trigger a manual code review for a PR in the background."""
    if await index_store.get_repository(repo_id) is None:
        raise HTTPException(status_code=404, detail="Repository not found")
        
    payload.repo_id = repo_id
    run_id = str(uuid.uuid4())
    started_at = datetime.now(UTC).isoformat()
    
    # Pre-create the AgentRun record in running status
    run_record = AgentRun(
        id=run_id,
        repo_id=repo_id,
        agent_type="pr_review",
        status=AgentRunStatus.running,
        input=payload.model_dump(),
        started_at=started_at,
    )
    await index_store.save_agent_run(run_record)
    
    # Dispatch code review agent to background task
    background_tasks.add_task(code_review_agent.review_pr, payload, run_id)
    
    return run_record


@router.get("/api/repositories/{repo_id}/pr-reviews", response_model=list[AgentRun])
async def list_pr_reviews(repo_id: str) -> list[AgentRun]:
    """List all code review runs for a repository."""
    if await index_store.get_repository(repo_id) is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return await index_store.get_agent_runs(repo_id)


@router.get("/api/repositories/{repo_id}/pr-reviews/{run_id}", response_model=AgentRun)
async def get_pr_review(repo_id: str, run_id: str) -> AgentRun:
    """Get the details of a specific PR review run."""
    run = await index_store.get_agent_run(run_id)
    if not run or run.repo_id != repo_id:
        raise HTTPException(status_code=404, detail="PR review run not found")
    return run

