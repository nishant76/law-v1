"""
Diary API — the lawyer's court diary.

Endpoints are read-heavy: the day view is what a lawyer opens every morning.
All writes go through DiaryService; this module only validates and shapes.
"""
from datetime import date as date_cls, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import CurrentUser, get_current_user, get_db, parse_uuid_or_404
from backend.core.logger import get_logger
from backend.models import HearingStatus
from backend.services.diary_service import get_diary_service, local_today

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["diary"])


class CreateEntryRequest(BaseModel):
    matter_id: str
    hearing_date: datetime
    court: Optional[str] = None
    judge_name: Optional[str] = None
    board_number: Optional[str] = Field(default=None, max_length=20)
    purpose: Optional[str] = Field(default=None, max_length=255)
    appeared_by: Optional[str] = Field(default=None, max_length=255)


class RecordOutcomeRequest(BaseModel):
    status: HearingStatus
    outcome: Optional[str] = None
    next_date: Optional[datetime] = None
    adjournment_reason: Optional[str] = Field(default=None, max_length=500)
    action_required: Optional[str] = None
    appeared_by: Optional[str] = Field(default=None, max_length=255)
    board_number: Optional[str] = Field(default=None, max_length=20)


@router.get("/diary", response_model=dict)
async def get_diary_day(
    day: Optional[date_cls] = Query(None, description="Local (IST) date; defaults to today"),
    days: int = Query(1, ge=1, le=90, description="Number of days from `day`"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cause list for a date, or for a range starting at that date.

    `days=1` (default) is the day view. `days=7` gives the week.
    """
    try:
        service = get_diary_service()
        firm_id = current_user.firm_id
        target = day or local_today()

        # Materialise entries for matters whose hearing dates arrived through
        # the eCourts sync but were never opened in the diary.
        await service.ensure_scheduled_entries(db, firm_id=firm_id)

        if days == 1:
            entries = await service.get_day(db, firm_id, target)
        else:
            entries = await service.get_range(db, firm_id, target, target + timedelta(days=days - 1))

        return {
            "success": True,
            "data": {
                "date": target.isoformat(),
                "days": days,
                "entries": entries,
                "count": len(entries),
            },
        }
    except Exception as e:
        logger.error(f"Failed to load diary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load diary",
        )


@router.get("/diary/matters/{matter_id}", response_model=dict)
async def get_matter_diary(
    matter_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full hearing history for one matter — every date, most recent first."""
    # Outside the try: the 404 this raises must not be swallowed by the generic
    # handler below and re-reported as a 500.
    parse_uuid_or_404(matter_id, "Matter")
    try:
        service = get_diary_service()
        entries = await service.get_matter_history(db, current_user.firm_id, matter_id)
        return {"success": True, "data": {"entries": entries, "count": len(entries)}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load matter diary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load matter diary",
        )


@router.post("/diary", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_diary_entry(
    payload: CreateEntryRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a court date to the diary by hand."""
    parse_uuid_or_404(payload.matter_id, "Matter")
    try:
        service = get_diary_service()
        entry = await service.create_entry(
            session=db,
            firm_id=current_user.firm_id,
            matter_id=payload.matter_id,
            hearing_date=payload.hearing_date,
            created_by=current_user.user_id,
            court=payload.court,
            judge_name=payload.judge_name,
            board_number=payload.board_number,
            purpose=payload.purpose,
            appeared_by=payload.appeared_by,
        )
        if entry is None:
            # Wrong firm → 404, never 403 (never reveal existence).
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Matter not found"
            )
        return {"success": True, "data": {"id": str(entry.id)}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create diary entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create diary entry",
        )


@router.patch("/diary/{entry_id}", response_model=dict)
async def record_hearing_outcome(
    entry_id: str,
    payload: RecordOutcomeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Record what happened on a court date.

    Supplying `next_date` rolls the matter forward: it creates the next
    scheduled entry, updates the matter, and arms fresh 30/7/1 reminders.
    """
    parse_uuid_or_404(entry_id, "Diary entry")
    try:
        service = get_diary_service()
        entry = await service.record_outcome(
            session=db,
            firm_id=current_user.firm_id,
            entry_id=entry_id,
            status=payload.status,
            outcome=payload.outcome,
            next_date=payload.next_date,
            adjournment_reason=payload.adjournment_reason,
            action_required=payload.action_required,
            appeared_by=payload.appeared_by,
            board_number=payload.board_number,
        )
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found"
            )
        return {"success": True, "data": entry}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record hearing outcome: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record hearing outcome",
        )
