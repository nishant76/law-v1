"""
eCourts API — sync hearing dates for the logged-in lawyer's matters.

Endpoints:
  GET  /api/v1/ecourts/status          — integration status + profile fields on file
  PUT  /api/v1/ecourts/profile         — set bar council number + state code + advocate name
  GET  /api/v1/ecourts/states          — list of eCourts state codes (for UI dropdown)
  POST /api/v1/ecourts/sync            — advocate-search sync (requires bar council number)
  POST /api/v1/ecourts/refresh-cnr     — refresh hearing dates for all matters with CNR set
  GET  /api/v1/ecourts/case/{cnr}      — fetch a single case by CNR (used for CNR auto-fill)
  POST /api/v1/ecourts/discover        — one-time CNR discovery via ecourtsindia.com API (₹1)

Rules (CLAUDE.md):
- JWT on every endpoint; firm_id / user_id from JWT only.
- All logic in ecourts_service.py.
- Never fabricate hearing dates.

NOTE on sync strategy (Jun 2026): courtEstWebService.php is non-functional for
most states so the advocate-search /sync returns no results. Use /refresh-cnr
(CNR-based) as the reliable path — lawyers enter CNRs from their eCourts app
and we refresh hearing dates for each CNR automatically.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_db, get_current_user, CurrentUser
from backend.models.law_user import User
from backend.models.law_matter import Matter
from backend.services.ecourts_service import (
    get_ecourts_service,
    ECourtsError,
    ECourtsNotConfigured,
    ECOURTS_STATE_CODES,
)
from backend.services.ecourts_scraper_service import (
    get_cnrs_by_advocate,
    EcourtsDiscoveryNotConfigured,
    EcourtsDiscoveryError,
    ECOURTS_INDIA_STATE_CODES,
)
from backend.services.ecourts_api_service import (
    search_pending_cases,
    search_by_litigant_name,
    get_case_by_cnr as api_get_case_by_cnr,
    get_order_pdf as api_get_order_pdf,
    bulk_refresh as api_bulk_refresh,
    EcourtsAPIError,
    EcourtsAPINotConfigured,
    city_to_state_code,
    city_to_district_prefix,
    slug_to_advocate_name,
)
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/ecourts", tags=["ecourts"])


class EcourtsProfileRequest(BaseModel):
    bar_council_number: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        description="Enrollment number from state bar council, e.g. P/1234/2020",
    )
    ecourts_state_code: Optional[str] = Field(
        None,
        max_length=10,
        description="eCourts numeric state code, e.g. '3' for Punjab",
    )
    advocate_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=255,
        description="Advocate name as registered on eCourts (used as fallback)",
    )


async def _load_user(user_id: str, firm_id: str, session: AsyncSession) -> User:
    stmt = select(User).where(
        User.id == uuid.UUID(user_id),
        User.firm_id == uuid.UUID(firm_id),
        User.deleted_at.is_(None),
    )
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/status")
async def ecourts_status(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current eCourts integration status for the logged-in lawyer."""
    user = await _load_user(str(current_user.user_id), str(current_user.firm_id), db)

    # Count matters with CNR numbers set for this firm
    stmt = (
        select(Matter)
        .where(
            Matter.firm_id == current_user.firm_id,
            Matter.cnr_number.isnot(None),
            Matter.deleted_at.is_(None),
        )
    )
    matters_with_cnr = len((await db.execute(stmt)).scalars().all())

    return {
        "success": True,
        "bar_council_number": user.bar_council_number,
        "ecourts_state_code": user.ecourts_state_code,
        "advocate_name": user.ecourts_advocate_name,
        "ready_to_sync": bool(user.bar_council_number and user.ecourts_state_code),
        "cnr_sync_available": True,
        "matters_with_cnr": matters_with_cnr,
        "name_match_found": user.ecourts_name_match_found,
        "sync_note": (
            "CNR-based sync is active. Advocate-search sync requires Punjab/Haryana "
            "court establishment data which is not yet available in the eCourts mobile API."
        ),
    }


