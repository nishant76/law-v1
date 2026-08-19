"""
Settings — the real firm and advocate profile.

This replaces a page that was entirely hardcoded: it displayed a different
advocate's name and bar council number, claimed WhatsApp reminders were
configured with an invented cadence, and claimed two-factor auth was enabled
when no such feature exists. Under the launch-quality mandate, a settings screen
asserting protections that are not real is the most dangerous kind of fake data,
so everything here reads and writes actual columns.

Fields live in two places and are exposed as one profile:
  * law.users  — the individual advocate (name, phone, bar council number,
                 eCourts identity, WhatsApp number, cause-list opt-in)
  * law.firms  — the chamber (name, city, state, plan)
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import CurrentUser, get_current_user, get_db
from backend.core.config import settings as app_settings
from backend.core.logger import get_logger
from backend.models import Firm, User
from backend.services.notification_service import (
    get_notification_service,
    normalise_phone,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class ProfileUpdate(BaseModel):
    """Every field optional — the UI saves one row at a time."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    bar_council_number: Optional[str] = Field(None, max_length=50)
    ecourts_advocate_name: Optional[str] = Field(None, max_length=255)
    ecourts_state_code: Optional[str] = Field(None, max_length=10)
    whatsapp_number: Optional[str] = Field(None, max_length=20)
    daily_cause_list_enabled: Optional[bool] = None
    # Firm-level
    firm_name: Optional[str] = Field(None, min_length=1, max_length=255)
    firm_city: Optional[str] = Field(None, max_length=100)
    firm_state: Optional[str] = Field(None, max_length=100)

    @field_validator("whatsapp_number", "phone")
    @classmethod
    def _check_phone(cls, v: Optional[str]) -> Optional[str]:
        # Empty string clears the field; anything else must be a usable number,
        # since a number we cannot dial is worse than no number at all.
        if v is None or v.strip() == "":
            return None
        if normalise_phone(v) is None:
            raise ValueError("Enter a valid phone number, e.g. 98765 43210")
        return v.strip()


def _profile_json(user: User, firm: Optional[Firm]) -> dict:
    notifier = get_notification_service()
    return {
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role if isinstance(user.role, str) else user.role.value,
            "bar_council_number": user.bar_council_number,
            "ecourts_advocate_name": user.ecourts_advocate_name,
            "ecourts_state_code": user.ecourts_state_code,
            "whatsapp_number": user.whatsapp_number,
            "daily_cause_list_enabled": user.daily_cause_list_enabled,
        },
        "firm": {
            "name": firm.name if firm else None,
            "city": firm.city if firm else None,
            "state": firm.state if firm else None,
            "plan": firm.plan if firm else None,
        },
        # What the server can actually do right now, so the page never claims a
        # channel is working when its provider is unconfigured.
        "capabilities": {
            "email_configured": notifier.email_configured,
            "whatsapp_configured": notifier.whatsapp_configured,
            "ecourts_configured": bool(app_settings.ECOURTS_API_TOKEN),
            "reminder_offsets_days": [30, 7, 1],
            "timezone": app_settings.LOCAL_TIMEZONE,
        },
    }


async def _load(current_user: CurrentUser, db: AsyncSession):
    user = (await db.execute(
        select(User).where(User.id == uuid.UUID(current_user.user_id), User.deleted_at.is_(None))
    )).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    firm = (await db.execute(
        select(Firm).where(Firm.id == uuid.UUID(current_user.firm_id))
    )).scalar_one_or_none()
    return user, firm


@router.get("/profile")
async def get_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The signed-in advocate's real profile, plus what the server can deliver."""
    user, firm = await _load(current_user, db)
    return {"success": True, "data": _profile_json(user, firm)}


@router.patch("/profile")
async def update_profile(
    body: ProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update advocate and chamber details."""
    user, firm = await _load(current_user, db)
    data = body.model_dump(exclude_unset=True)

    for field in (
        "name", "phone", "bar_council_number", "ecourts_advocate_name",
        "ecourts_state_code", "whatsapp_number", "daily_cause_list_enabled",
    ):
        if field in data:
            setattr(user, field, data[field])

    # Chamber details are firm-wide, so only an admin may change them.
    firm_fields = {"firm_name": "name", "firm_city": "city", "firm_state": "state"}
    wants_firm_change = any(f in data for f in firm_fields)
    if wants_firm_change:
        role = user.role if isinstance(user.role, str) else user.role.value
        if role not in ("firm_admin", "super_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a firm admin can change chamber details.",
            )
        if firm is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firm not found")
        for src, dest in firm_fields.items():
            if src in data:
                setattr(firm, dest, data[src])

    await db.commit()
    await db.refresh(user)
    if firm is not None:
        await db.refresh(firm)
    logger.info("Profile updated user_id=%s fields=%s", user.id, sorted(data))
    return {"success": True, "data": _profile_json(user, firm)}
