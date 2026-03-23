"""LLM abstraction service for non-RAG responses."""

from typing import Optional

from app.services.rag_chain import RAGChain


class LLMService:
    """Minimal LLM abstraction using existing provider stack."""

    def __init__(self, rag_chain: Optional[RAGChain] = None):
        self._rag_chain = rag_chain or RAGChain()

    def generate(self, prompt: str) -> str:
        """Generate a direct LLM response without retrieval."""
        return self._rag_chain._llm_generate(prompt)

