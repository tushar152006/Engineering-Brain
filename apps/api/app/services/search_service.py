"""Search service — hybrid keyword + semantic search."""

from __future__ import annotations

from fastapi import HTTPException

from app.llm.ollama_adapter import ollama_adapter
from app.models.schemas import SearchRequest, SearchResponse
from app.retrieval.ranking import hybrid_rank_chunks
from app.services.index_store import index_store


class SearchService:
    async def search(self, payload: SearchRequest) -> SearchResponse:
        if await index_store.get_repository(payload.repo_id) is None:
            raise HTTPException(status_code=404, detail="Repository not found")

        # Embed the query for semantic ranking (None if Ollama unavailable)
        query_embedding = await ollama_adapter.embed(payload.query)

        chunks = await index_store.get_chunks(payload.repo_id)
        results = hybrid_rank_chunks(payload.query, query_embedding, chunks, payload.limit)
        return SearchResponse(query=payload.query, results=results)


search_service = SearchService()
