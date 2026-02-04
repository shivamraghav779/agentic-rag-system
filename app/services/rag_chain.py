"""RAG chain implementation using Gemini/Groq API and FAISS."""
from typing import List, Optional, Dict
from datetime import datetime
import google.generativeai as genai
from app.services.vector_store import VectorStoreManager
from app.services.groq_client import GroqClient
from app.services.rag_enhancements import QueryProcessor, Reranker, PromptCompressor
from app.core.config import settings, get_api_key_manager, get_llm_provider_manager
from app.core.llm_provider_manager import LLMProvider


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
    
    def format_context(self, documents: List) -> str:
        """Format retrieved documents into context string."""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            context_parts.append(f"[Document {i}]\n{content}\n")
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

    def _llm_generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """Generate text from prompt using Gemini/Groq fallback. Used for query rewrite, expansion, and compression."""
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

        response = self.llm_provider_manager.execute_with_fallback(_gemini, _groq)
        return response.text or ""

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
            relevant_docs = self.vector_store_manager.similarity_search(
                vector_store_path, processed_query, k=k_retrieve
            )

            if not relevant_docs:
                return {
                    "answer": "No relevant information found in the documents.",
                    "source_documents": [],
                }

            # Post-retrieval: reranking (notebook-aligned)
            if settings.enable_reranking:
                relevant_docs = self.reranker.rerank(
                    question, relevant_docs, top_k=settings.retrieval_k_final
                )

            # Post-retrieval: optional prompt compression (notebook-aligned)
            if settings.enable_prompt_compression:
                prompt_compressor = PromptCompressor(llm_callable=self._llm_generate)
                relevant_docs = prompt_compressor.compress_documents(
                    relevant_docs, question
                )

            # Format context from retrieved documents
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
            if history_context:
                prompt = f"""{system_part}

{date_context}

{history_context}

Context from documents:
{context}

Current Question: {question}

{instruction_prompt}

Answer:"""
            else:
                prompt = f"""{system_part}

{date_context}

Context from documents:
{context}

Question: {question}

{instruction_prompt}

Answer:"""
            
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
            
            response = self.llm_provider_manager.execute_with_fallback(
                _generate_gemini_response,
                _generate_groq_response
            )
            
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
            prompt = f"""Generate a concise, descriptive title for a conversation that starts with this question: "{question}"

Requirements:
- The title should be a short, clear summary of what the conversation is about
- Maximum 100 characters
- Do not include quotation marks or special formatting
- Return only the title, nothing else

Title:"""
            
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
            
            response = self.llm_provider_manager.execute_with_fallback(
                _generate_title_gemini,
                _generate_title_groq
            )
            
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
