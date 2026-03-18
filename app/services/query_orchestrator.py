"""
Query orchestrator for hybrid SQL + RAG pipeline (Excel/CSV/DB documents).
Routes each query to SQL Agent or RAG based on classification (notebook-aligned).
"""
from typing import Any, Callable, Dict, List, Optional

from app.models.document import Document
from app.services.sql_agent_service import run_sql_agent
from app.prompts.templates import CLASSIFY_QUERY_PROMPT


# SQL-like keywords: aggregations, calculations, comparisons
SQL_KEYWORDS = [
    "count", "sum", "total", "average", "avg", "max", "min",
    "group by", "aggregate", "calculate", "compute",
    "how many", "number of", "total number",
    "better", "best", "worst", "performance", "compare",
    "yearly", "monthly", "quarterly", "year to date", "ytd",
    "profit", "loss", "p&l", "pl_ytd", "pl_mtd", "pl_qtd",
]

# RAG-like: descriptive, explanatory
RAG_KEYWORDS = [
    "what", "who", "when", "where", "why", "how",
    "describe", "explain", "tell me about", "information about",
    "details", "specific", "which security", "which fund",
]


class QueryOrchestrator:
    """
    Routes queries to SQL Agent or RAG based on query type.
    Used only for documents that have sqlite_path (Excel/CSV/DB).
    """

    def __init__(
        self,
        document: Document,
        rag_query_fn: Callable[..., Dict[str, Any]],
        llm_callable: Callable[[str], str],
    ):
        self.document = document
        self.rag_query_fn = rag_query_fn
        self.llm_callable = llm_callable

    def classify_query(self, query: str) -> str:
        """Classify as 'sql' or 'rag'."""
        query_lower = query.lower()
        sql_score = sum(1 for k in SQL_KEYWORDS if k in query_lower)
        rag_score = sum(1 for k in RAG_KEYWORDS if k in query_lower)

        if abs(sql_score - rag_score) <= 1:
            prompt = CLASSIFY_QUERY_PROMPT.format(query=query)
            try:
                response = self.llm_callable(prompt).strip().lower()
                return "sql" if "sql" in response else "rag"
            except Exception:
                return "sql" if sql_score >= rag_score else "rag"
        return "sql" if sql_score > rag_score else "rag"

    def route_query(
        self,
        question: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Route to SQL or RAG and return unified result.
        Returns dict: answer, source_documents, agent_used ("sql" | "rag").
        """
        query_type = self.classify_query(question)

        if query_type == "sql":
            result = run_sql_agent(self.document.sqlite_path, question)
            answer = result.get("output", "Sorry, could not get an answer.")
            return {
                "answer": answer,
                "source_documents": [],
                "agent_used": "sql",
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }

        # RAG branch
        try:
            result = self.rag_query_fn(
                self.document.vector_store_path,
                question,
                system_prompt=system_prompt,
                conversation_history=conversation_history,
            )
        except Exception as e:
            return {
                "answer": f"Sorry, an error occurred: {str(e)}",
                "source_documents": [],
                "agent_used": "rag",
            }

        answer = result.get("answer", "")
        if not answer or "sorry" in answer.lower() or "can not find" in answer.lower():
            answer = "Sorry, I could not find the answer in the documents."

        source_documents = result.get("source_documents", [])
        return {
            "answer": answer,
            "source_documents": source_documents,
            "agent_used": "rag",
            "prompt_tokens": result.get("prompt_tokens", 0),
            "completion_tokens": result.get("completion_tokens", 0),
        }
