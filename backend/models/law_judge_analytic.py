"""
Judge analytics model — collect judge data for Phase 2 feature
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, UUID, ForeignKey, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import BaseModel


class JudgeAnalytic(BaseModel):
    """Judge behavior analytics — Phase 1 collection, Phase 2 feature"""
    __tablename__ = "judge_analytics"
    __table_args__ = (
        Index("ix_judge_analytics_deleted_at", "deleted_at"),
        Index("ix_judge_analytics_judge_name", "judge_name"),
        Index("ix_judge_analytics_year", "year"),
        {"schema": "law"},
    )

    # Judge identification
    judge_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    court: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Matter information
    matter_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)  # civil, criminal, consumer, etc.
    outcome: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # granted, refused, allowed, dismissed, etc.

    # Citation linking
    citation_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("law.citations.id"), nullable=True)

    # Temporal data
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Judge tracking (for transfers)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # When posted to court
    transferred_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # When transferred to another court

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<JudgeAnalytic(id={self.id}, judge_name={self.judge_name}, court={self.court}, year={self.year})>"
