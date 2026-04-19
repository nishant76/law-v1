"""
Database connection and session management
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from backend.core.config import settings

# Celery prefork workers inherit the parent process's asyncpg connections.
# Those connections are bound to the parent's event loop, which is gone in
# the child. Each asyncio.run() in a task also creates a fresh event loop,
# making pooled connections stale immediately. NullPool disables connection
# pooling entirely — each async with AsyncSessionLocal() opens and closes a
# fresh connection — which is the correct pattern for Celery workers.
_in_celery_worker = os.getenv("CELERY_WORKER", "false").lower() == "true"

if _in_celery_worker:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
        connect_args={
            "timeout": 10,
            "command_timeout": 10,
            "server_settings": {"search_path": "law,shared,public"},
        },
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=5,
        max_overflow=10,
        connect_args={
            "timeout": 10,
            "command_timeout": 10,
            "server_settings": {"search_path": "law,shared,public"},
        },
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session():
    """Dependency injection for FastAPI endpoints"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
