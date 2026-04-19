"""
Draft model — generated legal documents
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, UUID, ForeignKey, DateTime, Text, Enum, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from .base import BaseModel


class DraftType(str, enum.Enum):
    """Type of legal draft"""
    CASE_SYNOPSIS = "case_synopsis"
    SMART_REPLY = "smart_reply"
    FILING_DRAFT = "filing_draft"
    OTHER = "other"


class DraftStatus(str, enum.Enum):
    """Draft generation status"""
    GENERATING = "generating"
    GENERATED = "generated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Draft(BaseModel):
    """Generated legal document draft"""
    __tablename__ = "drafts"
    __table_args__ = (
        Index("ix_drafts_deleted_at", "deleted_at"),
        Index("ix_drafts_firm_id", "firm_id"),
        Index("ix_drafts_matter_id", "matter_id"),
        Index("ix_drafts_status", "status"),
        {"schema": "law"},
    )

    firm_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("law.firms.id"), nullable=False)
    matter_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("law.matters.id"), nullable=True)

    # Generation info
    draft_type: Mapped[DraftType] = mapped_column(Enum(DraftType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    status: Mapped[DraftStatus] = mapped_column(Enum(DraftStatus, values_callable=lambda x: [e.value for e in x]), default=DraftStatus.GENERATING, nullable=False, index=True)

    # Content
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Quality metrics
    quality_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    citation_safety_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100: verify citations
    completeness_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    legal_accuracy_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    language_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100

    # Metadata
    generated_by_user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("law.users.id"), nullable=True)
    filing_objective: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # win_on_merits, delay, jurisdiction, settlement, appeal

    # Acceptance
    accepted_by_user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("law.users.id"), nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Export
    exported_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # docx, pdf, etc.

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<Draft(id={self.id}, draft_type={self.draft_type}, status={self.status})>"
