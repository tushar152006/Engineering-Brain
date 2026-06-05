"""Chat service — retrieval-augmented generation with graph-expanded context.

Pipeline (Phase 2):
  1. Embed the user's question (if Ollama available)
  2. Hybrid-rank chunks (semantic + keyword + symbol boost)
  3. Expand graph neighbors of top hits → boost second-pass ranking
  4. Build a compact evidence pack from top citations (includes symbol info)
  5. Call Ollama to synthesize a senior-engineer-style answer
  6. Return answer + citations + confidence + model_used

Fallback: if Ollama is unavailable, returns citation-only response so the
product keeps working without an LLM.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException

from app.core.config import settings
from app.llm.ollama_adapter import ollama_adapter
from app.models.schemas import ChatRequest, ChatResponse, Citation
from app.retrieval.ranking import expand_graph_neighbors, hybrid_rank_chunks
from app.services.index_store import index_store

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a senior software engineer with deep expertise in this codebase.
Your job is to answer engineering questions using ONLY the provided source evidence.

Rules:
- Ground every important claim in a file path and line range from the evidence.
- When the evidence shows symbol names (functions, classes), reference them by name.
- Clearly distinguish facts (supported by evidence) from inferences (your reasoning).
- If the evidence is insufficient, say so honestly — do not invent details.
- Write in plain, precise technical prose. No fluff.
- Keep your answer under 500 words unless the question genuinely requires more depth.
- Do not repeat the question back to the user.
- At the very end of your response, output a block starting with '=== UNKNOWNS ===' followed by a comma-separated list of things you do not know based on the evidence. If there are no unknowns, write 'None'.
"""

_EVIDENCE_TEMPLATE = """\
=== SOURCE EVIDENCE ===
{evidence}

=== QUESTION ===
{question}
"""


def _build_evidence_block(citations: list[Citation]) -> str:
    lines = []
    for i, c in enumerate(citations[:6], start=1):
        lines.append(
            f"[{i}] {c.file_path}:{c.start_line}-{c.end_line}  ({c.title})\n"
            f"    {c.excerpt}"
        )
    return "\n\n".join(lines)


def _confidence(citations: list[Citation]) -> str:
    if len(citations) >= 4:
        return "high"
    if len(citations) >= 2:
        return "medium"
    return "low"


