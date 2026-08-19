"""
Matters API — list and manage legal matters for the firm.

GET    /api/v1/matters                    — list all matters (sorted by next hearing date)
GET    /api/v1/matters/{id}                — full matter detail (fees, client info, eCourts data if linked)
PATCH  /api/v1/matters/{id}                — update case/client fields
POST   /api/v1/matters/{id}/fees           — add a fee installment
PATCH  /api/v1/matters/{id}/fees/{fee_id}  — update a fee installment (amount/due date/paid status)
DELETE /api/v1/matters/{id}/fees/{fee_id}  — remove a fee installment

Total Fees / Paid / Balance Due are always computed from the installment
rows — never stored directly on the matter, so the numbers can't drift out
of sync (CLAUDE.md CaseDetail Page Pattern — "fees strip").
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, case

from backend.api.deps import get_db, get_current_user
from backend.core.dependencies import CurrentUser
from backend.models.law_matter import Matter
from backend.models.law_matter_fee_installment import MatterFeeInstallment
from backend.services.ecourts_api_service import (
    get_case_by_cnr as api_get_case_by_cnr,
    EcourtsAPIError,
    EcourtsAPINotConfigured,
)
from backend.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/matters", tags=["matters"])


def _matter_summary(m: Matter) -> dict:
    return {
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


async def _load_matter(matter_id: str, current_user: CurrentUser, db: AsyncSession) -> Matter:
    try:
        mid = uuid.UUID(matter_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matter not found")

    stmt = select(Matter).where(
        Matter.id == mid,
        Matter.firm_id == uuid.UUID(current_user.firm_id),
        Matter.deleted_at.is_(None),
    )
    matter = (await db.execute(stmt)).scalar_one_or_none()
    if not matter:
        # Never reveal whether a matter exists for another firm — 404, not 403.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matter not found")
    return matter


def _fee_json(f: MatterFeeInstallment) -> dict:
    return {
        "id": str(f.id),
        "label": f.label,
        "amount": float(f.amount),
        "due_date": f.due_date.date().isoformat() if f.due_date else None,
        "is_paid": f.is_paid,
        "paid_date": f.paid_date.date().isoformat() if f.paid_date else None,
    }


async def _fee_installments(matter_id: uuid.UUID, firm_id: uuid.UUID, db: AsyncSession):
    stmt = (
        select(MatterFeeInstallment)
        .where(
            MatterFeeInstallment.matter_id == matter_id,
            MatterFeeInstallment.firm_id == firm_id,
            MatterFeeInstallment.deleted_at.is_(None),
        )
        .order_by(MatterFeeInstallment.due_date.asc().nullslast(), MatterFeeInstallment.created_at.asc())
    )
    return (await db.execute(stmt)).scalars().all()


@router.get("")
async def list_matters(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    The cases list.

    Carries client name and the fee balance alongside each matter: a lawyer
    scanning 100+ rows thinks in terms of "which client" and "who still owes
    me", not CNR strings. Fee totals come from ONE grouped aggregate joined to
    the matter query — never a per-row query, which would be 100+ round trips
    on a real practice.
    """
    firm_id = uuid.UUID(current_user.firm_id)

    # agreed = every installment; paid = those marked paid. Balance is the
    # difference, computed in SQL so the list and the detail page agree.
    fee_totals = (
        select(
            MatterFeeInstallment.matter_id.label("matter_id"),
            func.coalesce(func.sum(MatterFeeInstallment.amount), 0).label("agreed"),
            func.coalesce(
                func.sum(
                    case((MatterFeeInstallment.is_paid.is_(True), MatterFeeInstallment.amount), else_=0)
                ),
                0,
            ).label("paid"),
        )
        .where(
            MatterFeeInstallment.firm_id == firm_id,
            MatterFeeInstallment.deleted_at.is_(None),
        )
        .group_by(MatterFeeInstallment.matter_id)
        .subquery()
    )

    result = await db.execute(
        select(Matter, fee_totals.c.agreed, fee_totals.c.paid)
        .outerjoin(fee_totals, fee_totals.c.matter_id == Matter.id)
        .where(
            and_(
                Matter.firm_id == firm_id,
                Matter.deleted_at.is_(None),
            )
        )
        .order_by(Matter.next_hearing_date.asc().nullslast(), Matter.created_at.desc())
    )
    rows = result.all()

    matters = []
    for m, agreed, paid in rows:
        agreed_f = float(agreed or 0)
        paid_f = float(paid or 0)
        matters.append({
            **_matter_summary(m),
            "client_name": m.client_name,
            "fees": {
                "agreed": agreed_f,
                "paid": paid_f,
                "due": agreed_f - paid_f,
            },
        })

    return {
        "success": True,
        "matters": matters,
        "total": len(matters),
    }


