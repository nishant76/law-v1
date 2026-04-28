"""
Application configuration — loads from environment variables
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings from environment"""
    
    # App
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Nikhar"
    
    # Database — accept Neon/Railway postgres:// and postgresql:// connection strings
    _db_url_raw: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://nikhar:nikhar@localhost:5432/nikhar"
    )
    if _db_url_raw.startswith("postgres://"):
        DATABASE_URL: str = _db_url_raw.replace("postgres://", "postgresql+asyncpg://", 1)
    elif _db_url_raw.startswith("postgresql://") and "+asyncpg" not in _db_url_raw:
        DATABASE_URL: str = _db_url_raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        DATABASE_URL: str = _db_url_raw
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # LLM Provider Selection
    # Set to False to use direct OpenAI API (useful for local testing without Azure)
    # Set to True to use Azure OpenAI (production)
    USE_AZURE_OPENAI: bool = os.getenv("USE_AZURE_OPENAI", "true").lower() == "true"

    # Direct OpenAI API (when USE_AZURE_OPENAI=False)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_ORG_ID: Optional[str] = os.getenv("OPENAI_ORG_ID", None)
    
    # Azure OpenAI (when USE_AZURE_OPENAI=True)
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    GPT4O_DEPLOYMENT: str = os.getenv("GPT4O_DEPLOYMENT", "gpt-4o")
    GPT4O_MINI_DEPLOYMENT: str = os.getenv("GPT4O_MINI_DEPLOYMENT", "gpt-4o-mini")
    GPT52_DEPLOYMENT: str = os.getenv("GPT52_DEPLOYMENT", "gpt-5.2")
    EMBEDDING_DEPLOYMENT: str = os.getenv("EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
    
    # Azure Search
    AZURE_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    AZURE_SEARCH_KEY: str = os.getenv("AZURE_SEARCH_KEY", "")
    
    # Azure Blob Storage
    BLOB_CONNECTION_STRING: str = os.getenv("BLOB_CONNECTION_STRING", "")
    
    # SendGrid
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    
    # WhatsApp Business API
    WHATSAPP_API_TOKEN: str = os.getenv("WHATSAPP_API_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "dev-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "RS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    
    # Application Insights
    APPLICATIONINSIGHTS_CONNECTION_STRING: Optional[str] = os.getenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        None
    )


settings = Settings()
