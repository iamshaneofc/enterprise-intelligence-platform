import os
from typing import List, Optional, Dict
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import TypedDict


class ModelPricing(TypedDict):
    prompt: float
    completion: float


class EmbeddingPricing(TypedDict):
    prompt: float


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core project settings
    PROJECT_NAME: str = "Enterprise Intelligence Platform"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)

    # Security & Authentication
    SECRET_KEY: str = Field(default="eip-super-secret-development-key-change-in-production-1234567890")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./engineering_intelligence.db"
    )

    # Storage Configuration
    STORAGE_DIR: str = Field(default="storage/documents")
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".txt", ".md", ".csv", ".json"]

    # LLM Providers Configuration
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    
    PRIMARY_LLM_PROVIDER: str = "anthropic"
    PRIMARY_LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    FALLBACK_LLM_PROVIDER: str = "openai"
    FALLBACK_LLM_MODEL: str = "gpt-4o"
    
    # Per-model LLM pricing (USD per 1K tokens)
    LLM_PRICING: Dict[str, Dict[str, ModelPricing]] = Field(default_factory=lambda: {
        "anthropic": {
            "claude-3-5-sonnet-20241022": {"prompt": 0.003, "completion": 0.015},
            "claude-3-5-haiku-20241022": {"prompt": 0.0008, "completion": 0.004},
            "claude-3-opus-20240229": {"prompt": 0.015, "completion": 0.075},
        },
        "openai": {
            "gpt-4o": {"prompt": 0.0025, "completion": 0.01},
            "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        },
    })
    
    # Embedding Configuration
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    
    # Embedding pricing
    EMBEDDING_PRICING: Dict[str, Dict[str, EmbeddingPricing]] = Field(default_factory=lambda: {
        "openai": {
            "text-embedding-3-small": {"prompt": 0.00002},
            "text-embedding-3-large": {"prompt": 0.00013},
            "text-embedding-ada-002": {"prompt": 0.0001},
        },
    })

    # Test & Offline Fallback Modes
    USE_FAKE_LLM: bool = Field(default=False)
    USE_FAKE_EMBEDDINGS: bool = Field(default=False)

    # Retrieval & RAG Parameters
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 5
    RRF_K: int = 60
    SIMILARITY_THRESHOLD: float = 0.25

    # Agent Limits
    AGENT_MAX_STEPS: int = 5
    AGENT_TIMEOUT_SECONDS: int = 30

    # Rate Limiting
    RATE_LIMIT_AUTH: int = 10  # requests
    RATE_LIMIT_AUTH_WINDOW: int = 60  # seconds
    RATE_LIMIT_UPLOAD: int = 5  # requests
    RATE_LIMIT_UPLOAD_WINDOW: int = 300  # seconds (5 min)
    RATE_LIMIT_GENERAL: int = 100  # requests
    RATE_LIMIT_GENERAL_WINDOW: int = 60  # seconds

    # CORS
    CORS_ORIGINS: List[str] = ["*"]


settings = Settings()

