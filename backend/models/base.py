"""
Database models base class and utilities
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, UUID
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy.sql import func

# Base class for all models
Base = declarative_base()


class BaseModel(Base):
    """
    Base model with common columns for all tables.

    Every table must inherit from this.
    """
    __abstract__ = True

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
