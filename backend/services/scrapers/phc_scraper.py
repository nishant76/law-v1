"""
P&H HC (Punjab and Haryana High Court) scraper from highcourtchd.gov.in
Data sourced from official Government of India High Court website.
All judgment text is public domain under Section 52(1)(q) of the Copyright Act 1957.
No commercial data is scraped.

Judgment PDFs:    https://highcourtchd.gov.in/lts_judgments/[case].pdf
Listing pages:    https://highcourtchd.gov.in/sub_pages/snap_today_judgement.php
                  https://highcourtchd.gov.in/index.php?linkid=218  (judgment archive)
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from urllib.parse import unquote
import re

from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class PHCScraper(BaseScraper):
    """Scraper for Punjab and Haryana High Court judgments from highcourtchd.gov.in"""

    BASE_URL = "https://highcourtchd.gov.in"
    SOURCE_NAME = "P&H HC"
    COURT_NAME = "Punjab and Haryana High Court"
    RATE_LIMIT_DELAY = 3.0

    # Judgment PDFs served from the HC's DigitalOcean CDN
    # Pattern: https://ilrhcchd.sgp1.digitaloceanspaces.com/[id]/[CaseType]-No.-[num]-of-[year]-[parties].pdf
    _CDN_HOST = "ilrhcchd.sgp1.digitaloceanspaces.com"
    _CDN_PDF_PATTERN = re.compile(
        r'https?://ilrhcchd\.sgp1\.digitaloceanspaces\.com/\d+/[^"\'<\s]+\.pdf',
        re.IGNORECASE,
    )
    # PDFs under /lts_judgments/ on the main site
    _LTS_PDF_PATTERN = re.compile(
        r'/lts_judgments/([^"\'<\s]+\.pdf)', re.IGNORECASE
    )
    # Case-type prefix pattern used in CDN filenames: CWP, CRA, CRR, RSA, FAO, etc.
    _CASE_FILENAME_RE = re.compile(
        r'(?P<case_type>[A-Z]{2,6})-(?:No\.-)?(?P<case_no>\d+)-(?:OF-|of-)?(?P<year>\d{4})-(?P<parties>.+)\.pdf$',
        re.IGNORECASE,
    )

    # Candidate listing pages — tried in order until one yields PDF links
    # /index.php?linkid=218 is the only confirmed working path (returns CDN PDF links)
    # /sub_pages/snap_today_judgement.php — 404 as of April 2026
    # /lts_judgments/ — directory listing returns 403 (direct file URLs still work)
    # /judgments.php — 404 as of April 2026
    _LISTING_PATHS = [
        "/index.php?linkid=218",        # Confirmed 200 — CDN judgment links
    ]

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_judgment_urls(self, limit: int = 5000) -> List[str]:
        """
        Find judgment PDF URLs from P&H HC listing pages.
        Tries each candidate listing path until one returns results.
        """
        urls: List[str] = []

        for path in self._LISTING_PATHS:
            if len(urls) >= limit:
                break

            listing_url = f"{self.BASE_URL}{path}"
            logger.info(f"P&H HC: Trying listing page {listing_url}")
            response = await self.rate_limited_request(listing_url)
            if not response:
                continue

            page_urls = self._extract_pdf_urls(response.text)
            if not page_urls:
                logger.warning(f"P&H HC: No PDF links found at {listing_url}")
                continue

            logger.info(f"P&H HC: Found {len(page_urls)} PDF links at {listing_url}")
            for u in page_urls:
                if u not in urls:
                    urls.append(u)

            # If this listing path worked, try paginating it
            if page_urls and "?" not in path:
                page = 2
                max_pages = max(1, (limit // max(len(page_urls), 1)) + 1)
                while len(urls) < limit and page <= max_pages:
                    paginated = f"{listing_url}?page={page}"
                    r = await self.rate_limited_request(paginated)
                    if not r:
                        break
                    more = self._extract_pdf_urls(r.text)
                    if not more:
                        break
                    before = len(urls)
                    for u in more:
                        if u not in urls:
                            urls.append(u)
                    if len(urls) == before:
                        break
                    page += 1

        logger.info(f"P&H HC: Collected {len(urls)} judgment URLs total")
        return urls[:limit]

    def _extract_pdf_urls(self, html: str) -> List[str]:
        """
        Extract judgment PDF URLs from a listing page.
        Accepts only:
          1. CDN PDFs from ilrhcchd.sgp1.digitaloceanspaces.com (primary HC judgment store)
          2. /lts_judgments/ PDFs on highcourtchd.gov.in
        All other PDFs on the main site are administrative documents, not judgments.
        """
        urls = []
        try:
            # Priority 1: CDN judgment PDFs (confirmed pattern for real HC judgments)
            for m in self._CDN_PDF_PATTERN.finditer(html):
                full_url = m.group(0)
                if full_url not in urls:
                    urls.append(full_url)

            # Priority 2: /lts_judgments/ PDFs on main site
            for m in self._LTS_PDF_PATTERN.finditer(html):
                full_url = f"{self.BASE_URL}/lts_judgments/{m.group(1)}"
                if full_url not in urls:
                    urls.append(full_url)
        except Exception as e:
            logger.error(f"P&H HC: Error extracting PDF URLs: {e}")
        return urls

    async def parse_judgment(self, url: str) -> Optional[Dict[str, Any]]:
        """
        For PDF URLs, derive metadata from URL and filename.
        For HTML pages, parse the HTML for structured data.
        """
        try:
            if url.lower().endswith(".pdf"):
                return self._parse_from_pdf_url(url)

            response = await self.rate_limited_request(url)
            if not response:
                return None

            html = response.text
            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type.lower():
                return self._parse_from_pdf_url(url)

            case_name = self._extract_case_name(html)
            if not case_name:
                logger.debug(f"P&H HC: Could not extract case name from {url}")
                return None

            petitioner = self._extract_petitioner(html)
            respondent = self._extract_respondent(html)
            judgment_date = self._extract_judgment_date(html)
            judge_names = self._extract_judge_names(html)
            citation = self._extract_citation(html)
            judgment_text = self._extract_judgment_text(html)
            matter_type = self._extract_matter_type(html)
            year = self._extract_year(judgment_date, url)

            return {
                "case_name": case_name,
                "petitioner": petitioner,
                "respondent": respondent,
                "judgment_date": judgment_date,
                "judge_name": judge_names,
                "year": year,
                "court": self.COURT_NAME,
                "official_source": self.SOURCE_NAME,
                "source_url": url,
                "source_doc_id": self._extract_source_doc_id(url),
                "judgment_text": judgment_text,
                "matter_type": matter_type,
                "primary_citation": citation,
                "subject_tags": self._extract_subject_tags(html),
            }

        except Exception as e:
            logger.error(f"P&H HC: Error parsing judgment from {url}: {e}")
            return None

    def _parse_from_pdf_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Derive metadata from a PDF URL.
        CDN format: [CaseType]-No.-[num]-of-[year]-[PETITIONER-VERSUS-RESPONDENT].pdf
        e.g. CWP-No.-39633-OF-2025-(MANIK-KHURANA-VERSUS-THE-CAT-AND-OTHERS).pdf
        """
        try:
            filename = unquote(url.rsplit("/", 1)[-1])
            year = self._extract_year(None, url)
            petitioner = None
            respondent = None
            case_name = filename.replace(".pdf", "").replace("-", " ").replace("_", " ")[:200]
            matter_type = self._extract_matter_type(filename)

            # Try structured parse from CDN filename pattern
            m = self._CASE_FILENAME_RE.search(filename)
            if m:
                case_type = m.group("case_type").upper()
                case_no = m.group("case_no")
                year = int(m.group("year"))
                parties_raw = m.group("parties").replace("-", " ").strip("()")

                # Split parties on VERSUS / VS
                versus_split = re.split(r'\bVERSUS\b|\bVS\b', parties_raw, maxsplit=1, flags=re.IGNORECASE)
                if len(versus_split) == 2:
                    petitioner = versus_split[0].strip().title()[:300]
                    respondent = versus_split[1].strip().title()[:300]
                    case_name = f"{petitioner} v. {respondent}"
                else:
                    case_name = parties_raw.title()[:400]

                case_name = f"{case_type} No. {case_no} of {year} — {case_name}"[:500]
                matter_type = self._extract_matter_type(case_type)

            if not case_name:
                case_name = f"P&H HC Judgment {year}"

            return {
                "case_name": case_name,
                "petitioner": petitioner,
                "respondent": respondent,
                "judgment_date": None,
                "judge_name": None,
                "year": year,
                "court": self.COURT_NAME,
                "official_source": self.SOURCE_NAME,
                "source_url": url,
                "source_doc_id": self._extract_source_doc_id(url),
                "judgment_text": None,
                "matter_type": matter_type,
                "primary_citation": None,
                "subject_tags": None,
            }
        except Exception as e:
            logger.error(f"P&H HC: Error parsing PDF URL {url}: {e}")
            return None

    # ------------------------------------------------------------------ #
    #  Extraction helpers                                                  #
    # ------------------------------------------------------------------ #

    def _extract_case_name(self, html: str) -> Optional[str]:
        patterns = [
            r'<title>([^<|—-]+)</title>',
            r'<h1[^>]*>([^<]+)</h1>',
            r'<h2[^>]*>([^<]+)</h2>',
            r'Case["\']?\s*:\s*["\']?([^"\'<\n]{10,400})',
            r'<meta\s+name="title"\s+content="([^"]+)"',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                name = re.sub(r'\s+\|\s+.*', '', matches[0]).strip()
                name = re.sub(r'\s+—\s+.*', '', name).strip()
                if 10 < len(name) < 500:
                    return name
        return None

    def _extract_petitioner(self, html: str) -> Optional[str]:
        patterns = [
            r'Petitioner["\']?\s*[:\-]\s*["\']?([^"\'<\n]{3,300})',
            r'Appellant["\']?\s*[:\-]\s*["\']?([^"\'<\n]{3,300})',
            r'<td[^>]*>[Pp]etitioner</td>\s*<td[^>]*>([^<]+)</td>',
            r'<strong>Petitioner</strong>\s*[:\-]\s*([^<\n]+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        return None

    def _extract_respondent(self, html: str) -> Optional[str]:
        patterns = [
            r'Respondent["\']?\s*[:\-]\s*["\']?([^"\'<\n]{3,300})',
            r'Appellee["\']?\s*[:\-]\s*["\']?([^"\'<\n]{3,300})',
            r'<td[^>]*>[Rr]espondent</td>\s*<td[^>]*>([^<]+)</td>',
            r'<strong>Respondent</strong>\s*[:\-]\s*([^<\n]+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        return None

    def _extract_judgment_date(self, html: str) -> Optional[datetime]:
        patterns = [
            r'Date[s]?["\']?\s*[:\-]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'Decided["\']?\s*[:\-]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'Judgment Date["\']?\s*[:\-]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html)
            if matches:
                date_str = matches[0]
                for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d']:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
        return None

    def _extract_judge_names(self, html: str) -> Optional[str]:
        patterns = [
            r'<b>([A-Za-z\s.,]+),?\s+J\.</b>',
            r'[Jj]udge[s]?["\']?\s*[:\-]\s*([^<\n]+)',
            r'Bench["\']?\s*[:\-]\s*([^<\n]+)',
            r'Coram["\']?\s*[:\-]\s*([^<\n]+)',
        ]
        names = []
        for pattern in patterns:
            names.extend(re.findall(pattern, html))
        return "; ".join(n.strip() for n in names[:3]) if names else None

    def _extract_citation(self, html: str) -> Optional[str]:
        patterns = [
            r'\(\d{4}\)\s+\(\d\)\s+[A-Z]+\s+\d+',
            r'Citation["\']?\s*[:\-]\s*([^\n<]{5,100})',
            r'<b>([^<]*\d{4}[^<]*)</b>',
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
            r'<div[^>]*id="[^"]*judgment[^"]*"[^>]*>([\s\S]*?)</div>',
            r'<p[^>]*class="[^"]*body[^"]*"[^>]*>([^<]+(?:</p[^>]*>[^<]*<p[^>]*>)*[^<]+)</p>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            if matches:
                text = re.sub(r'<[^>]+>', ' ', matches[0])
                text = re.sub(r'\s+', ' ', text).strip()[:5000]
                if len(text) > 100:
                    return text
        return None

    def _extract_matter_type(self, text: str) -> Optional[str]:
        keywords = {
            "criminal appeal": "criminal",
            "civil appeal": "civil",
            "writ petition": "civil",
            "letters patent appeal": "civil",
            "crr": "criminal",          # Criminal Revision
            "cra": "criminal",          # Criminal Appeal
            "csa": "civil",             # Civil Second Appeal
            "rsa": "civil",             # Regular Second Appeal
            "crwp": "civil",            # Civil Writ Petition
            "crm": "criminal",          # Criminal Misc.
            "cheque bounce": "criminal",
            "ipc": "criminal",
            "crpc": "criminal",
            "cpc": "civil",
            "commercial": "commercial",
            "labour": "labour",
            "matrimonial": "matrimonial",
            "property": "civil",
            "section 138": "criminal",
        }
        tl = text.lower()
        for keyword, matter_type in keywords.items():
            if keyword in tl:
                return matter_type
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
        # CDN URL: digitaloceanspaces.com/[numeric_id]/[filename].pdf
        m = re.search(r'digitaloceanspaces\.com/(\d+)/', url)
        if m:
            return m.group(1)
        # /lts_judgments/CRR-1234-2024.pdf → "CRR-1234-2024"
        m = re.search(r'/lts_judgments/([^/]+?)(?:\.pdf)?$', url, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'[?&]id=([^&]+)', url)
        if m:
            return m.group(1)
        return None

    def _extract_subject_tags(self, html: str) -> Optional[str]:
        tag_map = {
            "criminal appeal": "criminal",
            "civil appeal": "civil",
            "writ petition": "writ",
            "letters patent appeal": "appeal",
            "cheque bounce": "cheque_bounce",
            "section 138": "cheque_bounce",
            "ipc": "criminal",
            "crpc": "criminal",
            "cpc": "civil",
            "criminal revision": "criminal",
            "civil revision": "civil",
            "commercial": "commercial",
            "labour": "labour",
            "matrimonial": "matrimonial",
            "property": "property",
            "bail": "bail",
            "consumer": "consumer",
        }
        hl = html.lower()
        seen: set = set()
        tags = []
        for kw, tag in tag_map.items():
            if kw in hl and tag not in seen:
                tags.append(tag)
                seen.add(tag)
        return json.dumps(tags) if tags else None
