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
        "case_type": c.get("caseType") or "",
        "status": c.get("caseStatus") or "PENDING",
        "next_hearing_date": c.get("nextHearingDate"),
        "filing_date": c.get("filingDate"),
        "court_code": c.get("courtCode") or "",
    }


def _normalise_case_detail(d: Dict[str, Any]) -> Dict[str, Any]:
    petitioners = d.get("petitioners") or []
    respondents = d.get("respondents") or []
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
        "court_name": d.get("courtName") or "",
        "court_code": d.get("cnrCourtCode") or d.get("courtComplexCode") or "",
        "case_type": d.get("caseTypeRaw") or d.get("caseType") or "",
        "case_type_sub": d.get("caseTypeSub") or "",
        "case_status": d.get("caseStatus") or "PENDING",
        "filing_date": d.get("filingDate"),
        "registration_date": d.get("registrationDate"),
        "filing_number": d.get("filingNumber") or "",
        "next_hearing_date": d.get("nextHearingDate"),
        "last_hearing_date": d.get("lastHearingDate"),
        "first_hearing_date": d.get("firstHearingDate"),
        "stage_of_case": d.get("stageOfCase") or "",
        "judges": d.get("judges") or [],
        "hearing_history": d.get("historyOfCaseHearings") or [],
        "orders": [
            {
                "date": o.get("orderDate"),
                "description": o.get("description"),
                "url": o.get("orderUrl"),
            }
            for o in (d.get("interimOrders") or [])
        ],
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