class ChatService:
    async def answer(self, payload: ChatRequest) -> ChatResponse:
        repository = index_store.get_repository(payload.repo_id)
        if repository is None:
            raise HTTPException(status_code=404, detail="Repository not found")

        # 1. Embed the query (graceful None if Ollama unavailable)
        query_embedding = await ollama_adapter.embed(payload.question)

        chunks = index_store.get_chunks(payload.repo_id)

        # 2. First-pass hybrid retrieval
        citations = hybrid_rank_chunks(
            payload.question,
            query_embedding,
            chunks,
            payload.limit,
        )

        # 3. Graph expansion — find files neighboring top hits and re-rank
        if citations and repository.edge_count > 0:
            neighbors = expand_graph_neighbors(
                citations,
                lambda fp: index_store.get_file_neighbors(payload.repo_id, fp),
            )
            if neighbors:
                citations = hybrid_rank_chunks(
                    payload.question,
                    query_embedding,
                    chunks,
                    payload.limit,
                    graph_neighbors=neighbors,
                )

        if not citations:
            return ChatResponse(
                answer=(
                    "I could not find strong evidence for that question in the indexed files. "
                    "Try asking with a specific filename, module name, function name, "
                    "or architecture term."
                ),
                citations=[],
                confidence="low",
                model_used=None,
            )

        # 4. Build evidence pack
        evidence_block = _build_evidence_block(citations)
        prompt = _EVIDENCE_TEMPLATE.format(
            evidence=evidence_block,
            question=payload.question,
        )

        # 5. LLM synthesis
        llm_answer = await ollama_adapter.generate(
            prompt,
            system=_SYSTEM_PROMPT,
            temperature=0.15,
        )

        conf = _confidence(citations)
        model_name = f"ollama/{settings.ollama_chat_model}" if llm_answer else None

        unknowns = []
        if llm_answer and "=== UNKNOWNS ===" in llm_answer:
            parts = llm_answer.split("=== UNKNOWNS ===")
            llm_answer = parts[0].strip()
            unknowns_text = parts[1].strip()
            if unknowns_text.lower() != "none":
                unknowns = [u.strip() for u in unknowns_text.split(",") if u.strip()]

        if llm_answer:
            return ChatResponse(
                answer=llm_answer,
                citations=citations,
                confidence=conf,
                unknowns=unknowns,
                model_used=model_name,
            )

        # 6. Fallback: citation-only mode
        evidence_lines = [
            f"• {c.file_path}:{c.start_line}-{c.end_line}  {c.title}"
            for c in citations[:5]
        ]
        fallback_answer = (
            f"Found {len(citations)} relevant references in **{repository.name}**. "
            "Ollama is not available — showing raw citations:\n\n"
            + "\n".join(evidence_lines)
            + "\n\n_Start Ollama and re-ask for a synthesized answer._"
        )
        return ChatResponse(
            answer=fallback_answer,
            citations=citations,
            confidence=conf,
            unknowns=[],
            model_used=None,
        )

    async def answer_stream(self, payload: ChatRequest):
        """Async generator for SSE streaming chat.

        Yields dicts:
          {"type": "token", "token": "<text>"}   — one per Ollama chunk
          {"type": "done", "citations": [...], "confidence": "...", "model_used": "..."}
        """
        repository = index_store.get_repository(payload.repo_id)
        if repository is None:
            raise HTTPException(status_code=404, detail="Repository not found")

        query_embedding = await ollama_adapter.embed(payload.question)
        chunks = index_store.get_chunks(payload.repo_id)

        # First-pass retrieval
        citations = hybrid_rank_chunks(
            payload.question,
            query_embedding,
            chunks,
            payload.limit,
        )

        # Graph expansion
        if citations and repository.edge_count > 0:
            neighbors = expand_graph_neighbors(
                citations,
                lambda fp: index_store.get_file_neighbors(payload.repo_id, fp),
            )
            if neighbors:
                citations = hybrid_rank_chunks(
                    payload.question,
                    query_embedding,
                    chunks,
                    payload.limit,
                    graph_neighbors=neighbors,
                )

        conf = _confidence(citations)

        if not citations:
            yield {
                "type": "done",
                "citations": [],
                "confidence": "low",
                "model_used": None,
            }
            return

        evidence_block = _build_evidence_block(citations)
        prompt = _EVIDENCE_TEMPLATE.format(
            evidence=evidence_block,
            question=payload.question,
        )

        # Stream tokens
        got_any = False
        accumulated = ""
        async for token in ollama_adapter.generate_stream(
            prompt,
            system=_SYSTEM_PROMPT,
            temperature=0.15,
        ):
            got_any = True
            accumulated += token
            yield {"type": "token", "token": token}

        model_name = f"ollama/{settings.ollama_chat_model}" if got_any else None

        if not got_any:
            # Ollama unavailable — emit fallback text as a single token
            evidence_lines = [
                f"• {c.file_path}:{c.start_line}-{c.end_line}  {c.title}"
                for c in citations[:5]
            ]
            fallback = (
                f"Found {len(citations)} relevant references in **{repository.name}**. "
                "Ollama is not available — showing raw citations:\n\n"
                + "\n".join(evidence_lines)
                + "\n\n_Start Ollama and re-ask for a synthesized answer._"
            )
            yield {"type": "token", "token": fallback}

        unknowns = []
        if got_any and "=== UNKNOWNS ===" in accumulated:
            parts = accumulated.split("=== UNKNOWNS ===")
            unknowns_text = parts[1].strip()
            if unknowns_text.lower() != "none":
                unknowns = [u.strip() for u in unknowns_text.split(",") if u.strip()]

        yield {
            "type": "done",
            "citations": [c.model_dump() for c in citations],
            "confidence": conf,
            "unknowns": unknowns,
            "model_used": model_name,
        }


chat_service = ChatService()
