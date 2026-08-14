"""
Matter fee installment model — one scheduled/received payment against a matter.

Total Fees, Paid, and Balance Due (the "fees strip" in the matter detail page,
per CLAUDE.md's CaseDetail Page Pattern) are all computed from this table —
sum(amount) = Total Fees, sum(amount where is_paid) = Paid, the difference
is Balance Due. No separate "agreed total" field on Matter, to avoid the two
numbers drifting out of sync.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, UUID, ForeignKey, DateTime, Boolean, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import BaseModel


class MatterFeeInstallment(BaseModel):
    """One fee installment (scheduled or received) against a matter."""
    __tablename__ = "matter_fee_installments"
    __table_args__ = (
        Index("ix_matter_fee_installments_deleted_at", "deleted_at"),
        Index("ix_matter_fee_installments_firm_id", "firm_id"),
        Index("ix_matter_fee_installments_matter_id", "matter_id"),
        {"schema": "law"},
    )

    firm_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("law.firms.id"), nullable=False)
    matter_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("law.matters.id"), nullable=False)

    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # e.g. "First installment", "Filing fee"
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    paid_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<MatterFeeInstallment(id={self.id}, matter_id={self.matter_id}, amount={self.amount}, is_paid={self.is_paid})>"
