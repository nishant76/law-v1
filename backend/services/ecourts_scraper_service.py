"""
ecourtsindia.com scraper — discovers a lawyer's CNR numbers at signup.

Uses Playwright SYNC API running in a thread-pool executor so it works
on Windows where uvicorn's SelectorEventLoop cannot spawn subprocesses
(asyncio.create_subprocess_exec raises NotImplementedError there).

Flow:
  1. search_lawyers(name)         → list of matching lawyer profiles
  2. get_cases_for_lawyer(slug)   → all cases + CNRs for one profile
  3. Lawyer confirms their cases on the frontend
  4. import_cnrs saved to matters table
"""
import asyncio
import os
import re
from typing import Any, Dict, List, Optional

from backend.core.logger import get_logger

logger = get_logger(__name__)

_SITE = "https://ecourtsindia.com"
_CNR_RE = re.compile(r'/cnr/([A-Z]{2}[A-Z0-9]{2}\d{6,})', re.IGNORECASE)
_SLUG_RE = re.compile(r'/lawyer/([a-z0-9\-\.]+)', re.IGNORECASE)

ECOURTS_INDIA_STATE_CODES: Dict[str, str] = {
    "punjab": "PB",
    "haryana": "HR",
    "chandigarh": "CH",
    "delhi": "DL",
    "himachal_pradesh": "HP",
    "uttar_pradesh": "UP",
    "maharashtra": "MH",
    "karnataka": "KA",
    "tamil_nadu": "TN",
    "rajasthan": "RJ",
}


class EcourtsDiscoveryError(Exception):
    """Raised on scraping errors."""


class EcourtsDiscoveryNotConfigured(Exception):
    """Raised when Playwright is not installed."""


def _ensure_playwright() -> None:
    try:
        import playwright  # noqa: F401
    except ImportError:
        raise EcourtsDiscoveryNotConfigured(
            "playwright is not installed. Run: pip install playwright && python -m playwright install chromium"
        )


# ── Sync browser helpers ──────────────────────────────────────────────────────

def _new_page_sync():
    """
    Launch a Playwright SYNC browser page that bypasses Cloudflare.

    Uses real Chrome (channel='chrome') which presents Chrome's TLS fingerprint
    rather than Chromium's — Cloudflare accepts Chrome but blocks headless Chromium.
    Falls back to bundled Chromium if Chrome is not installed.

    IMPORTANT: uses playwright.sync_api, not async_api. This avoids the
    asyncio.create_subprocess_exec NotImplementedError on Windows SelectorEventLoop.
    Callers must run this via asyncio.to_thread() so the blocking I/O doesn't
    hold up the FastAPI event loop.
    """
    from playwright.sync_api import sync_playwright

    headless = os.getenv("ECOURTS_HEADLESS", "0") == "1"

    p = sync_playwright().start()
    try:
        browser = p.chromium.launch(
            channel="chrome",
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--window-position=-10000,-10000",
            ],
        )
    except Exception:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )

    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-US",
    )
    page = context.new_page()
    page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    return p, browser, context, page


# ── Sync implementations (run in thread pool) ─────────────────────────────────

