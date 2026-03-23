"""Retrieval agent wrapping existing RAG/orchestration logic."""

from typing import Dict, List, Optional

from app.models.document import Document
from app.services.query_orchestrator import QueryOrchestrator
from app.services.rag_chain import RAGChain


class RetrievalAgent:
    """Wrapper over existing retrieval stack."""

    def __init__(self, rag_chain: Optional[RAGChain] = None):
        self.rag_chain = rag_chain or RAGChain()

    def answer(
        self,
        *,
        query: str,
        document: Document,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict:
        """
        Route to orchestrator for structured docs, else use standard RAG.
        Returns the same shape as RAGChain.query().
        """
        if getattr(document, "sqlite_path", None):
            orchestrator = QueryOrchestrator(
                document=document,
                rag_query_fn=lambda vs, q, **kw: self.rag_chain.query(vs, q, **kw),
                llm_callable=self.rag_chain._llm_generate,
            )
            return orchestrator.route_query(
                query,
                system_prompt=system_prompt,
                conversation_history=conversation_history,
            )

        return self.rag_chain.query(
            document.vector_store_path,
            query,
            system_prompt=system_prompt,
            conversation_history=conversation_history,
        )

