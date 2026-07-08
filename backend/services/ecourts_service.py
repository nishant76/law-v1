"""
eCourts Service — calls the eCourts mobile app REST API directly.

Base URL: https://app.ecourts.gov.in/ecourt_mobile_DC/

All requests are AES-128-CBC encrypted. The keys and IV construction were
reverse-engineered from the eCourts Android APK and are publicly documented
in github.com/akilvhora/court-meta (EncryptionHelper.cs).

No CAPTCHA, no licensed vendor, no scraping — this is the same REST API the
official eCourts mobile app uses. Build with a graceful fallback in case
endpoint shapes change without notice.

Auth flow:
  1. GET appReleaseWebService.php (no auth header) → JWT token + JSESSION cookie
  2. All subsequent: Authorization: Bearer <AES-encrypt(jwt)>
  3. JWT rotates — update from every successful response

CNR sync flow (primary — advocate-by-name search is not reliable for all states):
  1. Lawyer adds cases by CNR number from their eCourts app
  2. refresh_cnr() → caseHistoryWebService.php → next hearing date
  3. Daily Celery job refreshes all matters that have cnr_number set

Advocate sync flow (secondary — requires court establishment data to be indexed):
  1. searchByAdvocateName.php with bar council number
  2. For each CNR: caseHistoryWebService.php → hearing dates
  3. NOTE: as of Jun 2026, courtEstWebService is non-functional for many states
     so advocate search returns no_of_establishments=0.  The CNR-based flow is
     the reliable path.
"""
import asyncio
import base64
import json
import secrets
import socket
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from cryptography.hazmat.backends import default_backend
from backend.core.config import settings
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.law_matter import Matter
from backend.core.logger import get_logger

logger = get_logger(__name__)

# ── Crypto constants (from eCourts Android APK via court-meta) ───────────────
_ENCRYPT_KEY = bytes.fromhex("4D6251655468576D5A7134743677397A")
_DECRYPT_KEY = bytes.fromhex("3273357638782F413F4428472B4B6250")

# Each is 8 bytes (16 hex chars); combined with a random 8-byte suffix → 16-byte IV
_GLOBAL_IVS = [
    "556A586E32723575",
    "34743777217A2543",
    "413F4428472B4B62",
    "48404D635166546A",
    "614E645267556B58",
    "655368566D597133",
]

_MOBILE_BASE = settings.ECOURTS_MOBILE_BASE.rstrip("/")
_APP_VERSION = "9.0"
# uid must be "HOSTNAME:in.gov.ecourts.eCourtsServices" — the server uses this as
# a device identifier; omitting the hostname prefix causes the bootstrap to return
# token=null (confirmed via live testing Jun 2026).
_APP_UID = f"{socket.gethostname()}:in.gov.ecourts.eCourtsServices"

# Correct eCourts state codes — verified via districtWebService.php Jun 2026
# (old wrong values were punjab=3/haryana=6/chandigarh=4 which are Karnataka/Assam/Kerala)
ECOURTS_STATE_CODES: Dict[str, str] = {
    "punjab": "22",
    "haryana": "14",
    "chandigarh": "27",
    "delhi": "26",
    "himachal_pradesh": "5",
}


# ── AES-128-CBC helpers ───────────────────────────────────────────────────────

