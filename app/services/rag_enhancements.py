"""
Pre-retrieval and post-retrieval RAG enhancements aligned with the notebook pipeline:
- QueryProcessor: query rewriting and query expansion
- Reranker: cross-encoder reranking of retrieved documents
- PromptCompressor: compress context to reduce token usage
"""
from typing import List, Callable, Optional
from langchain_core.documents import Document
from app.core.config import settings
from app.prompts.templates import (
    REWRITE_QUERY_PROMPT,
    EXPAND_QUERY_PROMPT,
    COMPRESS_CONTEXT_PROMPT,
)


# Optional reranking: sentence-transformers may not be installed
RERANKING_AVAILABLE = False
try:
    from sentence_transformers import CrossEncoder
    RERANKING_AVAILABLE = True
except ImportError:
    CrossEncoder = None


class QueryProcessor:
    """
    Pre-retrieval processing: Query Rewriting and Query Expansion.
    Uses LLM to make queries more effective for retrieval.
    """

    def __init__(
        self,
        llm_callable: Callable[[str], str],
        enable_rewriting: Optional[bool] = None,
        enable_expansion: Optional[bool] = None,
    ):
        self.llm_callable = llm_callable
        self.enable_rewriting = enable_rewriting if enable_rewriting is not None else settings.enable_query_rewriting
        self.enable_expansion = enable_expansion if enable_expansion is not None else settings.enable_query_expansion

        self.financial_synonyms = {
            "profit": ["profit", "gain", "earnings", "income", "revenue"],
            "loss": ["loss", "deficit", "negative return"],
            "portfolio": ["portfolio", "fund", "account", "holdings"],
            "trade": ["trade", "transaction", "execution", "order"],
            "security": ["security", "asset", "instrument", "stock", "bond"],
            "quantity": ["quantity", "qty", "amount", "volume", "shares"],
            "price": ["price", "cost", "value", "valuation"],
            "performance": ["performance", "return", "yield", "result"],
        }

    def rewrite_query(self, query: str) -> str:
        """Rewrite query to be more effective for retrieval."""
        if not self.enable_rewriting:
            return query

        rewrite_prompt = REWRITE_QUERY_PROMPT.format(query=query)

        try:
            rewritten = self.llm_callable(rewrite_prompt)
            if rewritten:
                rewritten = rewritten.strip().strip('"').strip("'")
                return rewritten
        except Exception:
            pass
        return query

    def expand_query(self, query: str) -> str:
        """Expand query with synonyms and related terms for better retrieval coverage."""
        if not self.enable_expansion:
            return query

        expansion_prompt = EXPAND_QUERY_PROMPT.format(query=query)

        try:
            expanded = self.llm_callable(expansion_prompt)
            if expanded:
                expanded = expanded.strip().strip('"').strip("'")
                return expanded
        except Exception:
            pass

        # Fallback: keyword-based expansion
        words = query.lower().split()
        expanded_terms = []
        for word in words:
            expanded_terms.append(word)
            for key, synonyms in self.financial_synonyms.items():
                if key in word:
                    expanded_terms.extend(synonyms[:2])
                    break
        return " ".join(expanded_terms) if expanded_terms else query

    def process_query(self, query: str) -> str:
        """Apply all pre-retrieval processing steps."""
        processed = query
        if self.enable_rewriting:
            processed = self.rewrite_query(processed)
        if self.enable_expansion:
            processed = self.expand_query(processed)
        return processed


class Reranker:
    """
    Re-rank retrieved documents using a cross-encoder for better relevance.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        enable: Optional[bool] = None,
    ):
        self.enable = (enable if enable is not None else settings.enable_reranking) and RERANKING_AVAILABLE
        self.model = None

        if self.enable and CrossEncoder is not None:
            try:
                self.model = CrossEncoder(model_name or settings.reranking_model)
            except Exception:
                self.enable = False

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: Optional[int] = None,
    ) -> List[Document]:
        """Re-rank documents based on query-document relevance."""
        if not self.enable or not documents:
            k = top_k or settings.retrieval_k_final
            return documents[:k]

        if top_k is None:
            top_k = settings.retrieval_k_final

        pairs = [[query, doc.page_content] for doc in documents]
        scores = self.model.predict(pairs)
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in scored_docs[:top_k]]


class PromptCompressor:
    """
    Compress context to reduce token usage while preserving information relevant to the query.
    """

    def __init__(
        self,
        llm_callable: Callable[[str], str],
        compression_ratio: Optional[float] = None,
        enable: Optional[bool] = None,
    ):
        self.llm_callable = llm_callable
        self.compression_ratio = compression_ratio if compression_ratio is not None else settings.compression_ratio
        self.enable = enable if enable is not None else settings.enable_prompt_compression

    def compress_context(self, context: str, query: str) -> str:
        """Compress context by extracting only relevant information for the query."""
        if not self.enable or not context:
            return context

        target_length = int(len(context) * self.compression_ratio)
        if len(context) <= target_length:
            return context

        compression_prompt = COMPRESS_CONTEXT_PROMPT.format(
            target_length=target_length,
            query=query,
            context=context,
        )

        try:
            compressed = self.llm_callable(compression_prompt)
            if compressed:
                return compressed.strip()
        except Exception:
            pass

        return context[:target_length] + "..."

    def compress_documents(
        self,
        documents: List[Document],
        query: str,
    ) -> List[Document]:
        """Compress multiple documents' content."""
        if not self.enable:
            return documents

        result = []
        for doc in documents:
            content = doc.page_content
            compressed_content = self.compress_context(content, query)
            result.append(
                Document(page_content=compressed_content, metadata=dict(doc.metadata))
            )
        return result
