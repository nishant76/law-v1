"""
Citation model — Indian law citations from judgments
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, UUID, ForeignKey, DateTime, Text, Integer, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import BaseModel


class Citation(BaseModel):
    """Legal citation from judgment database"""
    __tablename__ = "citations"
    __table_args__ = (
        Index("ix_citations_deleted_at", "deleted_at"),
        Index("ix_citations_citation_key", "citation_key"),
        Index("ix_citations_case_name", "case_name"),
        {"schema": "law"},
    )

    # Citation identification
    citation_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)  # e.g., "2024-SCC-1"
    case_name: Mapped[str] = mapped_column(String(500), nullable=False)

    # Court information
    court: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Supreme Court, High Court, District Court
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Parties
    petitioner: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    respondent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Judgment details
    judge_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    judgment_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Content
    judgment_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Full judgment text
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Editorial summary

    # Classification
    matter_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)  # civil, criminal, consumer, etc.
    outcome: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # granted, refused, allowed, dismissed, bail_granted, etc.

    # Citation string
    primary_citation: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # e.g., "(2024) 5 SCC 123"

    # Classification tags (JSON array stored as text, e.g., '["civil","writ","property"]')
    subject_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Sources
    official_source: Mapped[str] = mapped_column(String(100), nullable=False)  # eSCR, P&H HC, Punjab district court portals
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_doc_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Document ID on source website

    # Embedding for semantic search
    embedding_vector: Mapped[Optional[str]] = mapped_column(String(10000), nullable=True)  # JSON array or string representation

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<Citation(id={self.id}, case_name={self.case_name}, court={self.court}, year={self.year})>"
