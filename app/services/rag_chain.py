"""RAG chain implementation using direct Gemini API and FAISS."""
from typing import List, Optional, Dict
from datetime import datetime
import google.generativeai as genai
from app.services.vector_store import VectorStoreManager
from app.core.config import settings


class RAGChain:
    """RAG chain for document-based question answering without Langchain."""
    
    def __init__(self):
        """Initialize RAG chain with Gemini model."""
        # Configure Gemini API
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.vector_store_manager = VectorStoreManager()
    
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
            # Retrieve relevant documents
            relevant_docs = self.vector_store_manager.similarity_search(
                vector_store_path, question, k=settings.retrieval_k
            )
            
            if not relevant_docs:
                return {
                    "answer": "No relevant information found in the documents.",
                    "source_documents": []
                }
            
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
            
            # Generate response using Gemini
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.temperature,
                    max_output_tokens=settings.max_output_tokens,
                )
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
            
            return {
                "answer": answer,
                "source_documents": source_documents
            }
        except Exception as e:
            raise Exception(f"Error querying RAG chain: {str(e)}")
    
    def get_relevant_chunks(self, vector_store_path: str, query: str, k: int = None) -> List:
        """Get relevant document chunks for a query."""
        if k is None:
            k = settings.retrieval_k
        return self.vector_store_manager.similarity_search(vector_store_path, query, k=k)
