"""
Application configuration using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Project
    PROJECT_NAME: str = "Interview RAG System"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database (supports both PostgreSQL and SQLite)
    DATABASE_URL: str = "sqlite:///./interview_rag.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    
    # LLM Configuration
    LLM_TYPE: str = "lmstudio"  # Options: lmstudio, ollama, openai, anthropic
    LMSTUDIO_BASE_URL: str = "http://127.0.0.1:12344"
    LMSTUDIO_MODEL: str = "qwen2.5-coder-14b-instruct"
    LMSTUDIO_API_KEY: str = "not-needed"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"
    
    # Embedding Configuration
    EMBEDDING_TYPE: str = "local"  # Options: local, openai
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Vector Store
    VECTOR_STORE_TYPE: str = "faiss"  # Options: faiss, chroma
    VECTOR_STORE_PATH: str = "./data/vector_stores"
    
    # Retrieval Configuration
    TOP_K_RETRIEVAL: int = 10
    RERANK_TOP_K: int = 0
    SIMILARITY_THRESHOLD: float = 0.0
    USE_HYBRID_RETRIEVAL: bool = True
    HYBRID_ALPHA: float = 0.5  # Weight for dense vs sparse
    
    # Chunking Configuration
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    CHUNKING_STRATEGY: str = "semantic"  # Options: fixed, semantic, recursive
    
    # RAG Configuration
    STRICT_RAG_MODE: bool = True
    REQUIRE_SOURCE_ATTRIBUTION: bool = True
    MIN_CONFIDENCE_THRESHOLD: float = 0.1
    MAX_CONTEXT_LENGTH: int = 2048
    
    # File Upload
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Score Validation
    ENABLE_SCORE_VALIDATION: bool = True
    LOG_SCORE_NORMALIZATION: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
