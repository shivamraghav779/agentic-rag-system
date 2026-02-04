"""Configuration settings for the chatbot application."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database (sync for Alembic; use async_database_url for app)
    database_url: str = "mysql+pymysql://user:password@localhost:3306/chatbot_db"

    @property
    def async_database_url(self) -> str:
        """URL for async driver (asyncmy)."""
        if "pymysql" in self.database_url:
            return self.database_url.replace("mysql+pymysql://", "mysql+asyncmy://", 1)
        return self.database_url.replace("mysql://", "mysql+asyncmy://", 1)
    
    # Gemini API
    google_api_key: str = ""  # Single key (deprecated, use google_api_keys)
    google_api_keys: str = ""  # Comma-separated list of API keys for fallback
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "text-embedding-004"
    
    # Groq API
    groq_api_keys: str = ""  # Comma-separated list of Groq API keys for fallback
    groq_model: str = "llama-3.3-70b-versatile"  # Default Groq model
    
    # LLM Configuration
    temperature: float = 0.7
    max_output_tokens: int = 2048
    
    # Retrieval Configuration
    retrieval_k: int = 4  # Number of documents to retrieve (used when reranking disabled)
    retrieval_k_initial: int = 10  # Initial retrieve count before reranking (when reranking enabled)
    retrieval_k_final: int = 5  # Number of documents after reranking
    source_doc_preview_length: int = 500  # Characters to show in source preview

    # Pre-retrieval processing (query rewriting & expansion)
    enable_query_rewriting: bool = True
    enable_query_expansion: bool = True

    # Post-retrieval processing (reranking & prompt compression)
    enable_reranking: bool = True
    enable_prompt_compression: bool = True
    reranking_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    compression_ratio: float = 0.7  # Compress context to this fraction (0.0-1.0)
    
    # Prompt Configuration
    default_instruction_prompt: str = """Please provide a comprehensive answer based on the context provided. If the context doesn't contain enough information to answer the question, say so clearly. Use the context to provide accurate and relevant information."""
    
    # JWT Authentication
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7  # Refresh tokens expire in 7 days
    
    # File paths (legacy flat layout; new uploads use per-org artifacts when available)
    upload_dir: str = "./uploads"
    vector_store_dir: str = "./vector_stores"
    sqlite_store_dir: str = "./sqlite_stores"

    # Per-organization artifact root: artifacts/{organization_id}/vector_store|structured_data|uploads
    artifacts_base_dir: str = "./artifacts"
    
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
Path(settings.sqlite_store_dir).mkdir(parents=True, exist_ok=True)

# Initialize Multi-Provider LLM Manager (lazy initialization to avoid circular imports)
llm_provider_manager = None

def get_llm_provider_manager():
    """Get or create the multi-provider LLM manager instance."""
    global llm_provider_manager
    if llm_provider_manager is None:
        from app.core.llm_provider_manager import MultiProviderLLMManager, LLMProvider
        
        # Get Gemini API keys
        gemini_keys = []
        if settings.google_api_keys:
            gemini_keys = [key.strip() for key in settings.google_api_keys.split(',') if key.strip()]
        elif settings.google_api_key:
            gemini_keys = [settings.google_api_key]
        
        # Get Groq API keys
        groq_keys = []
        if settings.groq_api_keys:
            groq_keys = [key.strip() for key in settings.groq_api_keys.split(',') if key.strip()]
        
        # Create multi-provider manager
        if gemini_keys or groq_keys:
            llm_provider_manager = MultiProviderLLMManager(
                gemini_keys=gemini_keys if gemini_keys else None,
                groq_keys=groq_keys if groq_keys else None,
                preferred_provider=LLMProvider.GEMINI if gemini_keys else LLMProvider.GROQ
            )
        else:
            import warnings
            warnings.warn("No LLM API keys configured. Set GOOGLE_API_KEYS and/or GROQ_API_KEYS in .env")
            raise ValueError("No LLM API keys configured. Set GOOGLE_API_KEYS and/or GROQ_API_KEYS in .env")
    
    return llm_provider_manager

# Backward compatibility: Create API key manager for embeddings (Gemini only)
api_key_manager = None

def get_api_key_manager():
    """Get or create the API key manager instance (for embeddings - Gemini only)."""
    global api_key_manager
    if api_key_manager is None:
        from app.core.api_key_manager import APIKeyManager
        
        # Get API keys - prefer google_api_keys (comma-separated) over google_api_key (single)
        api_keys_list = []
        if settings.google_api_keys:
            api_keys_list = [key.strip() for key in settings.google_api_keys.split(',') if key.strip()]
        elif settings.google_api_key:
            api_keys_list = [settings.google_api_key]
        
        # Create API key manager instance
        if api_keys_list:
            api_key_manager = APIKeyManager(api_keys_list)
        else:
            import warnings
            warnings.warn("No Gemini API keys configured for embeddings. Set GOOGLE_API_KEY or GOOGLE_API_KEYS in .env")
            raise ValueError("No Gemini API keys configured for embeddings. Set GOOGLE_API_KEY or GOOGLE_API_KEYS in .env")
    
    return api_key_manager