@router.put("/profile")
async def set_ecourts_profile(
    body: EcourtsProfileRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save bar council number, eCourts state code, and/or advocate name.
    At least bar_council_number + ecourts_state_code are required to enable sync.
    """
    if not any([body.bar_council_number, body.ecourts_state_code, body.advocate_name]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update.",
        )
    user = await _load_user(str(current_user.user_id), str(current_user.firm_id), db)
    if body.bar_council_number is not None:
        user.bar_council_number = body.bar_council_number.strip()
    if body.ecourts_state_code is not None:
        user.ecourts_state_code = body.ecourts_state_code.strip()
    if body.advocate_name is not None:
        user.ecourts_advocate_name = body.advocate_name.strip()
    await db.commit()
    return {
        "success": True,
        "bar_council_number": user.bar_council_number,
        "ecourts_state_code": user.ecourts_state_code,
        "advocate_name": user.ecourts_advocate_name,
        "ready_to_sync": bool(user.bar_council_number and user.ecourts_state_code),
    }


@router.get("/states")
async def list_states(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Returns known eCourts state codes (from local constant) plus a note
    to call the live API for the full list. Avoids a live API call on every
    page load — the codes don't change.
    """
    return {
        "success": True,
        "known_states": ECOURTS_STATE_CODES,
        "note": "Use GET /ecourts/states/live for the full authoritative list from eCourts.",
    }


@router.get("/states/live")
async def list_states_live(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Fetch the authoritative state list directly from the eCourts mobile API."""
    service = get_ecourts_service()
    try:
        states = await service.get_states()
    except (ECourtsError, httpx.HTTPError) as exc:
        logger.error(f"eCourts state list failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach eCourts. Try again later.",
        )
    return {"success": True, "states": states}


@router.post("/sync")
async def sync_hearings(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pull the lawyer's pending cases from eCourts (using their bar council number)
    and upsert them as Matters with updated next_hearing_date.
    """
    user = await _load_user(str(current_user.user_id), str(current_user.firm_id), db)

    if not user.bar_council_number or not user.ecourts_state_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Set your bar council enrollment number and state code first "
                "(PUT /api/v1/ecourts/profile)."
            ),
        )

    service = get_ecourts_service()
    try:
        result = await service.sync_firm_hearings(
            firm_id=str(current_user.firm_id),
            bar_code=user.bar_council_number,
            state_code=user.ecourts_state_code,
            session=db,
            advocate_name=user.ecourts_advocate_name,
        )
    except ECourtsError as exc:
        logger.error(f"eCourts sync error user={current_user.user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"eCourts sync failed: {exc}",
        )
    except httpx.HTTPError as exc:
        logger.error(f"eCourts HTTP error user={current_user.user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach eCourts. Try again later.",
        )
    except Exception as exc:
        logger.error(f"eCourts unexpected error user={current_user.user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="eCourts sync failed unexpectedly.",
        )

    return {"success": True, **result}