def _nav_with_retry(page, url: str, retries: int = 3, timeout: int = 60_000) -> None:
    """Navigate to url, retrying on timeout (Cloudflare occasionally slow-blocks)."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            return
        except Exception as e:
            last_err = e
            logger.warning(f"  nav attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                page.wait_for_timeout(3000 * attempt)  # 3s, 6s back-off
    raise last_err


def _search_lawyers_sync(name: str) -> List[Dict[str, Any]]:
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    from bs4 import BeautifulSoup

    # ecourtsindia.com search index is case-sensitive and normalised to uppercase.
    # Sending mixed-case returns 0 results even when the advocate exists.
    name_upper = name.strip().upper()
    url = f"{_SITE}/lawyer?adv={name_upper.replace(' ', '+')}"
    logger.info(f"eCourts scraper: searching lawyers name={name!r} (sent as {name_upper!r})")

    p, browser, context, page = _new_page_sync()
    try:
        _nav_with_retry(page, url)
        page.wait_for_timeout(1500)
        content = page.content()
    finally:
        browser.close()
        p.stop()

    soup = BeautifulSoup(content, "lxml")
    results: List[Dict[str, Any]] = []
    for a in soup.find_all("a", href=_SLUG_RE):
        href = a.get("href", "")
        m = _SLUG_RE.search(href)
        if not m:
            continue
        slug = m.group(1)
        text = a.get_text(separator="\n").strip()
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        display_name = lines[1] if len(lines) > 1 else lines[0] if lines else slug
        court = lines[2] if len(lines) > 2 else ""
        results.append({
            "display_name": display_name,
            "court": court,
            "slug": slug,
            "profile_url": f"{_SITE}/lawyer/{slug}",
        })

    logger.info(f"eCourts scraper: found {len(results)} lawyers for {name!r}")
    return results


def _get_cases_sync(slug: str, max_pages: int = 10) -> Dict[str, Any]:
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    from bs4 import BeautifulSoup

    profile_url = f"{_SITE}/lawyer/{slug}"
    logger.info(f"eCourts scraper: fetching cases slug={slug!r}")

    cases: List[Dict[str, Any]] = []
    pages_fetched = 0

    p, browser, context, page = _new_page_sync()
    try:
        current_url = profile_url
        while pages_fetched < max_pages:
            _nav_with_retry(page, current_url)
            page.wait_for_timeout(1500)
            content = page.content()
            pages_fetched += 1

            soup = BeautifulSoup(content, "lxml")
            new_on_page = 0
            for a in soup.find_all("a", href=_CNR_RE):
                href = a.get("href", "")
                m = _CNR_RE.search(href)
                if not m:
                    continue
                cnr = m.group(1).upper()
                text = a.get_text(separator="\n").strip()
                cases.append(_parse_case_card(text, cnr))
                new_on_page += 1

            logger.info(f"  page {pages_fetched}: {new_on_page} cases at {current_url}")

            next_link = soup.find("a", string=re.compile(r"^Next$", re.IGNORECASE))
            if not next_link:
                next_link = soup.find("a", attrs={"aria-label": re.compile(r"next", re.IGNORECASE)})
            if not next_link or not next_link.get("href"):
                logger.info(f"  no Next link on page {pages_fetched} — done")
                break
            next_href = next_link["href"]
            current_url = next_href if next_href.startswith("http") else f"{_SITE}{next_href}"
    finally:
        browser.close()
        p.stop()

    seen: set = set()
    unique = []
    for c in cases:
        if c["cnr"] not in seen:
            seen.add(c["cnr"])
            unique.append(c)

    logger.info(f"eCourts scraper: {len(unique)} unique cases for slug={slug!r} over {pages_fetched} pages")
    return {"cases": unique, "total": len(unique), "pages_fetched": pages_fetched}


# ── Court-code-aware case fetching ─────────────────────────────────────────────
# ecourtsindia.com profiles aggregate ALL advocates with the same name nationally.
# The ?cc=HRPK02 query parameter filters cases to a specific court establishment.
# CNR prefix → court code: HRPK020008152025 → cc=HRPK02 (HR+PK+02).
# City → CNR district prefix mapping for Punjab/Haryana courts.

CITY_TO_DISTRICT_PREFIX: Dict[str, str] = {
    # Haryana
    "panchkula": "HRPK",
    "ambala": "HRAM",
    "gurugram": "HRGR",
    "gurgaon": "HRGR",
    "faridabad": "HRFD",
    "hisar": "HRHS",
    "rohtak": "HRRT",
    "sonepat": "HRSP",
    "panipat": "HRPT",
    "karnal": "HRKR",
    "kurukshetra": "HRKK",
    "jhajjar": "HRJJ",
    "bhiwani": "HRBW",
    "sirsa": "HRSI",
    "rewari": "HRRW",
    "yamunanagar": "HRYN",
    "fatehabad": "HRFT",
    "kaithal": "HRKT",
    "narnaul": "HRNN",
    # Punjab
    "ludhiana": "PBLD",
    "amritsar": "PBAR",
    "jalandhar": "PBJL",
    "patiala": "PBPT",
    "mohali": "PBML",
    "sas nagar": "PBML",
    "bathinda": "PBBT",
    "hoshiarpur": "PBHP",
    "gurdaspur": "PBGD",
    "ropar": "PBRP",
    "rupnagar": "PBRP",
    "sangrur": "PBSG",
    "firozpur": "PBFZ",
    "moga": "PBMG",
    "kapurthala": "PBKP",
    "fatehgarh sahib": "PBFG",
    "nawanshahr": "PBNW",
    "tarn taran": "PBTT",
    # Chandigarh
    "chandigarh": "CHCH",
}

_CC_RE = re.compile(r'[?&]cc=([A-Z0-9]+)', re.IGNORECASE)


def _get_court_codes_sync(slug: str) -> List[Dict[str, Any]]:
    """
    Fetch a lawyer profile page and extract all available court code filter links.
    Returns list of {cc, court_name, count} for each court the advocate has cases in.
    Used to identify which courts to fetch cases from, filtered by the lawyer's city.
    """
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    from bs4 import BeautifulSoup

    url = f"{_SITE}/lawyer/{slug}"
    logger.info(f"eCourts scraper: fetching court codes for slug={slug!r}")

    p, browser, context, page = _new_page_sync()
    try:
        _nav_with_retry(page, url)
        page.wait_for_timeout(2000)
        content = page.content()
    finally:
        browser.close()
        p.stop()

    soup = BeautifulSoup(content, "lxml")
    courts: List[Dict[str, Any]] = []
    seen_cc: set = set()

    for a in soup.find_all("a", href=_CC_RE):
        href = a.get("href", "")
        m = _CC_RE.search(href)
        if not m:
            continue
        cc = m.group(1).upper()
        if cc in seen_cc:
            continue
        seen_cc.add(cc)
        txt = a.get_text(strip=True)
        # text is typically "CourtName\nCount" or "CourtNameCount"
        import re as _re
        count_match = _re.search(r'(\d+)\s*$', txt)
        count = int(count_match.group(1)) if count_match else 0
        court_name = txt[:count_match.start()].strip() if count_match else txt
        courts.append({"cc": cc, "court_name": court_name, "count": count})

    logger.info(f"eCourts scraper: found {len(courts)} court codes for slug={slug!r}")
    return courts


def _get_cases_by_court_code_sync(slug: str, cc: str, max_pages: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch all cases for a specific court code filter (e.g. cc=HRPK02).
    Paginates through all pages using ?cc=CC&pg=N.
    """
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    from bs4 import BeautifulSoup

    _PG_RE = re.compile(r'[?&]pg=(\d+)')
    cases: List[Dict[str, Any]] = []
    pages_fetched = 0

    p, browser, context, page = _new_page_sync()
    try:
        current_url = f"{_SITE}/lawyer/{slug}?cc={cc}"
        while pages_fetched < max_pages:
            _nav_with_retry(page, current_url)
            page.wait_for_timeout(1500)
            content = page.content()
            pages_fetched += 1

            soup = BeautifulSoup(content, "lxml")
            new_on_page = 0
            for a in soup.find_all("a", href=_CNR_RE):
                href = a.get("href", "")
                m = _CNR_RE.search(href)
                if not m:
                    continue
                cnr = m.group(1).upper()
                text = a.get_text(separator="\n").strip()
                cases.append(_parse_case_card(text, cnr))
                new_on_page += 1

            logger.info(f"  cc={cc} page {pages_fetched}: {new_on_page} cases")

            # Find Next link: /lawyer/slug?cc=CC&pg=N+1
            next_link = soup.find("a", string=re.compile(r"^Next$", re.IGNORECASE))
            if not next_link:
                next_link = soup.find("a", attrs={"aria-label": re.compile(r"next", re.IGNORECASE)})
            if next_link and next_link.get("href"):
                next_href = next_link["href"]
                current_url = next_href if next_href.startswith("http") else f"{_SITE}{next_href}"
            else:
                break
    finally:
        browser.close()
        p.stop()

    return cases


