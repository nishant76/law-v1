"""
Search history model — track searches for analytics
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, UUID, ForeignKey, DateTime, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import BaseModel


class SearchHistory(BaseModel):
    """Record of search queries for analytics"""
    __tablename__ = "search_history"
    __table_args__ = (
        Index("ix_search_history_deleted_at", "deleted_at"),
        Index("ix_search_history_firm_id", "firm_id"),
        Index("ix_search_history_user_id", "user_id"),
        Index("ix_search_history_created_at", "created_at"),
        {"schema": "law"},
    )

    firm_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("law.firms.id"), nullable=False)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("law.users.id"), nullable=True)

    # Search query
    query: Mapped[str] = mapped_column(Text, nullable=False)

    # Search scope
    search_scope: Mapped[str] = mapped_column(String(100), default="both")  # both, own_documents, public_judgments

    # Results
    results_from_own_documents: Mapped[int] = mapped_column(Integer, default=0)
    results_from_public_judgments: Mapped[int] = mapped_column(Integer, default=0)

    # Timing
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    search_filters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: outcome filter, court filter, etc.

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<SearchHistory(id={self.id}, firm_id={self.firm_id}, query={self.query[:50]})>"
