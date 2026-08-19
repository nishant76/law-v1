"""
In-app notification endpoints — the bell in the app shell.

Notifications are firm-scoped. A row with `user_id = NULL` is visible to every
user in the firm; a row with a user_id is visible only to that user.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import CurrentUser, get_current_user, get_db, parse_uuid_or_404
from backend.core.logger import get_logger
from backend.models import Notification

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["notifications"])


def _visible_to(current_user: CurrentUser):
    """Firm-wide rows plus rows addressed to this user."""
    return (
        Notification.firm_id == uuid.UUID(current_user.firm_id),
        Notification.deleted_at.is_(None),
        or_(
            Notification.user_id.is_(None),
            Notification.user_id == uuid.UUID(current_user.user_id),
        ),
    )


@router.get("/notifications", response_model=dict)
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications, newest first, with the unread count for the badge."""
    try:
        conditions = list(_visible_to(current_user))
        if unread_only:
            conditions.append(Notification.read_at.is_(None))

        rows = list((await db.execute(
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )).scalars())

        unread_count = (await db.execute(
            select(func.count()).select_from(Notification)
            .where(*_visible_to(current_user), Notification.read_at.is_(None))
        )).scalar_one()

        return {
            "success": True,
            "data": {
                "unread_count": unread_count,
                "notifications": [
                    {
                        "id": str(n.id),
                        "type": n.notification_type.value,
                        "title": n.title,
                        "body": n.body,
                        "link_path": n.link_path,
                        "matter_id": str(n.matter_id) if n.matter_id else None,
                        "read": n.read_at is not None,
                        "created_at": n.created_at.isoformat(),
                    }
                    for n in rows
                ],
            },
        }
    except Exception as e:
        logger.error(f"Failed to list notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list notifications",
        )


@router.put("/notifications/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark one notification as read."""
    parse_uuid_or_404(notification_id, "Notification")
    try:
        result = await db.execute(
            update(Notification)
            .where(
                Notification.id == uuid.UUID(notification_id),
                *_visible_to(current_user),
                Notification.read_at.is_(None),
            )
            .values(read_at=datetime.now(timezone.utc))
        )
        await db.commit()
        if result.rowcount == 0:
            # Already read, or not this firm's — 404 either way.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
            )
        return {"success": True, "message": "Notification marked read"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to mark notification read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification read",
        )


@router.put("/notifications/read-all", response_model=dict)
async def mark_all_read(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark every visible unread notification as read."""
    try:
        result = await db.execute(
            update(Notification)
            .where(*_visible_to(current_user), Notification.read_at.is_(None))
            .values(read_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return {"success": True, "data": {"marked": result.rowcount}}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to mark all notifications read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notifications read",
        )
