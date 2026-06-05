"""LLM adapter package — provider-agnostic interface for Engineering Brain."""

from app.llm.ollama_adapter import OllamaAdapter, ollama_adapter

__all__ = ["OllamaAdapter", "ollama_adapter"]