@router.get("/{matter_id}")
async def get_matter(
    matter_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full matter detail: case fields, client info, fee installments (with
    computed totals), and — if this matter has a CNR — the live eCourts case
    detail (judges, hearing history, orders, processes). The eCourts call is
    best-effort: a failure there never breaks the rest of the page, since the
    matter's own data should always be viewable regardless of eCourts status.
    """
    matter = await _load_matter(matter_id, current_user, db)
    fees = await _fee_installments(matter.id, matter.firm_id, db)

    total_fees = sum(float(f.amount) for f in fees)
    paid = sum(float(f.amount) for f in fees if f.is_paid)

    ecourts_case = None
    ecourts_error = None
    if matter.cnr_number:
        try:
            ecourts_case = await api_get_case_by_cnr(matter.cnr_number)
        except EcourtsAPINotConfigured as exc:
            ecourts_error = str(exc)
        except EcourtsAPIError as exc:
            logger.warning("matter detail: eCourts fetch failed cnr=%s: %s", matter.cnr_number, exc)
            ecourts_error = str(exc)

    return {
        "success": True,
        "matter": {
            **_matter_summary(matter),
            "judge_name": matter.judge_name,
            "matter_type": matter.matter_type,
            "description": matter.description,
            "filing_date": matter.filing_date.date().isoformat() if matter.filing_date else None,
            "limitation_date": matter.limitation_date.date().isoformat() if matter.limitation_date else None,
            "client_name": matter.client_name,
            "client_phone": matter.client_phone,
            "whatsapp_reminders_enabled": matter.whatsapp_reminders_enabled,
        },
        "fees": {
            "total": total_fees,
            "paid": paid,
            "due": total_fees - paid,
            "installments": [_fee_json(f) for f in fees],
        },
        "ecourts_case": ecourts_case,
        "ecourts_error": ecourts_error,
    }


class UpdateMatterRequest(BaseModel):
    case_name: Optional[str] = Field(None, min_length=1, max_length=500)
    court: Optional[str] = Field(None, max_length=255)
    matter_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    client_name: Optional[str] = Field(None, max_length=255)
    client_phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    whatsapp_reminders_enabled: Optional[bool] = None


@router.patch("/{matter_id}")
async def update_matter(
    matter_id: str,
    body: UpdateMatterRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    matter = await _load_matter(matter_id, current_user, db)

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(matter, field, value)

    await db.commit()
    await db.refresh(matter)
    return {"success": True, "matter": _matter_summary(matter)}


class FeeInstallmentRequest(BaseModel):
    label: Optional[str] = Field(None, max_length=255)
    amount: float = Field(..., gt=0)
    due_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    is_paid: bool = False
    paid_date: Optional[str] = Field(None, description="YYYY-MM-DD")


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date: {s!r}. Use YYYY-MM-DD.")


@router.post("/{matter_id}/fees")
async def add_fee_installment(
    matter_id: str,
    body: FeeInstallmentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    matter = await _load_matter(matter_id, current_user, db)

    fee = MatterFeeInstallment(
        firm_id=matter.firm_id,
        matter_id=matter.id,
        label=body.label,
        amount=body.amount,
        due_date=_parse_date(body.due_date),
        is_paid=body.is_paid,
        paid_date=_parse_date(body.paid_date),
    )
    db.add(fee)
    await db.commit()
    await db.refresh(fee)
    return {"success": True, "fee": _fee_json(fee)}


class UpdateFeeInstallmentRequest(BaseModel):
    label: Optional[str] = Field(None, max_length=255)
    amount: Optional[float] = Field(None, gt=0)
    due_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    is_paid: Optional[bool] = None
    paid_date: Optional[str] = Field(None, description="YYYY-MM-DD")


async def _load_fee(matter_id: uuid.UUID, fee_id: str, firm_id: uuid.UUID, db: AsyncSession) -> MatterFeeInstallment:
    try:
        fid = uuid.UUID(fee_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fee installment not found")

    stmt = select(MatterFeeInstallment).where(
        MatterFeeInstallment.id == fid,
        MatterFeeInstallment.matter_id == matter_id,
        MatterFeeInstallment.firm_id == firm_id,
        MatterFeeInstallment.deleted_at.is_(None),
    )
    fee = (await db.execute(stmt)).scalar_one_or_none()
    if not fee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fee installment not found")
    return fee


@router.patch("/{matter_id}/fees/{fee_id}")
async def update_fee_installment(
    matter_id: str,
    fee_id: str,
    body: UpdateFeeInstallmentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    matter = await _load_matter(matter_id, current_user, db)
    fee = await _load_fee(matter.id, fee_id, matter.firm_id, db)

    updates = body.model_dump(exclude_unset=True)
    if "due_date" in updates:
        updates["due_date"] = _parse_date(updates["due_date"])
    if "paid_date" in updates:
        updates["paid_date"] = _parse_date(updates["paid_date"])
    for field, value in updates.items():
        setattr(fee, field, value)

    await db.commit()
    await db.refresh(fee)
    return {"success": True, "fee": _fee_json(fee)}


@router.delete("/{matter_id}/fees/{fee_id}")
async def delete_fee_installment(
    matter_id: str,
    fee_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    matter = await _load_matter(matter_id, current_user, db)
    fee = await _load_fee(matter.id, fee_id, matter.firm_id, db)

    fee.deleted_at = datetime.now(timezone.utc)  # soft delete only
    await db.commit()
    return {"success": True}
