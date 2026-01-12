"""FAISS vector store management."""
from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings, get_api_key_manager


class VectorStoreManager:
    """Manages FAISS vector stores for documents."""
    
    def __init__(self):
        """Initialize with Gemini embeddings."""
        self.api_key_manager = get_api_key_manager()
        
        # Initialize embeddings with first key
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=self.api_key_manager.get_current_key()
        )
        self.base_dir = Path(settings.vector_store_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_vector_store(self, documents: List[Document], store_name: str) -> str:
        """Create a new FAISS vector store from documents."""
        def _create_store():
            # Reinitialize embeddings with current key (in case it changed)
            embeddings = GoogleGenerativeAIEmbeddings(
                model=settings.embedding_model,
                google_api_key=self.api_key_manager.get_current_key()
            )
            # Create FAISS vector store
            vector_store = FAISS.from_documents(documents, embeddings)
            
            # Save to disk
            store_path = self.base_dir / store_name
            vector_store.save_local(str(store_path))
            
            return str(store_path)
        
        try:
            return self.api_key_manager.execute_with_fallback(_create_store)
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
        def _search():
            # Reinitialize embeddings with current key (in case it changed)
            embeddings = GoogleGenerativeAIEmbeddings(
                model=settings.embedding_model,
                google_api_key=self.api_key_manager.get_current_key()
            )
            vector_store = FAISS.load_local(
                store_path,
                embeddings,
                allow_dangerous_deserialization=True
            )
            return vector_store.similarity_search(query, k=k)
        
        try:
            return self.api_key_manager.execute_with_fallback(_search)
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
        """Delete a vector store and its associated files.
        
        FAISS vector stores consist of:
        - index.faiss: The FAISS index file
        - index.pkl: The pickled metadata file
        
        This method deletes both files and removes the directory if empty.
        """
        try:
            base_path = Path(store_path)
            
            if not base_path.exists():
                # Path doesn't exist, nothing to delete
                return
            
            # FAISS creates multiple files (.faiss and .pkl)
            faiss_file = base_path / "index.faiss"
            pkl_file = base_path / "index.pkl"
            
            # Delete FAISS index file
            if faiss_file.exists():
                faiss_file.unlink()
            
            # Delete pickled metadata file
            if pkl_file.exists():
                pkl_file.unlink()
            
            # Try to remove directory if empty
            try:
                if base_path.is_dir():
                    base_path.rmdir()
            except OSError:
                # Directory not empty or doesn't exist - that's okay
                pass
            
            # If it's a file instead of directory, delete it directly
            if base_path.is_file():
                base_path.unlink()
                
        except Exception as e:
            raise Exception(f"Error deleting vector store at {store_path}: {str(e)}")

