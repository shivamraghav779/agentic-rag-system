"""General fallback agent (non-retrieval)."""

from typing import Dict

from app.services.llm_service import LLMService


class GeneralAgent:
    """Direct LLM response agent."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def answer(self, query: str) -> Dict:
        response = self.llm_service.generate(
            f"You are a helpful assistant. Answer clearly and concisely.\n\nUser query: {query}"
        )
        return {"answer": response, "source_documents": []}