@router.post("/refresh-cnr")
async def refresh_cnr_hearings(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh hearing dates for every matter in this firm that has a CNR number set.

    This is the RELIABLE sync path (Jun 2026): the advocate-by-name search
    is currently non-functional for Punjab/Haryana because courtEstWebService
    returns no establishments.  Lawyers add their CNR numbers from the eCourts
    app; this endpoint keeps their next-hearing dates current.
    """
    stmt = (
        select(Matter)
        .where(
            Matter.firm_id == current_user.firm_id,
            Matter.cnr_number.isnot(None),
            Matter.deleted_at.is_(None),
        )
    )
    matters = (await db.execute(stmt)).scalars().all()

    if not matters:
        return {
            "success": True,
            "message": "No matters have a CNR number set yet.",
            "refreshed": 0,
            "failed": 0,
        }

    refreshed: List[str] = []
    failed: List[dict] = []

    # Trigger bulk async refresh on the eCourtsIndia API (fire-and-forget)
    all_cnrs = [m.cnr_number for m in matters]
    try:
        await api_bulk_refresh(all_cnrs)
    except Exception as exc:
        logger.warning("refresh-cnr: bulk refresh trigger failed: %s", exc)

    for matter in matters:
        try:
            case = await api_get_case_by_cnr(matter.cnr_number)
            if case.get("next_hearing_date"):
                matter.next_hearing_date = case["next_hearing_date"]
            matter.case_status = case.get("case_status") or matter.case_status
            matter.court = case.get("court_name") or matter.court
            matter.ecourts_synced_at = datetime.now(timezone.utc)
            refreshed.append(matter.cnr_number)
        except EcourtsAPIError as exc:
            logger.warning("CNR refresh failed cnr=%s: %s", matter.cnr_number, exc)
            failed.append({"cnr": matter.cnr_number, "error": str(exc)})
        except Exception as exc:
            logger.warning("CNR refresh unexpected error cnr=%s: %s", matter.cnr_number, exc)
            failed.append({"cnr": matter.cnr_number, "error": "Unexpected error"})

    await db.commit()
    return {
        "success": True,
        "refreshed": len(refreshed),
        "failed": len(failed),
        "failed_cnrs": failed,
    }


@router.get("/case/{cnr}")
async def get_case_by_cnr(
    cnr: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Fetch a single case's full detail by CNR number from the eCourtsIndia REST API.
    Returns parties, court, next hearing date, hearing history, and orders.
    Use this to verify or auto-fill a matter from a CNR.
    """
    cnr = cnr.strip().upper()
    if not cnr or len(cnr) < 10:
        raise HTTPException(status_code=400, detail="Invalid CNR format.")

    try:
        case = await api_get_case_by_cnr(cnr)
    except EcourtsAPINotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except EcourtsAPIError as exc:
        logger.warning("CNR lookup failed cnr=%s: %s", cnr, exc)
        raise HTTPException(status_code=502, detail=str(exc))

    return {"success": True, "cnr": cnr, "case": case}


@router.get("/case/{cnr}/order/{filename}")
async def get_case_order_pdf(
    cnr: str,
    filename: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Proxy the signed order PDF from the eCourtsIndia REST API.

    `filename` is the bare filename from a case detail's order `url` field
    (e.g. "order-1.pdf") — not a standalone link. The vendor API requires our
    server-side Bearer token, so the frontend fetches this through us rather
    than linking to eCourts directly.
    """
    cnr = cnr.strip().upper()
    if not cnr or len(cnr) < 10:
        raise HTTPException(status_code=400, detail="Invalid CNR format.")
    if not re.match(r'^[A-Za-z0-9_\-\.]+$', filename):
        raise HTTPException(status_code=400, detail="Invalid order filename.")

    try:
        content, content_type = await api_get_order_pdf(cnr, filename)
    except EcourtsAPINotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except EcourtsAPIError as exc:
        logger.warning("Order fetch failed cnr=%s filename=%s: %s", cnr, filename, exc)
        raise HTTPException(status_code=502, detail=str(exc))

    return Response(content=content, media_type=content_type)


# ── preview-my-cases — zero-input case preview for the dashboard CTA ─────────


@router.get("/preview-my-cases")
async def preview_my_cases(
    city: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch pending cases for the logged-in lawyer using their stored name.
    No slug or profile-picking needed — uses the user's own name from their profile.
    Called from the dashboard 'Connect eCourts' banner.
    """
    user = await _load_user(str(current_user.user_id), str(current_user.firm_id), db)
    advocate_name = (user.ecourts_advocate_name or user.name or "").strip()
    if not advocate_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No advocate name found. Set your name in profile settings.",
        )

    state_code: Optional[str] = None
    district_prefix: Optional[str] = None
    if city and city.strip():
        city_clean = city.strip().lower()
        state_code = city_to_state_code(city_clean)
        district_prefix = city_to_district_prefix(city_clean)

    try:
        cases = await search_pending_cases(
            advocate_name=advocate_name,
            state_code=state_code,
            district_prefix=district_prefix,
        )
    except EcourtsAPINotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except EcourtsAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        logger.error("preview-my-cases unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Case preview failed: {exc}")

    # "Check once" rule: the very first unfiltered check permanently records
    # whether the lawyer's name matched anything on eCourts. Once set, this is
    # never overwritten — a city-filtered call finding nothing doesn't count
    # (that could just mean the wrong city), so only gate on the broad search.
    if user.ecourts_name_match_found is None and not (city and city.strip()):
        user.ecourts_name_match_found = bool(cases)
        await db.commit()

    return {
        "success": True,
        "advocate_name": advocate_name,
        "city": city,
        "district_prefix": district_prefix,
        "cases": cases,
        "total": len(cases),
        "name_match_found": user.ecourts_name_match_found,
    }


@router.get("/search-cases")
async def search_cases_by_name(
    q: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manual fallback: look up PENDING cases by party/litigant name.

    Used in the "Connect eCourts" flow when the lawyer's own advocate-name
    match (preview-my-cases) finds nothing — they type a case/party name and
    pick the right one from live results. Narrowed to the lawyer's stored
    eCourts state code when set, to cut down same-name collisions.
    """
    q = q.strip()
    if len(q) < 3:
        raise HTTPException(status_code=400, detail="Type at least 3 characters.")

    user = await _load_user(str(current_user.user_id), str(current_user.firm_id), db)

    try:
        cases = await search_by_litigant_name(q, state_code=user.ecourts_state_code)
    except EcourtsAPINotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except EcourtsAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        logger.error("search-cases unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Case search failed: {exc}")

    return {"success": True, "query": q, "cases": cases, "total": len(cases)}


# ── ecourtsindia.com — search + discover + import ────────────────────────────


@router.get("/search-lawyers")
async def search_lawyers(
    q: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Search ecourtsindia.com for advocates matching `q`.
    Returns a list of matching lawyer profiles (name, court, profile slug).
    Called from the first-login onboarding step 1.
    """
    q = q.strip()
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Search term must be at least 2 characters.")

    try:
        from backend.services.ecourts_scraper_service import (
            search_lawyers as _search,
            EcourtsDiscoveryNotConfigured,
            EcourtsDiscoveryError,
        )
        profiles = await _search(q)
    except EcourtsDiscoveryNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except EcourtsDiscoveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.error(f"search-lawyers unexpected error: {exc}")
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}")

    return {"success": True, "query": q, "profiles": profiles, "total": len(profiles)}


@router.get("/lawyer-cases/{slug}")
async def get_lawyer_cases(
    slug: str,
    city: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Fetch PENDING cases for an advocate via the eCourtsIndia REST API.

    `slug` is the ecourtsindia.com profile slug (e.g. "ashish-gupta") — we
    convert it to an advocate name ("Ashish Gupta") and call the search API.

    `city` (e.g. "panchkula") narrows results to that district via a client-
    side filter on the CNR court-code prefix (e.g. "HRPK").  Without city,
    results are scoped to the advocate's state (if determinable) or returned
    globally.
    """
    slug = slug.strip().lower()
    if not slug or not re.match(r'^[a-z0-9\-\.]+$', slug):
        raise HTTPException(status_code=400, detail="Invalid profile slug.")

    advocate_name = slug_to_advocate_name(slug)
    state_code: Optional[str] = None
    district_prefix: Optional[str] = None

    if city and city.strip():
        city_clean = city.strip().lower()
        state_code = city_to_state_code(city_clean)
        district_prefix = city_to_district_prefix(city_clean)

    try:
        cases = await search_pending_cases(
            advocate_name=advocate_name,
            state_code=state_code,
            district_prefix=district_prefix,
        )
    except EcourtsAPINotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except EcourtsAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.error("lawyer-cases unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Case fetch failed: {exc}")

    return {
        "success": True,
        "slug": slug,
        "advocate_name": advocate_name,
        "cases": cases,
        "total": len(cases),
        "pages_fetched": None,
        "district_prefix": district_prefix,
    }


class ImportCaseData(BaseModel):
    cnr: str
    case_name: Optional[str] = None
    petitioner: Optional[str] = None
    respondent: Optional[str] = None
    court: Optional[str] = None
    case_type: Optional[str] = None
    status: Optional[str] = None


class ImportCnrsRequest(BaseModel):
    cnrs: List[str] = Field(default=[], description="Legacy: list of bare CNR strings.")
    cases: List[ImportCaseData] = Field(default=[], description="Full case objects from the scraper.")


@router.post("/import-cnrs")
async def import_cnrs(
    body: ImportCnrsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Import cases as Matters for this firm.
    Accepts either full case objects (preferred — from onboarding scrape) or
    bare CNR strings (legacy). After insert, attempts to enrich hearing dates
    via the eCourts mobile API (works for district courts; HC CNRs skip silently).
    """
    # Normalise: merge bare cnrs into case objects
    all_cases: List[ImportCaseData] = list(body.cases)
    for raw in body.cnrs:
        cnr = raw.strip().upper()
        if cnr and not any(c.cnr.upper() == cnr for c in all_cases):
            all_cases.append(ImportCaseData(cnr=cnr))

    if not all_cases:
        raise HTTPException(status_code=400, detail="No cases provided.")

    now = datetime.now(timezone.utc)
    imported: List[str] = []
    skipped: List[str] = []

    for item in all_cases:
        cnr = item.cnr.strip().upper()
        if not cnr or len(cnr) < 10:
            skipped.append(item.cnr)
            continue

        # Skip if already exists
        stmt = select(Matter).where(
            Matter.firm_id == current_user.firm_id,
            Matter.cnr_number == cnr,
            Matter.deleted_at.is_(None),
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            skipped.append(cnr)
            continue

        # Build case name from scraped parties, or fall back to CNR
        if item.case_name and item.case_name != cnr:
            case_name = item.case_name[:480]
        elif item.petitioner or item.respondent:
            p = item.petitioner or "Unknown"
            r = item.respondent or "Unknown"
            case_name = f"{p} vs {r}"[:480]
        else:
            case_name = cnr  # last resort placeholder

        matter = Matter(
            firm_id=current_user.firm_id,
            case_name=case_name,
            cnr_number=cnr,
            court=item.court,
            petitioner=item.petitioner,
            respondent=item.respondent,
            matter_type=item.case_type,
            case_status=item.status or "Pending",
            ecourts_tracked=True,
            ecourts_synced_at=now,
            is_active=True,
        )
        db.add(matter)
        imported.append(cnr)

    await db.commit()

    # Immediately enrich imported matters with full detail from the REST API
    refreshed = 0
    failed: List[dict] = []
    if imported:
        stmt2 = select(Matter).where(
            Matter.firm_id == current_user.firm_id,
            Matter.cnr_number.in_(imported),
            Matter.deleted_at.is_(None),
        )
        matters = (await db.execute(stmt2)).scalars().all()
        for matter in matters:
            try:
                case = await api_get_case_by_cnr(matter.cnr_number)
                # Overwrite with authoritative data from the API
                p = case.get("petitioner") or "Unknown"
                r = case.get("respondent") or "Unknown"
                matter.case_name = f"{p} vs {r}"[:480]
                matter.petitioner = case.get("petitioner") or matter.petitioner
                matter.respondent = case.get("respondent") or matter.respondent
                if case.get("next_hearing_date"):
                    matter.next_hearing_date = case["next_hearing_date"]
                matter.case_status = case.get("case_status") or "Pending"
                matter.court = case.get("court_name") or matter.court
                matter.matter_type = case.get("case_type") or matter.matter_type
                matter.ecourts_synced_at = datetime.now(timezone.utc)
                refreshed += 1
            except EcourtsAPIError as exc:
                logger.warning("import-cnrs: REST API refresh failed cnr=%s: %s", matter.cnr_number, exc)
                failed.append({"cnr": matter.cnr_number, "error": str(exc)})
            except Exception as exc:
                logger.warning("import-cnrs: unexpected error cnr=%s: %s", matter.cnr_number, exc)
                failed.append({"cnr": matter.cnr_number, "error": "Unexpected error"})

        await db.commit()

    return {
        "success": True,
        "imported": len(imported),
        "skipped": len(skipped),
        "refreshed": refreshed,
        "failed": failed,
    }


# ── ecourtsindia.com CNR discovery (legacy one-step flow) ────────────────────

class DiscoverRequest(BaseModel):
    state: Optional[str] = Field(
        None,
        description="State key from ECOURTS_INDIA_STATE_CODES, e.g. 'punjab'. "
                    "Narrows results to one state — strongly recommended to avoid "
                    "picking up cases for other advocates with the same name.",
    )


@router.post("/discover")
async def discover_cnrs(
    body: DiscoverRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    One-time CNR discovery via the ecourtsindia.com paid API (~₹1).

    Uses the logged-in lawyer's saved advocate name to find all their pending
    cases. Returns the CNR list for the lawyer to review before importing.

    Call this ONCE at signup. After that, use /refresh-cnr daily (free).
    Requires ECOURTS_API_TOKEN to be set.
    """
    user = await _load_user(str(current_user.user_id), str(current_user.firm_id), db)

    if not user.ecourts_advocate_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set your advocate name first (PUT /api/v1/ecourts/profile).",
        )

    state_code = ECOURTS_INDIA_STATE_CODES.get(body.state or "") if body.state else None

    try:
        result = await get_cnrs_by_advocate(
            name=user.ecourts_advocate_name,
            state_code=state_code,
            status="Pending",
        )
    except EcourtsDiscoveryNotConfigured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "eCourts discovery is not configured. "
                "Add ECOURTS_API_TOKEN to your environment variables."
            ),
        )
    except EcourtsDiscoveryError as exc:
        logger.error(f"eCourts discovery error user={current_user.user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"eCourts discovery failed: {exc}",
        )

    return {
        "success": True,
        "advocate_name": user.ecourts_advocate_name,
        "state": body.state,
        "cnrs": result["cnrs"],
        "total": result["total"],
        "note": (
            "Review this list and call POST /ecourts/import-cnrs to import "
            "the ones that belong to you."
        ),
    }


# ── Backward-compat alias ─────────────────────────────────────────────────────
# Old endpoint: PUT /advocate-name → maps to the new /profile endpoint.

class _LegacyAdvocateNameRequest(BaseModel):
    advocate_name: str = Field(..., min_length=2, max_length=255)


@router.put("/advocate-name", include_in_schema=False)
async def set_advocate_name_legacy(
    body: _LegacyAdvocateNameRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await _load_user(str(current_user.user_id), str(current_user.firm_id), db)
    user.ecourts_advocate_name = body.advocate_name.strip()
    await db.commit()
    return {"success": True, "advocate_name": user.ecourts_advocate_name}
