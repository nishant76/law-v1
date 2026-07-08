"""
Application configuration — loads from environment variables
"""
import os
from typing import Optional, Tuple
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from dotenv import load_dotenv

load_dotenv()

# libpq/psycopg-only query params that asyncpg does NOT accept as connect kwargs.
# Neon/Railway connection strings include these; asyncpg errors on them
# ("connect() got an unexpected keyword argument 'sslmode'"). We strip them from
# the URL and translate to an SSL context applied via connect_args instead.
_ASYNCPG_INCOMPATIBLE_PARAMS = {"sslmode", "channel_binding"}


def _normalize_db_url(raw: str) -> Tuple[str, bool]:
    """
    Return (asyncpg_url, ssl_required).
    - Coerces postgres:// and postgresql:// to postgresql+asyncpg://
    - Strips libpq-only query params asyncpg rejects (sslmode, channel_binding)
    - ssl_required is True when sslmode requested SSL (require/verify-ca/verify-full)
    """
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw.startswith("postgresql://") and "+asyncpg" not in raw:
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)

    parts = urlsplit(raw)
    query = parse_qsl(parts.query, keep_blank_values=True)
    ssl_required = False
    kept = []
    for k, v in query:
        if k.lower() in _ASYNCPG_INCOMPATIBLE_PARAMS:
            if k.lower() == "sslmode" and v.lower() in ("require", "verify-ca", "verify-full"):
                ssl_required = True
            continue
        kept.append((k, v))
    cleaned = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment)
    )
    return cleaned, ssl_required


class Settings:
    """Application settings from environment"""
    
    # App
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "SuperAdvocate"
    
    # Database — accept Neon/Railway postgres:// and postgresql:// connection strings.
    # Strips asyncpg-incompatible params (sslmode/channel_binding) and records
    # whether SSL is required so engines can pass an SSL context via connect_args.
    _db_url_raw: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://nikhar:nikhar@localhost:5432/nikhar"
    )
    DATABASE_URL, DB_SSL_REQUIRED = _normalize_db_url(_db_url_raw)
    
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
    
    # eCourts mobile API — the same REST API used by the official eCourts Android app.
    # No licence or vendor token required. AES-128-CBC keys are baked into the app
    # (reverse-engineered; documented in github.com/akilvhora/court-meta).
    # Override only if the government moves the base URL.
    ECOURTS_MOBILE_BASE: str = os.getenv(
        "ECOURTS_MOBILE_BASE", "https://app.ecourts.gov.in/ecourt_mobile_DC"
    )

    # eCourtsIndia REST API (webapi.ecourtsindia.com) — licensed data vendor.
    # Bearer token from https://ecourtsindia.com/dashboard/settings
    ECOURTS_API_BASE: str = os.getenv("ECOURTS_API_BASE", "https://webapi.ecourtsindia.com")
    ECOURTS_API_TOKEN: str = os.getenv("ECOURTS_API_TOKEN", "")

    # SendGrid
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    
    # WhatsApp Business API
    WHATSAPP_API_TOKEN: str = os.getenv("WHATSAPP_API_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "change-me-in-production"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Application Insights
    APPLICATIONINSIGHTS_CONNECTION_STRING: Optional[str] = os.getenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        None
    )


settings = Settings()