def _get_cases_by_city_sync(slug: str, city: str, max_pages: int = 50) -> Dict[str, Any]:
    """
    Get all cases for an advocate filtered by city.
    1. Fetch profile court codes
    2. Keep only court codes whose prefix matches the city's district code
    3. Fetch all cases from matching courts
    Returns {cases, total, courts_searched, court_codes}
    """
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    city_lower = city.strip().lower()
    district_prefix = CITY_TO_DISTRICT_PREFIX.get(city_lower)

    # Get all court codes from profile
    all_courts = _get_court_codes_sync(slug)

    # Filter by city prefix if known; otherwise use all courts
    if district_prefix:
        matching_courts = [c for c in all_courts if c["cc"].startswith(district_prefix)]
        logger.info(f"eCourts: city={city!r} prefix={district_prefix} matched {len(matching_courts)}/{len(all_courts)} courts")
    else:
        matching_courts = all_courts
        logger.info(f"eCourts: no prefix for city={city!r}, using all {len(all_courts)} courts")

    # Fetch cases from each matching court
    cases: List[Dict[str, Any]] = []
    seen: set = set()

    p, browser, context, page = _new_page_sync()
    try:
        for court in matching_courts:
            cc = court["cc"]
            page_num = 1
            current_url = f"{_SITE}/lawyer/{slug}?cc={cc}"

            while page_num <= max_pages:
                from bs4 import BeautifulSoup
                _nav_with_retry(page, current_url)
                page.wait_for_timeout(1500)
                content = page.content()
                soup = BeautifulSoup(content, "lxml")

                new_on_page = 0
                for a in soup.find_all("a", href=_CNR_RE):
                    href = a.get("href", "")
                    m = _CNR_RE.search(href)
                    if not m:
                        continue
                    cnr = m.group(1).upper()
                    if cnr not in seen:
                        seen.add(cnr)
                        text = a.get_text(separator="\n").strip()
                        cases.append(_parse_case_card(text, cnr))
                        new_on_page += 1

                logger.info(f"  cc={cc} page {page_num}: {new_on_page} new cases")
                page_num += 1

                next_link = soup.find("a", string=re.compile(r"^Next$", re.IGNORECASE))
                if not next_link:
                    next_link = soup.find("a", attrs={"aria-label": re.compile(r"next", re.IGNORECASE)})
                if next_link and next_link.get("href"):
                    next_href = next_link["href"]
                    current_url = next_href if next_href.startswith("http") else f"{_SITE}{next_href}"
                else:
                    break
    finally:
        browser.close()
        p.stop()

    logger.info(f"eCourts: {len(cases)} total cases for slug={slug!r} city={city!r}")
    return {
        "cases": cases,
        "total": len(cases),
        "courts_searched": [c["cc"] for c in matching_courts],
        "court_codes": matching_courts,
        "district_prefix": district_prefix,
    }


