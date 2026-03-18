"""RAG chain implementation using Gemini/Groq API and FAISS."""
import json
from typing import List, Optional, Dict
from datetime import datetime
import google.generativeai as genai
from app.services.vector_store import VectorStoreManager
from app.services.groq_client import GroqClient
from app.services.rag_enhancements import QueryProcessor, Reranker, PromptCompressor
from app.core.config import settings, get_api_key_manager, get_llm_provider_manager
from app.core.llm_provider_manager import LLMProvider
from app.prompts.templates import (
    ANSWER_PROMPT_NO_HISTORY,
    ANSWER_PROMPT_WITH_HISTORY,
    CONVERSATION_TITLE_PROMPT,
    GROUNDING_VERIFY_PROMPT,
)
import time
from app.core.cache import TTLLRUCache


class RAGChain:
    """RAG chain for document-based question answering with multi-provider support.
    Pipeline aligned with notebook: pre-retrieval (query rewrite/expansion),
    retrieval, post-retrieval (reranking, optional prompt compression), then generation.
    """

    def __init__(self):
        """Initialize RAG chain with multi-provider support."""
        # API key manager for embeddings (Gemini only)
        self.api_key_manager = get_api_key_manager()

        # Multi-provider manager for chat completions (Gemini + Groq)
        self.llm_provider_manager = get_llm_provider_manager()

        # Configure Gemini with first key initially (for embeddings)
        genai.configure(api_key=self.api_key_manager.get_current_key())
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.vector_store_manager = VectorStoreManager()

        # Post-retrieval reranker (loads cross-encoder once if enabled)
        self.reranker = Reranker()

        # Cache LLM prompt outputs for query rewriting/expansion/compression.
        self._llm_prompt_cache = (
            TTLLRUCache(
                max_entries=settings.llm_prompt_cache_max_entries,
                ttl_seconds=settings.llm_prompt_cache_ttl_seconds,
            )
            if settings.enable_llm_prompt_cache
            else None
        )
    
    def format_context(
        self,
        documents: List,
        *,
        max_total_chars: int = None,
        max_doc_chars: int = None,
    ) -> str:
        """Format retrieved documents into context string with a length budget."""
        max_total_chars = (
            settings.context_max_chars if max_total_chars is None else max_total_chars
        )
        max_doc_chars = (
            settings.context_max_doc_chars if max_doc_chars is None else max_doc_chars
        )

        context_parts: List[str] = []
        used = 0

        for i, doc in enumerate(documents, 1):
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)
            content = content or ""

            if max_doc_chars and len(content) > max_doc_chars:
                content = content[:max_doc_chars]

            # Stop adding context once we hit the budget.
            if max_total_chars:
                remaining = max_total_chars - used
                if remaining <= 0:
                    break
                if len(content) > remaining:
                    content = content[:remaining]

            context_parts.append(f"[Document {i}]\n{content}\n")
            used += len(content)

        return "\n".join(context_parts)
    
    def format_conversation_history(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history into a readable context string."""
        if not history:
            return ""

        history_parts = ["Previous conversation:"]
        for i, chat in enumerate(history, 1):
            history_parts.append(f"Q{i}: {chat.get('question', '')}")
            history_parts.append(f"A{i}: {chat.get('answer', '')}")

        return "\n".join(history_parts)

    def _verify_grounding(self, question: str, answer: str, context: str) -> str:
        """
        Verify the proposed answer is supported by retrieved context.

        If not supported, returns a corrected/refusal answer.
        """
        # Fast exit for empty/noisy answers.
        if not answer or not answer.strip():
            return "I couldn't generate a response. Please try again."

        if "no relevant information found" in answer.lower():
            return answer

        prompt = GROUNDING_VERIFY_PROMPT.format(
            question=question,
            answer=answer,
            context=context,
        )

        verifier_output = self._llm_generate(
            prompt,
            max_tokens=settings.grounding_max_output_tokens,
        )

        # Enforce JSON-only response.
        try:
            parsed = json.loads(verifier_output)
            corrected = parsed.get("corrected_answer")
            if isinstance(corrected, str) and corrected.strip():
                return corrected.strip()
        except Exception:
            # If parsing fails, fall back to refusing (safer than trusting hallucinations).
            pass

        return "I couldn't find enough evidence in the provided documents to answer that."

    def _llm_generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """Generate text from prompt using Gemini/Groq fallback. Used for query rewrite, expansion, and compression."""
        last_error: Optional[Exception] = None
        max_attempts = max(1, settings.llm_max_retries + 1)

        cache_key = None
        # Multi-tenancy note:
        # Some LLM prompts (e.g., context compression) embed retrieved document text.
        # Caching those prompts can theoretically lead to cross-tenant reuse if the
        # same prompt text appears again. We only cache "short" prompts.
        cache_allowed = (
            self._llm_prompt_cache is not None
            and len(prompt) <= settings.llm_prompt_cache_max_prompt_chars
        )

        if cache_allowed:
            cache_key = json.dumps(
                {
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": settings.temperature,
                    "gemini_model": settings.gemini_model,
                    "groq_model": settings.groq_model,
                },
                sort_keys=True,
                ensure_ascii=True,
            )
            cached = self._llm_prompt_cache.get(cache_key)
            if cached is not None:
                return cached

        def _gemini():
            pm = self.llm_provider_manager.get_current_key_manager()
            genai.configure(api_key=pm.get_current_key())
            model = genai.GenerativeModel(settings.gemini_model)
            r = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=max_tokens,
                ),
            )
            return r

        def _groq():
            pm = self.llm_provider_manager.get_current_key_manager()
            groq_client = GroqClient(api_key=pm.get_current_key(), model=settings.groq_model)
            return groq_client.generate_content(
                prompt=prompt,
                temperature=0.3,
                max_tokens=max_tokens,
            )

        response = None
        for attempt in range(max_attempts):
            try:
                response = self.llm_provider_manager.execute_with_fallback(_gemini, _groq)
                break
            except Exception as e:
                last_error = e
                if attempt >= max_attempts - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))

        final_text = response.text or ""
        if cache_allowed and cache_key is not None and final_text:
            self._llm_prompt_cache.set(cache_key, final_text)
        return final_text

    def query(
        self, 
        vector_store_path: str, 
        question: str, 
        system_prompt: str = None, 
        instruction_prompt: str = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> dict:
        """Query the RAG chain with a question.
        
        Args:
            vector_store_path: Path to the vector store
            question: User's question
            system_prompt: User's custom system prompt (optional)
            instruction_prompt: Common instruction prompt (optional, uses default if not provided)
            conversation_history: List of previous Q&A pairs for context (optional)
        """
        try:
            # Pre-retrieval: query rewriting and expansion (notebook-aligned)
            query_processor = QueryProcessor(llm_callable=self._llm_generate)
            processed_query = query_processor.process_query(question)

            # Retrieval: fetch more when reranking is enabled, then trim
            k_retrieve = (
                settings.retrieval_k_initial
                if settings.enable_reranking
                else settings.retrieval_k
            )

            # Post-retrieval: reranking (notebook-aligned)
            # Always perform an explicit reranking step:
            # - If cross-encoder reranker is available, use it.
            # - Otherwise, fall back to score-based reranking using FAISS distances/similarity.
            if self.reranker.enable:
                relevant_docs = self.vector_store_manager.similarity_search(
                    vector_store_path, processed_query, k=k_retrieve
                )

                if not relevant_docs:
                    return {
                        "answer": "No relevant information found in the documents.",
                        "source_documents": [],
                    }

                if settings.enable_reranking:
                    relevant_docs = self.reranker.rerank(
                        question, relevant_docs, top_k=settings.retrieval_k_final
                    )
            else:
                # Score-based reranking to avoid the "no reranking" trap.
                scored = self.vector_store_manager.similarity_search_with_score(
                    vector_store_path, processed_query, k=k_retrieve
                )
                if not scored:
                    return {
                        "answer": "No relevant information found in the documents.",
                        "source_documents": [],
                    }

                scores = [s for _, s in scored]
                # Heuristic: if scores go negative, treat higher as better (cosine similarity).
                # Otherwise treat lower as better (common for FAISS distances).
                lower_is_better = min(scores) >= 0
                scored_sorted = sorted(
                    scored,
                    key=lambda x: x[1],
                    reverse=(not lower_is_better),
                )

                k_final = settings.retrieval_k_final if settings.enable_reranking else k_retrieve
                relevant_docs = [doc for doc, _ in scored_sorted[:k_final]]

            # Post-retrieval: optional prompt compression (notebook-aligned)
            if settings.enable_prompt_compression:
                prompt_compressor = PromptCompressor(llm_callable=self._llm_generate)
                relevant_docs = prompt_compressor.compress_documents(
                    relevant_docs, question
                )

            # Format context from retrieved documents (with prompt size budget)
            context = self.format_context(relevant_docs)
            
            # Use user's system prompt or default
            if system_prompt:
                system_part = system_prompt
            else:
                system_part = "You are a helpful AI assistant that answers questions based on the provided context from documents."
            
            # Use provided instruction prompt or default from config
            if instruction_prompt is None:
                instruction_prompt = settings.default_instruction_prompt
            
            # Format conversation history if provided
            history_context = ""
            if conversation_history:
                history_context = self.format_conversation_history(conversation_history)
            
            # Get current date and time
            current_datetime = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            date_context = f"Current date and time: {current_datetime}"

            # Create prompt with context, conversation history, and current date
            prompt = (
                ANSWER_PROMPT_WITH_HISTORY.format(
                    system_part=system_part,
                    date_context=date_context,
                    history_context=history_context,
                    context=context,
                    question=question,
                    instruction_prompt=instruction_prompt,
                )
                if history_context
                else ANSWER_PROMPT_NO_HISTORY.format(
                    system_part=system_part,
                    date_context=date_context,
                    context=context,
                    question=question,
                    instruction_prompt=instruction_prompt,
                )
            )
            
            # Generate response using multi-provider fallback (Gemini -> Groq)
            def _generate_gemini_response():
                """Generate response using Gemini."""
                provider_manager = self.llm_provider_manager.get_current_key_manager()
                genai.configure(api_key=provider_manager.get_current_key())
                model = genai.GenerativeModel(settings.gemini_model)
                return model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=settings.temperature,
                        max_output_tokens=settings.max_output_tokens,
                    )
                )
            
            def _generate_groq_response():
                """Generate response using Groq."""
                provider_manager = self.llm_provider_manager.get_current_key_manager()
                groq_client = GroqClient(
                    api_key=provider_manager.get_current_key(),
                    model=settings.groq_model
                )
                # Extract system prompt if present
                system_prompt_part = None
                user_prompt_part = prompt
                
                # Try to extract system prompt from prompt (if it's structured)
                if "\n\n" in prompt:
                    parts = prompt.split("\n\n", 1)
                    if "System Instructions:" in parts[0] or "Organization Context:" in parts[0]:
                        system_prompt_part = parts[0]
                        user_prompt_part = parts[1] if len(parts) > 1 else prompt
                
                return groq_client.generate_content(
                    prompt=user_prompt_part,
                    system_prompt=system_prompt_part,
                    temperature=settings.temperature,
                    max_tokens=settings.max_output_tokens
                )
            
            # execute_with_fallback handles provider/key fallback; we additionally
            # retry transient failures (network/timeouts).
            response = None
            max_attempts = max(1, settings.llm_max_retries + 1)
            for attempt in range(max_attempts):
                try:
                    response = self.llm_provider_manager.execute_with_fallback(
                        _generate_gemini_response,
                        _generate_groq_response,
                    )
                    break
                except Exception:
                    if attempt >= max_attempts - 1:
                        raise
                    time.sleep(0.5 * (attempt + 1))
            
            answer = response.text if response.text else "I couldn't generate a response. Please try again."
            
            # Format source documents for response
            preview_length = settings.source_doc_preview_length
            source_documents = [
                {
                    "content": (doc.page_content[:preview_length] if hasattr(doc, 'page_content') else str(doc)[:preview_length]),
                    "metadata": (doc.metadata if hasattr(doc, 'metadata') else {})
                }
                for doc in relevant_docs
            ]

            # Extract token usage from response
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

            # Faithfulness / grounding check to reduce hallucinations.
            # This intentionally prefers safety (refusal) if the verifier is unreliable.
            if settings.enable_grounding_check:
                answer = self._verify_grounding(
                    question=question,
                    answer=answer,
                    context=context,
                )
            
            return {
                "answer": answer,
                "source_documents": source_documents,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens
            }
        except Exception as e:
            raise Exception(f"Error querying RAG chain: {str(e)}")
    
    def generate_conversation_title(self, question: str) -> str:
        """Generate a concise title for a conversation based on the first question.
        
        Args:
            question: The first question in the conversation
            
        Returns:
            A concise title (max 100 characters) for the conversation
        """
        try:
            prompt = CONVERSATION_TITLE_PROMPT.format(question=question)
            
            # Generate title using multi-provider fallback
            def _generate_title_gemini():
                """Generate title using Gemini."""
                provider_manager = self.llm_provider_manager.get_current_key_manager()
                genai.configure(api_key=provider_manager.get_current_key())
                model = genai.GenerativeModel(settings.gemini_model)
                return model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,  # Lower temperature for more consistent titles
                        max_output_tokens=50,  # Titles should be short
                    )
                )
            
            def _generate_title_groq():
                """Generate title using Groq."""
                provider_manager = self.llm_provider_manager.get_current_key_manager()
                groq_client = GroqClient(
                    api_key=provider_manager.get_current_key(),
                    model=settings.groq_model
                )
                return groq_client.generate_content(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=50
                )
            
            last_error: Optional[Exception] = None
            max_attempts = max(1, settings.llm_max_retries + 1)
            response = None
            for attempt in range(max_attempts):
                try:
                    response = self.llm_provider_manager.execute_with_fallback(
                        _generate_title_gemini,
                        _generate_title_groq
                    )
                    break
                except Exception as e:
                    last_error = e
                    if attempt >= max_attempts - 1:
                        raise
                    time.sleep(0.5 * (attempt + 1))
            
            title = response.text.strip() if response.text else question[:100]
            
            # Remove any quotation marks that might be added
            title = title.strip('"\'')
            
            # Ensure it doesn't exceed 100 characters
            if len(title) > 100:
                title = title[:97] + "..."
            
            return title if title else question[:100]
        except Exception as e:
            # Fallback to truncated question if title generation fails
            return question[:100] if len(question) > 100 else question
    
    def get_relevant_chunks(self, vector_store_path: str, query: str, k: int = None) -> List:
        """Get relevant document chunks for a query."""
        if k is None:
            k = settings.retrieval_k
        return self.vector_store_manager.similarity_search(vector_store_path, query, k=k)
