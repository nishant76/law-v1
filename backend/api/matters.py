"""
Matters API — list and manage legal matters for the firm.
GET /api/v1/matters — list all matters (sorted by next hearing date)
"""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.api.deps import get_db, get_current_user
from backend.core.dependencies import CurrentUser
from backend.models.law_matter import Matter
from backend.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/matters", tags=["matters"])


@router.get("")
async def list_matters(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Matter)
        .where(
            and_(
                Matter.firm_id == uuid.UUID(current_user.firm_id),
                Matter.deleted_at.is_(None),
            )
        )
        .order_by(Matter.next_hearing_date.asc().nullslast(), Matter.created_at.desc())
    )
    matters = result.scalars().all()

    return {
        "success": True,
        "matters": [
            {
                "id": str(m.id),
                "case_name": m.case_name,
                "cnr_number": m.cnr_number,
                "matter_number": m.matter_number,
                "court": m.court,
                "petitioner": m.petitioner,
                "respondent": m.respondent,
                "case_status": m.case_status,
                "next_hearing_date": (
                    m.next_hearing_date.date().isoformat() if m.next_hearing_date else None
                ),
                "is_active": m.is_active,
                "ecourts_tracked": m.ecourts_tracked,
                "created_at": m.created_at.isoformat(),
            }
            for m in matters
        ],
        "total": len(matters),
    }
