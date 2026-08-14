"""
Hearing entry — one row per court date, per matter.

This is the diary proper. A physical lawyer's diary records, for each date:
which matters are listed, at what board/serial number, what stage each is at,
what actually happened, and the date it was adjourned to. `law.matters` only
carries the *next* hearing date, which cannot answer "what happened on the 14th"
or "how many adjournments has this matter had".

Two states:
  * SCHEDULED — the date is listed but has not happened yet (created from the
    eCourts sync or by the lawyer). Feeds the cause-list view and reminders.
  * a completed entry — `outcome` is filled in after the hearing; recording it
    rolls `next_date` back onto the matter and re-arms the reminder cadence.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, UUID, ForeignKey, DateTime, Boolean, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import BaseModel


class HearingStatus(str, enum.Enum):
    """Lifecycle of a listed date."""
    SCHEDULED = "scheduled"      # listed, not yet heard
    HELD = "held"                # heard, something happened
    ADJOURNED = "adjourned"      # taken up but put off to a new date
    NOT_TAKEN_UP = "not_taken_up"  # not reached / judge on leave
    DISPOSED = "disposed"        # matter finished on this date


class HearingEntry(BaseModel):
    """A single court date in the lawyer's diary."""
    __tablename__ = "hearing_entries"
    __table_args__ = (
        Index("ix_hearing_entries_deleted_at", "deleted_at"),
        Index("ix_hearing_entries_firm_id", "firm_id"),
        Index("ix_hearing_entries_matter_id", "matter_id"),
        Index("ix_hearing_entries_hearing_date", "hearing_date"),
        {"schema": "law"},
    )

    firm_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("law.firms.id"), nullable=False
    )
    matter_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("law.matters.id"), nullable=False
    )

    hearing_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[HearingStatus] = mapped_column(
        Enum(HearingStatus, values_callable=lambda x: [e.value for e in x]),
        default=HearingStatus.SCHEDULED,
        nullable=False,
        index=True,
    )

    # Cause-list context — what the lawyer needs to find the matter in court.
    court: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    judge_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Serial number on the day's cause list ("item 37").
    board_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Stage: arguments / evidence / framing of issues / reply / order.
    purpose: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Filled in after the hearing.
    outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    adjournment_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    next_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # What the lawyer must do before the next date.
    action_required: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Who appeared. Free text — a clerk or a proxy counsel is common and is not
    # necessarily a platform user.
    appeared_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # True when this row was created by the eCourts sync rather than by hand,
    # so the sync can update it without clobbering the lawyer's own entries.
    from_ecourts: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("law.users.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<HearingEntry(id={self.id}, matter_id={self.matter_id}, date={self.hearing_date})>"
