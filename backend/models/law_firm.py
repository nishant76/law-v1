"""
Firm model — represents a law firm or solo practitioner
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, UUID, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import BaseModel


class Firm(BaseModel):
    """Law firm or solo practitioner account"""
    __tablename__ = "firms"
    __table_args__ = (
        Index("ix_firms_deleted_at", "deleted_at"),
        {"schema": "law"},
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Location
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Chandigarh, Ludhiana, Amritsar, etc.
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Punjab, Haryana

    # Billing
    plan: Mapped[str] = mapped_column(String(50), default="trial", nullable=False)  # solo, small, mid, large
    trial_days: Mapped[int] = mapped_column(Integer, default=30)
    trial_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Judge data collection flag (Phase 1 — no feature UI yet)
    collect_judge_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<Firm(id={self.id}, name={self.name}, plan={self.plan})>"
