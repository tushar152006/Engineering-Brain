"""Ollama adapter — typed HTTP client for Ollama's REST API.

This adapter wraps Ollama's /api/chat and /api/embeddings endpoints.
All methods fail gracefully: if Ollama is not running they return None
so the rest of the system degrades to keyword-only mode without crashing.

Docs: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=30.0, pool=5.0)


class OllamaAdapter:
    """Async HTTP adapter for Ollama local inference."""

    def __init__(self) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    async def is_available(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Chat / text generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.2,
    ) -> str | None:
        """Generate a single-shot text completion via Ollama.

        Returns the generated text, or None if Ollama is unavailable.
        """
        if not settings.enable_llm:
            return None

        chat_model = model or settings.ollama_chat_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": chat_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "").strip()
        except httpx.ConnectError:
            logger.warning("Ollama not reachable — falling back to citation-only mode")
            return None
        except Exception as exc:
            logger.warning("Ollama generate failed: %s", exc)
            return None

    async def generate_stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """Streaming text generation — yields token chunks as they arrive."""
        if not settings.enable_llm:
            return

        chat_model = model or settings.ollama_chat_model
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": chat_model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream(
                    "POST", f"{self._base_url}/api/chat", json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield token
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            logger.warning("Ollama stream failed: %s", exc)
            return

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    async def embed(
        self,
        text: str,
        *,
        model: str | None = None,
    ) -> list[float] | None:
        """Generate an embedding vector for a single text input.

        Returns a list[float] or None if Ollama is unavailable.
        """
        if not settings.enable_embeddings:
            return None

        embed_model = model or settings.ollama_embed_model

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": embed_model, "prompt": text},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("embedding")
        except httpx.ConnectError:
            return None
        except Exception as exc:
            logger.warning("Ollama embed failed: %s", exc)
            return None

    async def embed_batch(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[list[float] | None]:
        """Embed a batch of texts sequentially.

        Returns a list aligned with the input; entries are None on failure.
        """
        results: list[list[float] | None] = []
        for text in texts:
            results.append(await self.embed(text, model=model))
        return results


# Singleton — import and use directly
ollama_adapter = OllamaAdapter()
