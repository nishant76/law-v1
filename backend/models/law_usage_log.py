"""
Usage logs model — track API usage for billing and limits
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, UUID, ForeignKey, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import BaseModel


class UsageLog(BaseModel):
    """API usage tracking for quota and billing"""
    __tablename__ = "usage_logs"
    __table_args__ = (
        Index("ix_usage_logs_deleted_at", "deleted_at"),
        Index("ix_usage_logs_firm_id", "firm_id"),
        Index("ix_usage_logs_created_at", "created_at"),
        {"schema": "law"},
    )

    firm_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("law.firms.id"), nullable=False)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("law.users.id"), nullable=True)

    # Action type
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # document_upload, search, draft_generate, etc.

    # Resource details
    resource_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)  # document_id, draft_id, matter_id, etc.
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # document, draft, search, etc.

    # Tokens used (for AI actions)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)  # for LLM calls

    # Metadata
    endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # correlation ID

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<UsageLog(id={self.id}, firm_id={self.firm_id}, action={self.action})>"
