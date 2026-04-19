"""
Audit log model — platform-wide audit trail
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, UUID, DateTime, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from backend.models.base import Base


class AuditLog(Base):
    """Platform-wide audit trail in shared schema"""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_deleted_at", "deleted_at"),
        Index("ix_audit_logs_firm_id", "firm_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        {"schema": "shared"}
    )

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )

    # Who did it
    firm_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # What happened
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # login, create_document, generate_draft, etc.
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # document, draft, matter, user, firm
    resource_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Details
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON with action-specific details

    # HTTP
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    http_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # IP address
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, firm_id={self.firm_id}, action={self.action})>"