# ── Public async API (wraps sync in thread pool) ──────────────────────────────

async def search_lawyers(name: str) -> List[Dict[str, Any]]:
    """Search ecourtsindia.com for advocates matching `name`."""
    _ensure_playwright()
    try:
        return await asyncio.to_thread(_search_lawyers_sync, name)
    except EcourtsDiscoveryNotConfigured:
        raise
    except Exception as exc:
        logger.error(f"eCourts scraper: search_lawyers failed: {exc}")
        raise EcourtsDiscoveryError(f"Browser automation failed: {exc}") from exc


async def get_court_codes(slug: str) -> List[Dict[str, Any]]:
    """Return all court code filters available on an advocate's profile page."""
    _ensure_playwright()
    try:
        return await asyncio.to_thread(_get_court_codes_sync, slug)
    except EcourtsDiscoveryNotConfigured:
        raise
    except Exception as exc:
        logger.error(f"eCourts scraper: get_court_codes failed: {exc}")
        raise EcourtsDiscoveryError(f"Browser automation failed: {exc}") from exc


async def get_cases_by_city(slug: str, city: str, max_pages: int = 50) -> Dict[str, Any]:
    """
    Get all cases for an advocate filtered by their practice city.
    Uses ?cc=PREFIX court code filters so only cases from that district are returned.
    This avoids fetching 14,000+ cases from a common-name profile.
    """
    _ensure_playwright()
    try:
        return await asyncio.to_thread(_get_cases_by_city_sync, slug, city, max_pages)
    except EcourtsDiscoveryNotConfigured:
        raise
    except Exception as exc:
        logger.error(f"eCourts scraper: get_cases_by_city failed: {exc}")
        raise EcourtsDiscoveryError(f"Browser automation failed: {exc}") from exc


