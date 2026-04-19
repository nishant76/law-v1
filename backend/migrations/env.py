"""Alembic migration environment — async SQLAlchemy 2.0 pattern"""
import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Add project root to sys.path so backend.* imports use the same module cache
# as the application — prevents duplicate Base / double table registration.
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.core.config import settings
from backend.models.base import Base
import backend.models  # noqa: F401 — registers all tables into Base.metadata

config = context.config

# Inject DATABASE_URL from environment / .env into alembic config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Called synchronously inside run_sync.
    transactional_ddl=False lets PostgreSQL commit each DDL statement
    immediately — avoids double-transaction conflict with async engine.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        transactional_ddl=False,
    )
    context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
