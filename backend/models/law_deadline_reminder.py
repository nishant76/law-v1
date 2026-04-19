"""
Deadline reminder model — tracks key dates and reminders
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, UUID, ForeignKey, DateTime, Boolean, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from .base import BaseModel


class ReminderType(str, enum.Enum):
    """Type of deadline reminder"""
    HEARING = "hearing"
    FILING_DEADLINE = "filing_deadline"
    LIMITATION_PERIOD = "limitation_period"
    URGENT = "urgent"


class ReminderStatus(str, enum.Enum):
    """Reminder sent status"""
    PENDING = "pending"
    SENT = "sent"
    MISSED = "missed"


class DeadlineReminder(BaseModel):
    """Deadline and reminder tracking"""
    __tablename__ = "deadline_reminders"
    __table_args__ = (
        Index("ix_deadline_reminders_deleted_at", "deleted_at"),
        Index("ix_deadline_reminders_firm_id", "firm_id"),
        Index("ix_deadline_reminders_matter_id", "matter_id"),
        Index("ix_deadline_reminders_reminder_date", "reminder_date"),
        {"schema": "law"},
    )

    firm_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("law.firms.id"), nullable=False)
    matter_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("law.matters.id"), nullable=False)

    # Reminder details
    reminder_type: Mapped[ReminderType] = mapped_column(Enum(ReminderType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Key date (30 days, 7 days, 1 day before reminder)
    key_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reminder_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Reminder channels
    status: Mapped[ReminderStatus] = mapped_column(Enum(ReminderStatus, values_callable=lambda x: [e.value for e in x]), default=ReminderStatus.PENDING, nullable=False, index=True)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    whatsapp_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # WhatsApp messaging
    whatsapp_message_template: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # Message to send to client
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # If deadline missed
    missed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<DeadlineReminder(id={self.id}, matter_id={self.matter_id}, type={self.reminder_type})>"