def _encrypt(data: Any) -> str:
    """
    Serialize data to JSON, encrypt with AES-128-CBC, and return the
    transport string: randomIV(16hex) + globalIndex(1digit) + base64(cipher).
    """
    payload = json.dumps(data, separators=(",", ":"))
    idx = secrets.randbelow(len(_GLOBAL_IVS))
    random_iv_hex = secrets.token_hex(8)                       # 16 hex chars
    iv = bytes.fromhex(_GLOBAL_IVS[idx] + random_iv_hex)      # 32 hex → 16 bytes

    cipher = Cipher(algorithms.AES(_ENCRYPT_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(payload.encode("utf-8")) + padder.finalize()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    return random_iv_hex + str(idx) + base64.b64encode(ciphertext).decode("utf-8")


def _decrypt(result: str) -> Optional[Dict[str, Any]]:
    """
    Decrypt an eCourts response string → parsed JSON dict.
    Returns None on any failure so callers can handle gracefully.
    """
    try:
        result = result.strip()
        if len(result) < 32:
            return None
        iv = bytes.fromhex(result[:32])
        cipher_bytes = base64.b64decode(result[32:].strip())

        cipher = Cipher(algorithms.AES(_DECRYPT_KEY), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_plain = decryptor.update(cipher_bytes) + decryptor.finalize()
        unpadder = sym_padding.PKCS7(128).unpadder()
        plain = unpadder.update(padded_plain) + unpadder.finalize()

        # Strip non-printable chars (the mobile app does this before JSON.parse)
        text = "".join(c for c in plain.decode("utf-8") if c.isprintable() or c in "\n\r\t")
        return json.loads(text)
    except Exception as exc:
        logger.debug(f"eCourts decrypt failed: {exc}")
        return None


# ── Token service ─────────────────────────────────────────────────────────────

class _TokenService:
    """
    Manages the eCourts JWT.
    Bootstrap: GET appReleaseWebService.php (no auth) → first token.
    Rotation: each successful response may carry an updated token.
    On 401: invalidate and re-bootstrap once.
    """

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._lock = asyncio.Lock()

    def update(self, data: Dict[str, Any]) -> None:
        if token := data.get("token"):
            self._token = str(token)

    def invalidate(self) -> None:
        self._token = None

    async def get(self, client: httpx.AsyncClient) -> str:
        async with self._lock:
            if self._token:
                return self._token
            params = _encrypt({"version": _APP_VERSION, "uid": _APP_UID})
            resp = await client.get(
                f"{_MOBILE_BASE}/appReleaseWebService.php",
                params={"params": params},
                timeout=20.0,
            )
            resp.raise_for_status()
            data = _decrypt(resp.text)
            if not data or not data.get("token"):
                raise ECourtsError("eCourts bootstrap failed — no token in response")
            self._token = str(data["token"])
            logger.info("eCourts JWT bootstrapped successfully")
            return self._token


# ── Exceptions ────────────────────────────────────────────────────────────────

class ECourtsError(RuntimeError):
    """Raised when the eCourts mobile API returns an error or unreadable response."""


class ECourtsNotConfigured(RuntimeError):
    """Raised when required lawyer profile data (bar council number) is not set."""


# ── HTTP client ───────────────────────────────────────────────────────────────

class _ECourtsHTTPClient:
    """
    Thin async HTTP client over the encrypted mobile API.

    Uses a single persistent httpx.AsyncClient so that JSESSION cookies set
    during bootstrap survive across subsequent API calls.  The client is
    created lazily on the first request (event loop must be running).
    """

    def __init__(self, tokens: _TokenService) -> None:
        self._tokens = tokens
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        async with self._client_lock:
            if self._client is None or self._client.is_closed:
                self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self._client

    async def close(self) -> None:
        async with self._client_lock:
            if self._client and not self._client.is_closed:
                await self._client.aclose()
                self._client = None

    async def get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt params, attach JWT Bearer, call the endpoint.
        Retries once on 401 (re-bootstraps the token).
        """
        encrypted_params = _encrypt(params)
        client = await self._get_client()

        for attempt in range(2):
            token = await self._tokens.get(client)
            headers = {"Authorization": f"Bearer {_encrypt(token)}"}

            resp = await client.get(
                f"{_MOBILE_BASE}/{endpoint}",
                params={"params": encrypted_params},
                headers=headers,
            )
            resp.raise_for_status()

            data = _decrypt(resp.text)
            if not data:
                raise ECourtsError(
                    f"eCourts returned unreadable response from {endpoint}"
                )

            if data.get("status") == "N" and str(data.get("status_code")) == "401":
                if attempt == 0:
                    logger.warning("eCourts 401 — invalidating token and retrying")
                    self._tokens.invalidate()
                    continue
                raise ECourtsError("eCourts authentication failed after token refresh")

            self._tokens.update(data)
            return data

        raise ECourtsError("eCourts: max retries exceeded")


# ── Response parsers ──────────────────────────────────────────────────────────

def _parse_date(val: Any) -> Optional[datetime]:
    if not val or not isinstance(val, str):
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(val.strip()[:10], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _to_list(val: Any) -> List[str]:
    """Coerce a party field (string or list) to a clean list of names."""
    if isinstance(val, list):
        return [str(v).strip() for v in val if str(v).strip()]
    if isinstance(val, str):
        return [p.strip() for p in val.split(",") if p.strip()]
    return []


# CNR prefix → eCourts state code (first 2 chars of CNR are state abbreviation)
_CNR_PREFIX_TO_STATE: Dict[str, str] = {
    "PB": "22",   # Punjab
    "HR": "14",   # Haryana
    "CH": "27",   # Chandigarh
    "DL": "26",   # Delhi
    "HP": "5",    # Himachal Pradesh
    "MH": "1",    # Maharashtra
    "KA": "3",    # Karnataka
    "TN": "10",   # Tamil Nadu
    "UP": "13",   # Uttar Pradesh
    "RJ": "9",    # Rajasthan
}


def _state_code_from_cnr(cnr: str) -> str:
    """Infer eCourts state code from a CNR number (first 2 chars = state code)."""
    prefix = cnr.strip().upper()[:2]
    return _CNR_PREFIX_TO_STATE.get(prefix, "22")  # default Punjab


def _parse_advocate_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    searchByAdvocateName response groups cases by establishment code as the key.
    Values may be lists of case dicts OR '#'-delimited row strings.
    We flatten all groups into a list of {cino, ...} dicts.
    """
    SKIP = {"status", "status_code", "msg", "token", "message"}
    cases: List[Dict[str, Any]] = []

    for key, val in data.items():
        if key in SKIP:
            continue
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    cases.append(item)
        elif isinstance(val, str) and val.strip():
            # Delimiter-encoded: rows separated by '#', columns by '~'
            for row in val.split("#"):
                row = row.strip()
                if not row:
                    continue
                cols = row.split("~")
                if cols and cols[0]:
                    cases.append({"cino": cols[0].strip(), "_cols": cols})

    return cases


def _parse_case_history(data: Dict[str, Any], cino: str) -> Dict[str, Any]:
    """
    caseHistoryWebService response → normalised case dict.
    Field names vary across courts; we try the most common variants.
    """
    def _first(*keys: str) -> Any:
        for k in keys:
            if v := data.get(k):
                return v
        return None

    next_date_raw = _first("NextDate", "next_date", "next_hearing", "nxt_date", "next_hearing_date")
    petitioner = _first("petitioner", "petitioners", "appellant", "Petitioner")
    respondent = _first("respondent", "respondents", "Respondent")
    court_name = _first("court_name", "CourtName", "court", "establishment_name")
    case_type = _first("case_type", "casetype", "CaseType", "type")
    reg_no = _first("reg_no", "registration_number", "case_no", "CaseNo", "caseNo")
    status = _first("case_status", "caseStatus", "status_type") or "Pending"

    return {
        "cino": cino,
        "next_hearing_date": _parse_date(next_date_raw),
        "petitioners": _to_list(petitioner),
        "respondents": _to_list(respondent),
        "court_name": str(court_name or ""),
        "case_type": str(case_type or ""),
        "registration_number": str(reg_no or ""),
        "case_status": str(status),
    }


# ── Main service ──────────────────────────────────────────────────────────────

class ECourtsService:
    """
    High-level service: advocate case sync using the eCourts mobile API.

    Identification: bar council enrollment number (e.g. "P/1234/2020") +
    eCourts state code (e.g. "3" for Punjab).
    """

    def __init__(self) -> None:
        self._tokens = _TokenService()
        self._http = _ECourtsHTTPClient(self._tokens)

    async def get_states(self) -> List[Dict[str, Any]]:
        """Fetch the list of states + codes from eCourts. Use to validate state codes."""
        data = await self._http.get("stateWebService.php", {
            "language_flag": "english",
            "bilingual_flag": "0",
        })
        states = data.get("states") or data.get("data") or []
        return states if isinstance(states, list) else []

    async def search_by_bar_code(
        self,
        bar_code: str,
        state_code: str,
        dist_code: str = "0",
    ) -> List[Dict[str, Any]]:
        """
        Search an advocate's cases by bar council enrollment number.
        bar_code format: "P/1234/2020" (state prefix / number / year).
        state_code: eCourts state code (e.g. "3" for Punjab).
        Returns raw case entries (need enrichment via get_case_history).
        """
        data = await self._http.get("searchByAdvocateName.php", {
            "state_code": state_code,
            "dist_code": dist_code,
            "court_code_arr": "",           # empty = state-wide search
            "checkedSearchByRadioValue": "2",  # 2 = bar code mode
            "barstatecode": state_code,
            "barcode": bar_code,
            "pendingDisposed": "Pending",
            "language_flag": "english",
            "bilingual_flag": "0",
        })
        return _parse_advocate_response(data)

    async def search_by_name(
        self,
        advocate_name: str,
        state_code: str,
        dist_code: str = "0",
    ) -> List[Dict[str, Any]]:
        """Fallback: search by advocate name when bar code is unavailable."""
        data = await self._http.get("searchByAdvocateName.php", {
            "state_code": state_code,
            "dist_code": dist_code,
            "court_code_arr": "",
            "checkedSearchByRadioValue": "1",  # 1 = name mode
            "advocateName": advocate_name,
            "pendingDisposed": "Pending",
            "language_flag": "english",
            "bilingual_flag": "0",
        })
        return _parse_advocate_response(data)

    async def get_case_history(
        self, cino: str, state_code: str, dist_code: str = "0"
    ) -> Dict[str, Any]:
        """Full case details (next hearing date, parties, court) for one CNR."""
        data = await self._http.get("caseHistoryWebService.php", {
            "cino": cino,
            "state_code": state_code,
            "dist_code": dist_code,
            "language_flag": "english",
            "bilingual_flag": "0",
        })
        return _parse_case_history(data, cino)

    async def get_case_by_cnr(self, cnr: str) -> Dict[str, Any]:
        """
        Fetch case details by CNR number.  The state_code is inferred from the
        CNR prefix (first two chars are the state abbreviation).

        This is the PRIMARY sync path for Phase 1.  Lawyers enter their CNR
        numbers (visible in the official eCourts app), and we refresh hearing
        dates automatically.  The advocate-by-name search is unreliable in the
        current API version (courtEstWebService returns 0 establishments).
        """
        state_code = _state_code_from_cnr(cnr)
        return await self.get_case_history(cnr, state_code)

    async def refresh_matter_cnr(
        self, cnr: str, firm_id: str, session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Refresh a single matter's hearing date from eCourts.
        Called by the daily Celery job for every matter with cnr_number set.
        Returns the parsed case dict (or raises ECourtsError on failure).
        """
        case = await self.get_case_by_cnr(cnr)

        stmt = sa_select(Matter).where(
            Matter.firm_id == _uuid.UUID(firm_id),
            Matter.cnr_number == cnr,
            Matter.deleted_at.is_(None),
        )
        matter = (await session.execute(stmt)).scalar_one_or_none()
        if matter and case.get("next_hearing_date"):
            matter.next_hearing_date = case["next_hearing_date"]
            matter.case_status = case.get("case_status") or matter.case_status
            matter.ecourts_synced_at = datetime.now(timezone.utc)
            await session.commit()

        return case

    async def sync_firm_hearings(
        self,
        firm_id: str,
        bar_code: str,
        state_code: str,
        session: AsyncSession,
        advocate_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Pull advocate's cases → upsert as Matters keyed by CNR → return summary.

        bar_code: enrollment number e.g. "P/1234/2020"
        state_code: eCourts state code e.g. "3" (Punjab)
        advocate_name: optional fallback if bar_code search returns nothing
        """
        # Search by bar code, fall back to name if needed
        raw_cases = await self.search_by_bar_code(bar_code, state_code)
        if not raw_cases and advocate_name:
            logger.info(f"Bar code search empty, falling back to name search for '{advocate_name}'")
            raw_cases = await self.search_by_name(advocate_name, state_code)

        # Enrich each case with full history (next hearing date, parties, etc.)
        enriched: List[Dict[str, Any]] = []
        for c in raw_cases:
            cino = c.get("cino") or c.get("cinum") or c.get("cnr")
            if not cino:
                continue
            try:
                full = await self.get_case_history(cino, state_code)
                enriched.append(full)
            except ECourtsError as exc:
                logger.debug(f"Skipping {cino} — history fetch failed: {exc}")
                # Keep a minimal entry so the CNR at least appears in the docket
                enriched.append({
                    "cino": cino,
                    "next_hearing_date": None,
                    "petitioners": [],
                    "respondents": [],
                    "court_name": "",
                    "case_type": "",
                    "registration_number": "",
                    "case_status": "Pending",
                })

        now = datetime.now(timezone.utc)
        updated = created = 0
        upcoming: List[Dict[str, Any]] = []

        for c in enriched:
            cino = c["cino"]
            p_list = c.get("petitioners") or []
            r_list = c.get("respondents") or []
            title = (
                f"{', '.join(p_list) or 'Unknown'} vs {', '.join(r_list) or 'Unknown'}"
            )[:480]

            stmt = sa_select(Matter).where(
                Matter.firm_id == _uuid.UUID(firm_id),
                Matter.cnr_number == cino,
                Matter.deleted_at.is_(None),
            )
            matter = (await session.execute(stmt)).scalar_one_or_none()

            if matter:
                if c.get("next_hearing_date"):
                    matter.next_hearing_date = c["next_hearing_date"]
                matter.case_status = c.get("case_status") or matter.case_status
                matter.ecourts_synced_at = now
                updated += 1
            else:
                matter = Matter(
                    firm_id=_uuid.UUID(firm_id),
                    case_name=title,
                    matter_number=c.get("registration_number") or None,
                    court=c.get("court_name") or None,
                    petitioner=", ".join(p_list) or None,
                    respondent=", ".join(r_list) or None,
                    matter_type=c.get("case_type") or None,
                    next_hearing_date=c.get("next_hearing_date"),
                    cnr_number=cino,
                    case_status=c.get("case_status") or "Pending",
                    ecourts_synced_at=now,
                    ecourts_tracked=True,
                    is_active=True,
                )
                session.add(matter)
                created += 1

            hearing = c.get("next_hearing_date")
            if hearing and hearing >= now:
                upcoming.append({
                    "cnr": cino,
                    "case_name": title,
                    "court": c.get("court_name"),
                    "next_hearing_date": hearing.date().isoformat(),
                })

        await session.commit()
        logger.info(
            f"eCourts sync firm={firm_id} bar_code={bar_code}: "
            f"found={len(raw_cases)} enriched={len(enriched)} "
            f"updated={updated} created={created}"
        )
        return {
            "fetched": len(raw_cases),
            "updated": updated,
            "created": created,
            "upcoming": sorted(upcoming, key=lambda x: x["next_hearing_date"]),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_service: Optional[ECourtsService] = None


def get_ecourts_service() -> ECourtsService:
    global _service
    if _service is None:
        _service = ECourtsService()
    return _service