async def get_cases_for_lawyer(slug: str, max_pages: int = 10) -> Dict[str, Any]:
    """Scrape all cases for a lawyer profile slug (no city filter)."""
    _ensure_playwright()
    try:
        return await asyncio.to_thread(_get_cases_sync, slug, max_pages)
    except EcourtsDiscoveryNotConfigured:
        raise
    except Exception as exc:
        logger.error(f"eCourts scraper: get_cases_for_lawyer failed: {exc}")
        raise EcourtsDiscoveryError(f"Browser automation failed: {exc}") from exc


# ── Case card parser ──────────────────────────────────────────────────────────

def _parse_case_card(text: str, cnr: str) -> Dict[str, Any]:
    """
    Parse a case card's text into structured fields.
    ecourtsindia.com renders field labels and colons as separate DOM nodes so
    get_text produces bare ':' lines — we filter those before label lookups.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and ln.strip() != ":"]

    def _after(label: str) -> str:
        label_lower = label.lower()
        for i, ln in enumerate(lines):
            if ln.lower().startswith(label_lower) and i + 1 < len(lines):
                val = lines[i + 1]
                return val if val != "-" else ""
        return ""

    case_name = lines[0] if lines else ""
    vs_match = re.split(r"\s+[Vv][Ss]?\.?\s+", case_name, maxsplit=1)
    petitioner = vs_match[0].strip() if vs_match else ""
    respondent = vs_match[1].strip() if len(vs_match) > 1 else ""

    return {
        "cnr": cnr,
        "case_name": case_name,
        "petitioner": petitioner,
        "respondent": respondent,
        "pet_adv": _after("Petitioner Adv"),
        "res_adv": _after("Respondent Adv"),
        "court": _after("Court"),
        "case_type": _after("Case Type"),
        "status": _after("Case Status"),
    }


# ── Legacy shim ───────────────────────────────────────────────────────────────

async def get_cnrs_by_advocate(
    name: str,
    state_code: Optional[str] = None,
    status: str = "Pending",
) -> Dict[str, Any]:
    profiles = await search_lawyers(name)
    if not profiles:
        return {"cnrs": [], "total": 0, "raw_count": 0}

    all_cnrs: List[str] = []
    for profile in profiles:
        result = await get_cases_for_lawyer(profile["slug"])
        for case in result["cases"]:
            cnr = case["cnr"]
            if state_code and not cnr.upper().startswith(state_code.upper()):
                continue
            all_cnrs.append(cnr)

    unique = list(dict.fromkeys(all_cnrs))
    return {"cnrs": unique, "total": len(unique), "raw_count": len(all_cnrs)}
