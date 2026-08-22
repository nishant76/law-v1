"""
Matter model — represents a legal case or matter
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, UUID, ForeignKey, DateTime, Text, Boolean, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import BaseModel


class Matter(BaseModel):
    """Legal matter (case)"""
    __tablename__ = "matters"
    __table_args__ = (
        Index("ix_matters_deleted_at", "deleted_at"),
        Index("ix_matters_firm_id", "firm_id"),
        Index("ix_matters_matter_number", "firm_id", "matter_number"),
        {"schema": "law"},
    )

    firm_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("law.firms.id"), nullable=False)

    # Case identification
    matter_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "SLP-2026-001"
    case_name: Mapped[str] = mapped_column(String(500), nullable=False)

    # Court information
    court: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # e.g., "District Court, Amritsar"
    judge_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Matter type (for Linear Process Guide)
    matter_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # civil, criminal, consumer, cheque_bounce, etc.

    # Parties
    petitioner: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    respondent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Key dates
    filing_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_hearing_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    limitation_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # For deadline tracking

    # eCourts integration — CNR is the 16-char Case Number Record used to fetch
    # case status / hearing dates from the eCourts data API.
    cnr_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    case_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # PENDING/DISPOSED/etc from eCourts
    ecourts_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ecourts_tracked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # auto-created/maintained from eCourts sync

    # Matter metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Fees — the agreed total fee for this matter. Installments track the
    # payment schedule against this number. Paid = sum of paid installments.
    agreed_fee: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    # Client information
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # WhatsApp reminders (from deadline tracker)
    whatsapp_reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<Matter(id={self.id}, case_name={self.case_name}, court={self.court})>"
