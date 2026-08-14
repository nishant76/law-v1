"""
Deadline API endpoints
Handles deadline creation, listing, marking missed, and condonation drafts
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import CurrentUser, get_current_user, get_db
from backend.models import DeadlineReminder, ReminderType, ReminderStatus, Draft
from backend.services.deadline_service import get_deadline_service
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["deadlines"])


@router.post("/deadlines", response_model=dict)
async def create_deadline(
    matter_id: str,
    deadline_type: ReminderType,
    deadline_date: datetime,
    description: str,
    client_phone: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new deadline reminder

    Args:
        matter_id: Matter ID
        deadline_type: Type of deadline
        deadline_date: Key date for the deadline
        description: Description
        client_phone: Client phone for WhatsApp (optional)

    Returns:
        The reminder set created for this deadline (30 / 7 / 1 days before,
        skipping any offset already in the past).
    """
    try:
        service = get_deadline_service()
        reminders = await service.create_deadline(
            session=db,
            matter_id=matter_id,
            firm_id=current_user.firm_id,
            deadline_type=deadline_type,
            deadline_date=deadline_date,
            description=description,
            client_phone=client_phone,
        )

        return {
            "success": True,
            "data": {
                "key_date": deadline_date.isoformat(),
                "reminders": [
                    {
                        "id": str(r.id),
                        "reminder_type": r.reminder_type.value,
                        "title": r.title,
                        "key_date": r.key_date.isoformat(),
                        "reminder_date": r.reminder_date.isoformat(),
                        "status": r.status.value,
                    }
                    for r in reminders
                ],
            },
        }

    except Exception as e:
        logger.error(f"Failed to create deadline: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create deadline",
        )


@router.get("/deadlines", response_model=dict)
async def list_upcoming_deadlines(
    days_ahead: int = 30,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List upcoming deadlines for the firm

    Args:
        days_ahead: Number of days to look ahead (default 30)

    Returns:
        List of upcoming deadlines
    """
    try:
        service = get_deadline_service()
        deadlines = await service.get_upcoming_deadlines(
            session=db,
            firm_id=current_user.firm_id,
            days_ahead=days_ahead,
        )

        # `deadline_type` / `urgency` are what the UI filters on. `status` here
        # is the reminder's own delivery state (pending/sent/missed) and is kept
        # separate from urgency, which is derived from the key date.
        now = datetime.now(timezone.utc)
        deadline_list = []
        for d, matter in deadlines:
            key_date = d.key_date if d.key_date.tzinfo else d.key_date.replace(tzinfo=timezone.utc)
            days_remaining = (key_date - now).days
            if d.status == ReminderStatus.MISSED or days_remaining < 0:
                urgency = "missed"
            elif days_remaining <= 3:
                urgency = "urgent"
            else:
                urgency = "upcoming"
            deadline_list.append({
                "id": str(d.id),
                "matter_id": str(d.matter_id),
                "matter_title": matter.case_name if matter else d.title,
                "court": matter.court if matter else None,
                "case_number": matter.matter_number if matter else None,
                "deadline_type": d.reminder_type.value,
                "title": d.title,
                "description": d.description,
                "due_date": key_date.isoformat(),
                "reminder_date": d.reminder_date.isoformat(),
                "days_remaining": days_remaining,
                "urgency": urgency,
                "delivery_status": d.status.value,
                "whatsapp_enabled": bool(matter.whatsapp_reminders_enabled) if matter else False,
            })

        return {
            "success": True,
            "data": deadline_list,
        }

    except Exception as e:
        logger.error(f"Failed to list deadlines: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list deadlines",
        )


@router.put("/deadlines/{deadline_id}/missed", response_model=dict)
async def mark_deadline_missed(
    deadline_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a deadline as missed

    Args:
        deadline_id: Deadline ID

    Returns:
        Success status
    """
    try:
        service = get_deadline_service()
        success = await service.mark_deadline_missed(
            session=db,
            deadline_id=deadline_id,
            firm_id=current_user.firm_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deadline not found",
            )

        return {
            "success": True,
            "message": "Deadline marked as missed",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark deadline missed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark deadline as missed",
        )


@router.post("/deadlines/{deadline_id}/condonation", response_model=dict)
async def generate_condonation_draft(
    deadline_id: str,
    reason_for_delay: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate condonation of delay draft for missed deadline

    Args:
        deadline_id: Deadline ID
        reason_for_delay: Reason for the delay

    Returns:
        Generated draft details
    """
    try:
        service = get_deadline_service()
        draft = await service.generate_condonation_draft(
            session=db,
            deadline_id=deadline_id,
            firm_id=current_user.firm_id,
            reason_for_delay=reason_for_delay,
        )

        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deadline not found",
            )

        return {
            "success": True,
            "data": {
                "draft_id": str(draft.id),
                "title": draft.title,
                "status": draft.status.value,
                "confidence_score": draft.confidence_score,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate condonation draft: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate condonation draft",
        )


@router.delete("/deadlines/{deadline_id}", response_model=dict)
async def delete_deadline(
    deadline_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft delete a deadline

    Args:
        deadline_id: Deadline ID

    Returns:
        Success status
    """
    try:
        import uuid as _uuid
        from sqlalchemy import update
        from backend.models import DeadlineReminder

        stmt = (
            update(DeadlineReminder)
            .where(
                DeadlineReminder.id == _uuid.UUID(deadline_id),
                DeadlineReminder.firm_id == _uuid.UUID(current_user.firm_id),
                DeadlineReminder.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(timezone.utc))
        )

        result = await db.execute(stmt)
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deadline not found",
            )

        return {
            "success": True,
            "message": "Deadline deleted",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete deadline: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete deadline",
        )