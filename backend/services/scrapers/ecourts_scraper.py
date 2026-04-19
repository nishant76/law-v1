"""
eCourts judgment portal scraper — judgments.ecourts.gov.in
Data sourced from official Government of India eCourts platform.
All judgment text is public domain under Section 52(1)(q) of the Copyright Act 1957.
No commercial data is scraped.

Portal:   https://judgments.ecourts.gov.in
Targets:  Punjab and Haryana High Court judgments, last 2 years
Search:   POST to /pdfsearch/ with state/court/date filters
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import re

from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ECourtsScraper(BaseScraper):
    """
    Scraper for Punjab and Haryana High Court judgments via judgments.ecourts.gov.in.

    The eCourts portal serves judgments from all Indian courts.  P&H HC judgments
    are available under state_code=3 (Punjab and Haryana).  The portal uses a
    form-POST search returning an HTML results table with PDF links.
    """

    BASE_URL = "https://judgments.ecourts.gov.in"
    SOURCE_NAME = "eCourts"
    COURT_NAME = "Punjab and Haryana High Court"
    RATE_LIMIT_DELAY = 3.0

    # eCourts uses state/court codes in the search form
    STATE_CODE = "3"       # Punjab and Haryana
    COURT_CODE = "1"       # High Court
    DIST_CODE = "0"        # All districts

    # PDF link pattern returned in search results
    _PDF_PATTERN = re.compile(r'href=["\']([^"\']*\.pdf)["\']', re.IGNORECASE)
    # Judgment page link pattern
    _JDG_PATTERN = re.compile(
        r'href=["\']([^"\']*(?:judgement|judgment|view_judgment)[^"\']*)["\']',
        re.IGNORECASE,
    )

    # Search endpoint — form POST
    _SEARCH_PATH = "/pdfsearch/"
    # Alternative path if the above returns 404
    _SEARCH_PATH_ALT = "/pdfsearch/index.php"

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self._search_url = f"{self.BASE_URL}{self._SEARCH_PATH}"
        # Date range: last 2 years
        self._date_to = datetime.now(timezone.utc)
        self._date_from = self._date_to - timedelta(days=730)

    async def get_judgment_urls(self, limit: int = 5000) -> List[str]:
        """
        POST search queries to the eCourts judgment portal and collect result URLs.
        Iterates through pages until the limit is reached or no more results.
        """
        urls: List[str] = []
        page_no = 1

        while len(urls) < limit:
            logger.info(
                f"eCourts: Fetching search results page {page_no} "
                f"({len(urls)}/{limit} URLs so far)"
            )
            payload = self._build_search_payload(page_no)
            response = await self._post_search(payload)

            if not response:
                # Try alternate path once
                if page_no == 1:
                    self._search_url = f"{self.BASE_URL}{self._SEARCH_PATH_ALT}"
                    response = await self._post_search(payload)
                if not response:
                    logger.warning("eCourts: Search endpoint unreachable, stopping")
                    break

            page_urls = self._extract_judgment_urls(response.text)
            if not page_urls:
                logger.info(f"eCourts: No more results at page {page_no}")
                break

            before = len(urls)
            for u in page_urls:
                if u not in urls:
                    urls.append(u)
            if len(urls) == before:
                break  # Duplicate page

            page_no += 1

        logger.info(f"eCourts: Collected {len(urls)} judgment URLs")
        return urls[:limit]

    def _build_search_payload(self, page_no: int) -> dict:
        """Build POST form payload for eCourts search."""
        return {
            "state_code": self.STATE_CODE,
            "dist_code": self.DIST_CODE,
            "court_code": self.COURT_CODE,
            "from_date": self._date_from.strftime("%d-%m-%Y"),
            "to_date": self._date_to.strftime("%d-%m-%Y"),
            "free_text": "",
            "pet_name": "",
            "res_name": "",
            "judge_name": "",
            "act": "",
            "section": "",
            "appFlag": "web",
            "pageNo": str(page_no),
        }

    async def _post_search(self, payload: dict):
        """POST a search to the eCourts portal and return the response."""
        try:
            await __import__("asyncio").sleep(self.RATE_LIMIT_DELAY)
            response = await self.http_client.post(
                self._search_url,
                data=payload,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": self.BASE_URL,
                },
            )
            response.raise_for_status()
            return response
        except Exception as e:
            error_msg = f"eCourts: Search POST failed: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return None

    def _extract_judgment_urls(self, html: str) -> List[str]:
        """Extract individual judgment/PDF URLs from a search results page.

        The eCourts portal requires CAPTCHA to complete a search.  When a POST
        without a valid CAPTCHA token is submitted, the portal returns the home
        page (HTTP 200) rather than a results page.  We detect this by checking
        for the CAPTCHA input field in the response and log a warning so the
        operator knows why zero results are returned.
        """
        # Detect CAPTCHA gate — portal returned the home/search form
        if 'id="captcha"' in html or 'securimage' in html:
            logger.warning(
                "eCourts: Search returned CAPTCHA challenge — automated scraping "
                "is blocked by judgments.ecourts.gov.in.  "
                "The portal requires a human-solved CAPTCHA to retrieve results.  "
                "P&H HC judgments are being collected via highcourtchd.gov.in instead."
            )
            return []

        urls = []
        try:
            # Priority 1: direct PDF links
            for m in self._PDF_PATTERN.finditer(html):
                href = m.group(1)
                full_url = href if href.startswith("http") else f"{self.BASE_URL}/{href.lstrip('/')}"
                if full_url not in urls:
                    urls.append(full_url)

            # Priority 2: HTML judgment view links
            if not urls:
                for m in self._JDG_PATTERN.finditer(html):
                    href = m.group(1)
                    full_url = href if href.startswith("http") else f"{self.BASE_URL}/{href.lstrip('/')}"
                    if full_url not in urls:
                        urls.append(full_url)
        except Exception as e:
            logger.error(f"eCourts: Error extracting judgment URLs: {e}")
        return urls

    async def parse_judgment(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse a judgment page or PDF URL from eCourts."""
        try:
            if url.lower().endswith(".pdf"):
                return self._parse_from_pdf_url(url)

            response = await self.rate_limited_request(url)
            if not response:
                return None

            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type.lower():
                return self._parse_from_pdf_url(url)

            html = response.text
            case_name = self._extract_case_name(html)
            if not case_name:
                logger.debug(f"eCourts: Could not extract case name from {url}")
                return None

            judgment_date = self._extract_judgment_date(html)
            year = self._extract_year(judgment_date, url)

            return {
                "case_name": case_name,
                "petitioner": self._extract_party(html, "petitioner"),
                "respondent": self._extract_party(html, "respondent"),
                "judgment_date": judgment_date,
                "judge_name": self._extract_judge_names(html),
                "year": year,
                "court": self.COURT_NAME,
                "official_source": self.SOURCE_NAME,
                "source_url": url,
                "source_doc_id": self._extract_source_doc_id(url),
                "judgment_text": self._extract_judgment_text(html),
                "matter_type": self._extract_matter_type(html),
                "primary_citation": self._extract_citation(html),
                "subject_tags": self._extract_subject_tags(html),
            }

        except Exception as e:
            logger.error(f"eCourts: Error parsing judgment from {url}: {e}")
            return None

    def _parse_from_pdf_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Derive metadata from a PDF URL when no HTML wrapper exists."""
        try:
            filename = url.rsplit("/", 1)[-1].replace(".pdf", "")
            year = self._extract_year(None, url)
            case_name = filename.replace("_", " ").replace("-", " ")[:200] or f"eCourts Judgment {year}"
            return {
                "case_name": case_name,
                "petitioner": None,
                "respondent": None,
                "judgment_date": None,
                "judge_name": None,
                "year": year,
                "court": self.COURT_NAME,
                "official_source": self.SOURCE_NAME,
                "source_url": url,
                "source_doc_id": self._extract_source_doc_id(url),
                "judgment_text": None,
                "matter_type": "general",
                "primary_citation": None,
                "subject_tags": None,
            }
        except Exception as e:
            logger.error(f"eCourts: Error parsing PDF URL {url}: {e}")
            return None

    # ------------------------------------------------------------------ #
    #  Extraction helpers                                                  #
    # ------------------------------------------------------------------ #

    def _extract_case_name(self, html: str) -> Optional[str]:
        patterns = [
            r'<td[^>]*>[Cc]ase\s+[Nn]ame[^<]*</td>\s*<td[^>]*>([^<]+)</td>',
            r'Case\s+Name["\']?\s*[:\-]\s*([^<\n]{10,400})',
            r'<h[1-3][^>]*>([^<]{10,400})</h[1-3]>',
            r'<title>([^<|—-]{10,400})</title>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                name = matches[0].strip()
                if 10 < len(name) < 500:
                    return name
        return None

    def _extract_party(self, html: str, role: str) -> Optional[str]:
        patterns = [
            rf'{role}["\']?\s*[:\-]\s*["\']?([^"\'<\n]{{3,300}})',
            rf'<td[^>]*>{role}</td>\s*<td[^>]*>([^<]+)</td>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        return None

    def _extract_judgment_date(self, html: str) -> Optional[datetime]:
        patterns = [
            r'Date\s+of\s+[Jj]udgment["\']?\s*[:\-]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'[Jj]udgment\s+[Dd]ate["\']?\s*[:\-]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'Decided\s+on["\']?\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html)
            if matches:
                for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d']:
                    try:
                        return datetime.strptime(matches[0], fmt)
                    except ValueError:
                        continue
        return None

    def _extract_judge_names(self, html: str) -> Optional[str]:
        patterns = [
            r'<b>([A-Za-z\s.,]+),?\s+J\.</b>',
            r'[Jj]udge[s]?["\']?\s*[:\-]\s*([^<\n]+)',
            r'Coram["\']?\s*[:\-]\s*([^<\n]+)',
        ]
        names = []
        for pattern in patterns:
            names.extend(re.findall(pattern, html))
        return "; ".join(n.strip() for n in names[:3]) if names else None

    def _extract_citation(self, html: str) -> Optional[str]:
        patterns = [
            r'\(\d{4}\)\s+\d+\s+[A-Z]+\s+\d+',
            r'Citation["\']?\s*[:\-]\s*([^\n<]{5,100})',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html)
            if matches:
                c = matches[0].strip()
                if len(c) < 100:
                    return c
        return None

    def _extract_judgment_text(self, html: str) -> Optional[str]:
        patterns = [
            r'<div[^>]*class="[^"]*judgment[^"]*"[^>]*>([\s\S]*?)</div>',
            r'<div[^>]*id="[^"]*content[^"]*"[^>]*>([\s\S]*?)</div>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            if matches:
                text = re.sub(r'<[^>]+>', ' ', matches[0])
                text = re.sub(r'\s+', ' ', text).strip()[:5000]
                if len(text) > 100:
                    return text
        return None

    def _extract_matter_type(self, text: str) -> str:
        keywords = {
            "criminal": "criminal", "civil": "civil", "writ": "civil",
            "commercial": "commercial", "labour": "labour",
            "matrimonial": "matrimonial", "consumer": "consumer",
            "cheque": "criminal", "tax": "tax",
        }
        tl = text.lower()
        for kw, mt in keywords.items():
            if kw in tl:
                return mt
        return "general"

    def _extract_year(self, judgment_date: Optional[datetime], url: str) -> int:
        if judgment_date:
            return judgment_date.year
        year_matches = re.findall(r'(\d{4})', url)
        for y in year_matches:
            year = int(y)
            if 1950 <= year <= datetime.now(timezone.utc).year:
                return year
        return datetime.now(timezone.utc).year

    def _extract_source_doc_id(self, url: str) -> Optional[str]:
        m = re.search(r'[?&](?:id|doc_id|judgment_id)=([^&]+)', url)
        if m:
            return m.group(1)
        # From filename: /path/12345.pdf → "12345"
        m = re.search(r'/(\d+)\.pdf$', url, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    def _extract_subject_tags(self, html: str) -> Optional[str]:
        tag_map = {
            "criminal": "criminal", "civil": "civil", "writ": "writ",
            "bail": "bail", "cheque": "cheque_bounce", "section 138": "cheque_bounce",
            "labour": "labour", "matrimonial": "matrimonial",
            "property": "property", "consumer": "consumer",
            "commercial": "commercial", "tax": "tax",
        }
        hl = html.lower()
        seen: set = set()
        tags = []
        for kw, tag in tag_map.items():
            if kw in hl and tag not in seen:
                tags.append(tag)
                seen.add(tag)
        return json.dumps(tags) if tags else None
