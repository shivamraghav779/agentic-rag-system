"""FAISS vector store management."""
from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings


class VectorStoreManager:
    """Manages FAISS vector stores for documents."""
    
    def __init__(self):
        """Initialize with Gemini embeddings."""
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=settings.google_api_key
        )
        self.base_dir = Path(settings.vector_store_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_vector_store(self, documents: List[Document], store_name: str) -> str:
        """Create a new FAISS vector store from documents."""
        try:
            # Create FAISS vector store
            vector_store = FAISS.from_documents(documents, self.embeddings)
            
            # Save to disk
            store_path = self.base_dir / store_name
            vector_store.save_local(str(store_path))
            
            return str(store_path)
        except Exception as e:
            raise Exception(f"Error creating vector store: {str(e)}")
    
    def load_vector_store(self, store_path: str) -> FAISS:
        """Load an existing FAISS vector store."""
        try:
            vector_store = FAISS.load_local(
                store_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            return vector_store
        except Exception as e:
            raise Exception(f"Error loading vector store: {str(e)}")
    
    def add_documents_to_store(self, store_path: str, documents: List[Document]) -> None:
        """Add new documents to an existing vector store."""
        try:
            vector_store = self.load_vector_store(store_path)
            vector_store.add_documents(documents)
            vector_store.save_local(store_path)
        except Exception as e:
            raise Exception(f"Error adding documents to vector store: {str(e)}")
    
    def similarity_search(self, store_path: str, query: str, k: int = 4) -> List[Document]:
        """Perform similarity search in the vector store."""
        try:
            vector_store = self.load_vector_store(store_path)
            results = vector_store.similarity_search(query, k=k)
            return results
        except Exception as e:
            raise Exception(f"Error performing similarity search: {str(e)}")
    
    def similarity_search_with_score(self, store_path: str, query: str, k: int = 4) -> List[tuple]:
        """Perform similarity search with scores."""
        try:
            vector_store = self.load_vector_store(store_path)
            results = vector_store.similarity_search_with_score(query, k=k)
            return results
        except Exception as e:
            raise Exception(f"Error performing similarity search with score: {str(e)}")
    
    def delete_vector_store(self, store_path: str) -> None:
        """Delete a vector store and its associated files."""
        try:
            # FAISS creates multiple files (.faiss and .pkl)
            base_path = Path(store_path)
            faiss_file = base_path / "index.faiss"
            pkl_file = base_path / "index.pkl"
            
            if faiss_file.exists():
                faiss_file.unlink()
            if pkl_file.exists():
                pkl_file.unlink()
            
            # Try to remove directory if empty
            try:
                base_path.rmdir()
            except OSError:
                pass  # Directory not empty or doesn't exist
        except Exception as e:
            raise Exception(f"Error deleting vector store: {str(e)}")

