"""Configuration settings for the chatbot application."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "mysql+pymysql://user:password@localhost:3306/chatbot_db"
    
    # Gemini API
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "text-embedding-004"
    
    # LLM Configuration
    temperature: float = 0.7
    max_output_tokens: int = 2048
    
    # Retrieval Configuration
    retrieval_k: int = 4  # Number of documents to retrieve
    source_doc_preview_length: int = 500  # Characters to show in source preview
    
    # JWT Authentication
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # File paths
    upload_dir: str = "./uploads"
    vector_store_dir: str = "./vector_stores"
    
    # Chunking configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create singleton instance
settings = Settings()

# Ensure directories exist
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.vector_store_dir).mkdir(parents=True, exist_ok=True)

