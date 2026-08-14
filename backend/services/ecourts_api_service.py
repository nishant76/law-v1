"""
eCourtsIndia REST API service (webapi.ecourtsindia.com).

Replaces the broken eCourts mobile API for all case lookups and hearing date
sync.  Token is stored as ECOURTS_API_TOKEN in the environment (Bearer auth).

Public functions:
  search_pending_cases()  — onboarding: find all pending cases for an advocate
  get_case_by_cnr()       — CNR detail (parties, hearing dates, orders)
  bulk_refresh()          — trigger async refresh for a batch of CNRs
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# City → state / district helpers
# ---------------------------------------------------------------------------

CITY_TO_STATE_CODE: Dict[str, str] = {
    # Haryana
    "panchkula": "HR", "ambala": "HR", "gurugram": "HR", "gurgaon": "HR",
    "faridabad": "HR", "sirsa": "HR", "hisar": "HR", "rohtak": "HR",
    "karnal": "HR", "sonipat": "HR", "kurukshetra": "HR", "panipat": "HR",
    "bhiwani": "HR", "fatehabad": "HR", "jhajjar": "HR", "kaithal": "HR",
    "mahendragarh": "HR", "nuh": "HR", "palwal": "HR", "rewari": "HR",
    "yamunanagar": "HR",
    # Punjab
    "ludhiana": "PB", "amritsar": "PB", "jalandhar": "PB", "patiala": "PB",
    "mohali": "PB", "bathinda": "PB", "sangrur": "PB", "hoshiarpur": "PB",
    "ferozepur": "PB", "gurdaspur": "PB", "moga": "PB", "pathankot": "PB",
    # Chandigarh
    "chandigarh": "CH",
}

CITY_TO_DISTRICT_PREFIX: Dict[str, str] = {
    "panchkula": "HRPK", "ambala": "HRAM", "gurugram": "HRGR", "gurgaon": "HRGR",
    "faridabad": "HRFD", "sirsa": "HRSI", "hisar": "HRHI", "rohtak": "HRRK",
    "karnal": "HRKR", "sonipat": "HRSN", "kurukshetra": "HRKK", "panipat": "HRPN",
    "bhiwani": "HRBW", "fatehabad": "HRFT", "jhajjar": "HRJJ", "kaithal": "HRKT",
    "ludhiana": "PBLD", "amritsar": "PBAR", "jalandhar": "PBJL", "patiala": "PBPT",
    "mohali": "PBMO", "bathinda": "PBBT", "chandigarh": "CHCH",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class EcourtsAPIError(Exception):
    """API returned an error or was unreachable."""


class EcourtsAPINotConfigured(Exception):
    """ECOURTS_API_TOKEN is not set."""


# ---------------------------------------------------------------------------
# HTTP client helper
# ---------------------------------------------------------------------------

def _client() -> httpx.AsyncClient:
    token = settings.ECOURTS_API_TOKEN
    if not token:
        raise EcourtsAPINotConfigured(
            "ECOURTS_API_TOKEN is not configured. Add it to your .env file."
        )
    base = settings.ECOURTS_API_BASE.rstrip("/")
    return httpx.AsyncClient(
        base_url=base,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def search_pending_cases(
    advocate_name: str,
    state_code: Optional[str] = None,
    district_prefix: Optional[str] = None,
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    """
    Fetch ALL pending cases for an advocate from the eCourtsIndia REST API.

    Args:
        advocate_name:    Full name as registered on eCourts (e.g. "Ashish Gupta")
        state_code:       Two-letter state code to narrow (e.g. "HR" for Haryana)
        district_prefix:  CNR prefix to filter results (e.g. "HRPK" for Panchkula)
                          Applied client-side after fetching.
        page_size:        Results per page; max 100.

    Returns a list of normalised case dicts (cnr, case_name, petitioner, respondent,
    court, case_type, status, next_hearing_date, filing_date, court_code).
    """
    params: Dict[str, Any] = {
        "Advocates": advocate_name,
        "CaseStatuses": "PENDING",
        "PageSize": min(page_size, 100),
        "SortBy": "nextHearingDate",
        "SortOrder": "asc",
    }
    if state_code:
        params["StateCodes"] = state_code

    all_cases: List[Dict[str, Any]] = []
    page = 1

    async with _client() as http:
        while True:
            params["Page"] = page
            try:
                r = await http.get("/api/partner/search", params=params)
                r.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise EcourtsAPIError(
                    f"Search failed (HTTP {exc.response.status_code}): "
                    f"{exc.response.text[:300]}"
                ) from exc
            except httpx.HTTPError as exc:
                raise EcourtsAPIError(f"Network error reaching eCourts API: {exc}") from exc

            data = r.json().get("data", {})
            results: List[Dict] = data.get("results", [])

            for c in results:
                cnr = c.get("cnr") or c.get("id") or ""
                if not cnr:
                    continue
                # Client-side district filter
                if district_prefix:
                    court_code = c.get("courtCode", "")
                    if not court_code.upper().startswith(district_prefix.upper()):
                        continue
                all_cases.append(_normalise_search_result(c))

            if not data.get("hasNextPage", False):
                break
            page += 1
            if page > 50:
                logger.warning(
                    "ecourts_api.search_pending_cases: reached 50-page limit "
                    "for advocate=%r", advocate_name
                )
                break

    logger.info(
        "ecourts_api.search_pending_cases: advocate=%r state=%r prefix=%r -> %d cases",
        advocate_name, state_code, district_prefix, len(all_cases),
    )
    return all_cases


async def search_judgments_live(
    query: str,
    state_codes: Optional[List[str]] = None,
    top: int = 20,
) -> List[Dict[str, Any]]:
    """
    Full-text search over eCourtsIndia cases using the `Query` parameter.
    Unlike advocate/litigant search, `Query` matches across case names, sections,
    acts, and order text — suitable for legal concept searches.

    Used by SearchService to populate "Find Judgments" in real time when the
    local law.citations table has no results.

    Args:
        query:       User's search string (e.g. "bail section 138 cheque bounce")
        state_codes: State codes to filter (default: HR, PB, CH for Punjab/Haryana/Chandigarh)
        top:         Max results to return (max 100 per API page)
    """
    query = query.strip()
    if len(query) < 3:
        return []

    if state_codes is None:
        state_codes = ["HR", "PB", "CH"]

    params: Dict[str, Any] = {
        "Query": query,
        "PageSize": min(top, 100),
        "Page": 1,
    }
    if state_codes:
        params["StateCodes"] = ",".join(state_codes)

    async with _client() as http:
        try:
            r = await http.get("/api/partner/search", params=params)
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise EcourtsAPIError(
                f"Judgment search failed (HTTP {exc.response.status_code}): "
                f"{exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise EcourtsAPIError(f"Network error reaching eCourts API: {exc}") from exc

    results = r.json().get("data", {}).get("results", [])
    cases = [_normalise_search_result(c) for c in results if (c.get("cnr") or c.get("id"))]
    logger.info(
        "ecourts_api.search_judgments_live: query=%r states=%r -> %d results",
        query[:60], state_codes, len(cases),
    )
    return cases


async def search_by_litigant_name(
    query: str,
    state_code: Optional[str] = None,
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """
    Search PENDING cases by party/litigant name via the eCourtsIndia REST API's
    `Litigants` filter — matches both petitioner and respondent side, unlike
    `Petitioners`/`Respondents` alone which can miss a party buried in a long
    cause title, and unlike `Query` (full-text over orders too) which produces
    false positives for a name lookup.

    Manual fallback in the "Connect eCourts" flow when the lawyer's own
    advocate-name match returns nothing. Single page only — this backs a
    live-typing search box, not a bulk import.
    """
    query = query.strip()
    if len(query) < 3:
        return []

    params: Dict[str, Any] = {
        "Litigants": query,
        "CaseStatuses": "PENDING",
        "PageSize": min(page_size, 100),
        "Page": 1,
        "SortBy": "nextHearingDate",
        "SortOrder": "asc",
    }
    if state_code:
        params["StateCodes"] = state_code

    async with _client() as http:
        try:
            r = await http.get("/api/partner/search", params=params)
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise EcourtsAPIError(
                f"Search failed (HTTP {exc.response.status_code}): "
                f"{exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise EcourtsAPIError(f"Network error reaching eCourts API: {exc}") from exc

    results = r.json().get("data", {}).get("results", [])
    cases = [_normalise_search_result(c) for c in results if (c.get("cnr") or c.get("id"))]
    logger.info(
        "ecourts_api.search_by_litigant_name: query=%r state=%r -> %d cases",
        query, state_code, len(cases),
    )
    return cases


async def get_case_by_cnr(cnr: str) -> Dict[str, Any]:
    """
    Fetch full case detail for a single CNR from the eCourtsIndia REST API.

    Returns a normalised dict with parties, dates, judges, hearing history,
    and orders.  Raises EcourtsAPIError if the CNR is not found.
    """
    cnr = cnr.strip().upper()
    async with _client() as http:
        try:
            r = await http.get(f"/api/partner/case/{cnr}")
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise EcourtsAPIError(f"CNR {cnr} not found on eCourts.")
            raise EcourtsAPIError(
                f"CNR lookup failed (HTTP {exc.response.status_code})"
            ) from exc
        except httpx.HTTPError as exc:
            raise EcourtsAPIError(f"Network error reaching eCourts API: {exc}") from exc

    body = r.json()
    # The API wraps the case data in courtCaseData; fall back to data directly
    d = (body.get("data") or {}).get("courtCaseData") or body.get("data") or {}
    return _normalise_case_detail(d)


async def get_order_pdf(cnr: str, filename: str) -> tuple[bytes, str]:
    """
    Fetch the signed (certified copy) PDF for one order.

    `filename` is the bare filename from an order's `url` field (e.g.
    "order-1.pdf") — NOT a standalone link. The vendor API requires the same
    Bearer token as every other call, so the frontend can't hit this directly;
    it must proxy through our backend (see /ecourts/case/{cnr}/order/{filename}).

    Returns (content_bytes, content_type).
    """
    cnr = cnr.strip().upper()
    filename = filename.strip()
    async with _client() as http:
        try:
            r = await http.get(f"/api/partner/case/{cnr}/order/{filename}")
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise EcourtsAPIError(f"Order {filename} not found for case {cnr}.")
            raise EcourtsAPIError(
                f"Order fetch failed (HTTP {exc.response.status_code})"
            ) from exc
        except httpx.HTTPError as exc:
            raise EcourtsAPIError(f"Network error reaching eCourts API: {exc}") from exc

    content_type = r.headers.get("content-type", "application/pdf")
    return r.content, content_type


async def bulk_refresh(cnrs: List[str]) -> None:
    """
    Trigger an async refresh for up to 50 CNRs per call.
    The API refreshes asynchronously; results appear when dateModified advances.
    """
    if not cnrs:
        return
    async with _client() as http:
        for i in range(0, len(cnrs), 50):
            chunk = [c.strip().upper() for c in cnrs[i : i + 50]]
            try:
                r = await http.post("/api/partner/case/bulk-refresh", json={"cnrs": chunk})
                r.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning(
                    "ecourts_api.bulk_refresh: chunk %d failed: %s", i // 50, exc
                )


# ---------------------------------------------------------------------------
# Internal normalisers
# ---------------------------------------------------------------------------

def _normalise_search_result(c: Dict[str, Any]) -> Dict[str, Any]:
    """
    Field shape verified live against `GET /api/partner/search` on 2026-07-11 —
    the raw response carries far more per-case metadata than we used to keep
    (judges, filing/registration numbers, bench type, order/hearing counts,
    filing year, etc.). Surfacing it here so the Connect eCourts list and the
    manual case-search results aren't reduced to just name + CNR + court.
    """
    petitioners = c.get("petitioners") or []
    respondents = c.get("respondents") or []
    pet = petitioners[0] if petitioners else ""
    res = respondents[0] if respondents else ""
    return {
        "cnr": c.get("cnr") or c.get("id") or "",
        "case_name": f"{pet} vs {res}" if (pet or res) else (c.get("cnr") or ""),
        "petitioner": ", ".join(petitioners),
        "respondent": ", ".join(respondents),
        "pet_adv": ", ".join(c.get("petitionerAdvocates") or []),
        "res_adv": ", ".join(c.get("respondentAdvocates") or []),
        "court": c.get("courtName") or "",
        "court_code": c.get("courtCode") or "",
        "case_type": c.get("caseType") or "",
        "status": c.get("caseStatus") or "PENDING",
        "next_hearing_date": c.get("nextHearingDate"),
        "last_hearing_date": c.get("lastHearingDate"),
        "first_hearing_date": c.get("firstHearingDate"),
        "filing_date": c.get("filingDate"),
        "filing_number": c.get("filingNumber") or "",
        "registration_number": c.get("registrationNumber") or "",
        "registration_date": c.get("registrationDate"),
        "decision_date": c.get("decisionDate"),
        "judges": c.get("judges") or [],
        "acts_and_sections": c.get("actsAndSections") or [],
        "case_category": c.get("caseCategory") or "",
        "bench_type": c.get("benchType") or "",
        "state_code": c.get("stateCode") or "",
        "filing_year": c.get("filingYear"),
        "has_orders": bool(c.get("hasOrders")),
        "has_judgments": bool(c.get("hasJudgments")),
        "order_count": c.get("orderCount"),
        "hearing_count": c.get("hearingCount"),
    }


def _normalise_case_detail(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Field shape verified live against `GET /api/partner/case/{cnr}` on
    2026-07-11 (courtCaseData payload). Notable corrections vs. the previous
    version: historyOfCaseHearings items use judge/businessOnDate/hearingDate/
    purposeOfListing (not passed through raw before); interimOrders items only
    reliably carry orderDate + description (no orderUrl unless the case has
    actual PDF/markdown files in `files.files[]` — the `has_order_documents`
    flag below reflects whether any exist, since most cases in the wild are
    metadata-only with no digitised order text yet). `processes` (notices/
    process-service events) and `judgment_orders` (final judgments, distinct
    from interim orders) were previously dropped entirely.
    """
    petitioners = d.get("petitioners") or []
    respondents = d.get("respondents") or []
    files = ((d.get("files") or {}).get("files")) or []
    return {
        "cnr": d.get("cnr") or "",
        "case_name": (
            f"{petitioners[0]} vs {respondents[0]}"
            if (petitioners and respondents)
            else d.get("cnr") or ""
        ),
        "petitioners": petitioners,
        "respondents": respondents,
        "petitioner": ", ".join(petitioners),
        "respondent": ", ".join(respondents),
        "petitioner_advocates": d.get("petitionerAdvocates") or [],
        "respondent_advocates": d.get("respondentAdvocates") or [],
        "court_name": d.get("courtName") or "",
        "court_code": d.get("cnrCourtCode") or d.get("courtComplexCode") or "",
        "case_type": d.get("caseType") or "",
        "case_type_raw": d.get("caseTypeRaw") or "",
        "case_type_sub": d.get("caseTypeSub") or "",
        "case_status": d.get("caseStatus") or "PENDING",
        "filing_date": d.get("filingDate"),
        "filing_number": d.get("filingNumber") or "",
        "registration_date": d.get("registrationDate"),
        "registration_number": d.get("registrationNumber") or "",
        "next_hearing_date": d.get("nextHearingDate"),
        "last_hearing_date": d.get("lastHearingDate"),
        "first_hearing_date": d.get("firstHearingDate"),
        "decision_date": d.get("decisionDate"),
        "stage_of_case": d.get("stageOfCaseRaw") or d.get("stageOfCase") or "",
        "purpose": d.get("purpose") or "",
        "judges": d.get("judges") or [],
        "judge_codes": d.get("judgeCode") or [],
        "hearing_history": [
            {
                "hearing_date": h.get("hearingDate"),
                "business_on_date": h.get("businessOnDate"),
                "judge": h.get("judge"),
                "purpose": h.get("purposeOfListing"),
            }
            for h in (d.get("historyOfCaseHearings") or [])
        ],
        "orders": [
            {
                "date": o.get("orderDate"),
                "description": o.get("description"),
                "url": o.get("orderUrl"),
            }
            for o in (d.get("interimOrders") or [])
        ],
        "judgment_orders": [
            {
                "date": o.get("orderDate"),
                "description": o.get("description"),
                "url": o.get("orderUrl"),
            }
            for o in (d.get("judgmentOrders") or [])
        ],
        "processes": [
            {"date": p.get("processDate"), "title": p.get("processTitle")}
            for p in (d.get("processes") or [])
        ],
        "has_order_documents": bool(files),
        "order_count": d.get("orderCount"),
        "interim_order_count": d.get("interimOrderCount"),
        "judgment_count": d.get("judgmentCount"),
        "hearing_count": d.get("hearingCount"),
        "district": d.get("district") or "",
        "state": d.get("state") or "",
    }


# ---------------------------------------------------------------------------
# City helpers (used by endpoints)
# ---------------------------------------------------------------------------

def city_to_state_code(city: str) -> Optional[str]:
    return CITY_TO_STATE_CODE.get(city.strip().lower())


def city_to_district_prefix(city: str) -> Optional[str]:
    return CITY_TO_DISTRICT_PREFIX.get(city.strip().lower())


def slug_to_advocate_name(slug: str) -> str:
    """Convert ecourtsindia.com profile slug to advocate name.
    'ashish-gupta' -> 'Ashish Gupta'
    """
    return " ".join(part.capitalize() for part in slug.strip().lower().split("-"))
