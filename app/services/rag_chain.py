"""RAG chain implementation using direct Gemini API and FAISS."""
from typing import List
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
    
    def query(self, vector_store_path: str, question: str) -> dict:
        """Query the RAG chain with a question."""
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
            
            # Create prompt with context
            prompt = f"""You are a helpful AI assistant that answers questions based on the provided context from documents.

Context from documents:
{context}

Question: {question}

Please provide a comprehensive answer based on the context provided. If the context doesn't contain enough information to answer the question, say so clearly. Use the context to provide accurate and relevant information.

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
