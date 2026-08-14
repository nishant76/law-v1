"""
In-app notification model.

Backs the notification bell in the app shell. A row is written by the reminder
job at the same moment the email/WhatsApp go out, so the lawyer sees the alert
even when both external channels are unconfigured or fail.

`user_id` is nullable: a NULL row is a firm-wide notification visible to every
user in the firm (used when a reminder belongs to a matter rather than to one
lawyer).
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, UUID, ForeignKey, DateTime, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class NotificationType(str, enum.Enum):
    """What produced the notification."""
    HEARING = "hearing"
    DEADLINE = "deadline"
    DEADLINE_MISSED = "deadline_missed"
    ECOURTS_SYNC = "ecourts_sync"
    DOCUMENT = "document"
    SYSTEM = "system"


class Notification(BaseModel):
    """In-app notification."""
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_deleted_at", "deleted_at"),
        Index("ix_notifications_firm_id", "firm_id"),
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_read_at", "read_at"),
        {"schema": "law"},
    )

    firm_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("law.firms.id"), nullable=False
    )
    # NULL = visible to the whole firm.
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("law.users.id"), nullable=True
    )
    matter_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("law.matters.id"), nullable=True
    )

    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Relative in-app path, e.g. "/app/cases/<id>". Never an external URL.
    link_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type={self.notification_type})>"
