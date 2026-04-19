"""
User model — represents a lawyer, staff member, or admin
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, UUID, Boolean, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from .base import BaseModel


class UserRole(str, enum.Enum):
    """User roles in the platform"""
    SUPER_ADMIN = "super_admin"
    FIRM_ADMIN = "firm_admin"
    LAWYER = "lawyer"
    STAFF = "staff"
    TRIAL = "trial"


class User(BaseModel):
    """User account — lawyer, staff, or admin"""
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_deleted_at", "deleted_at"),
        Index("ix_users_firm_id", "firm_id"),
        Index("ix_users_email", "email"),
        {"schema": "law"},
    )

    firm_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("law.firms.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Authentication
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Authorization
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.LAWYER, nullable=False, index=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # JWT blacklist tracking
    last_token_issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
