"""
eSCR (Supreme Court Reports) scraper from main.sci.gov.in
Data sourced from official Government of India Supreme Court website.
All judgment text is public domain under Section 52(1)(q) of the Copyright Act 1957.
No commercial data is scraped.

Judgment listing:  https://main.sci.gov.in/judgments
Individual PDFs:   https://main.sci.gov.in/supremecourt/[year]/[case_id]/[filename].pdf
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import re

from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ESCRScraper(BaseScraper):
    """Scraper for Supreme Court Reports from main.sci.gov.in"""

    BASE_URL = "https://main.sci.gov.in"
    SOURCE_NAME = "eSCR"
    COURT_NAME = "Supreme Court of India"
    RATE_LIMIT_DELAY = 3.0
    SSL_VERIFY = False  # main.sci.gov.in has SSL cert issues (expired / hostname mismatch)

    # PDF path pattern: /supremecourt/[year]/[case_id]/[filename].pdf
    _PDF_PATTERN = re.compile(r'/supremecourt/(\d{4})/(\d+)/[^"\'<\s]+\.pdf', re.IGNORECASE)
    # Judgment page links
    _PAGE_PATTERN = re.compile(r'/judgments?/\d+/?', re.IGNORECASE)

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.listing_url = f"{self.BASE_URL}/judgments"

    async def get_judgment_urls(self, limit: int = 5000) -> List[str]:
        """
        Fetch the judgment listing page and extract individual judgment/PDF URLs.
        Falls back to year-based pagination if the listing page supports it.
        """
        urls: List[str] = []
        page = 1
        max_pages = max(1, (limit // 20) + 1)  # ~20 judgments per page assumed

        while len(urls) < limit and page <= max_pages:
            listing = f"{self.listing_url}?page={page}"
            logger.info(f"eSCR: Fetching listing page {page} ({len(urls)}/{limit} URLs so far)")

            response = await self.rate_limited_request(listing)
            if not response:
                logger.warning(f"eSCR: No response for page {page}, stopping")
                break

            new_urls = self._extract_urls_from_listing(response.text)
            if not new_urls:
                logger.warning(f"eSCR: No judgment URLs found on page {page}, stopping")
                break

            before = len(urls)
            for u in new_urls:
                if u not in urls:
                    urls.append(u)
            if len(urls) == before:
                # Duplicate page — stop
                break

            page += 1

        logger.info(f"eSCR: Collected {len(urls)} judgment URLs")
        return urls[:limit]

    def _extract_urls_from_listing(self, html: str) -> List[str]:
        """Extract judgment URLs from the listing page HTML."""
        urls = []
        try:
            # Priority 1: PDF links  /supremecourt/[year]/[id]/[file].pdf
            for m in self._PDF_PATTERN.finditer(html):
                full_url = f"{self.BASE_URL}{m.group(0)}"
                if full_url not in urls:
                    urls.append(full_url)

            # Priority 2: HTML judgment page links /judgments/[id]
            for m in self._PAGE_PATTERN.finditer(html):
                full_url = f"{self.BASE_URL}{m.group(0)}"
                if full_url not in urls:
                    urls.append(full_url)
        except Exception as e:
            logger.error(f"eSCR: Error extracting URLs from listing: {e}")
        return urls

    async def parse_judgment(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a Supreme Court judgment page or PDF landing page.
        """
        try:
            response = await self.rate_limited_request(url)
            if not response:
                return None

            html = response.text
            content_type = response.headers.get("content-type", "")

            # If we landed directly on a PDF, extract metadata from the URL itself
            if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
                return self._parse_from_pdf_url(url)

            case_name = self._extract_case_name(html)
            if not case_name:
                logger.debug(f"eSCR: Could not extract case name from {url}")
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
            logger.error(f"eSCR: Error parsing judgment from {url}: {e}")
            return None

    def _parse_from_pdf_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Derive metadata from a PDF URL when no HTML wrapper is available.
        URL pattern: /supremecourt/[year]/[case_id]/[filename].pdf
        """
        try:
            m = self._PDF_PATTERN.search(url)
            if not m:
                return None
            year = int(m.group(1))
            case_id = m.group(2)

            # Derive a case name from the filename segment
            filename = url.rsplit("/", 1)[-1].replace(".pdf", "").replace("_", " ")
            case_name = filename[:200] if filename else f"SC Judgment {year}"

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
                "source_doc_id": case_id,
                "judgment_text": None,
                "matter_type": "general",
                "primary_citation": None,
                "subject_tags": None,
            }
        except Exception as e:
            logger.error(f"eSCR: Error parsing PDF URL {url}: {e}")
            return None

    # ------------------------------------------------------------------ #
    #  Extraction helpers                                                  #
    # ------------------------------------------------------------------ #

    def _extract_case_name(self, html: str) -> Optional[str]:
        patterns = [
            r'<h1[^>]*>([^<]+)</h1>',
            r'<title>([^<|—-]+)</title>',
            r'<meta\s+name="title"\s+content="([^"]+)"',
            r'case_name["\']?\s*:\s*["\']?([^"\'<]{10,500})',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                name = matches[0].strip()
                if 10 < len(name) < 500:
                    return name
        return None

    def _extract_petitioner(self, html: str) -> Optional[str]:
        patterns = [
            r'Petitioner["\']?\s*:\s*["\']?([^"\'<\n]{3,300})',
            r'Appellant["\']?\s*:\s*["\']?([^"\'<\n]{3,300})',
            r'<td[^>]*>Petitioner</td>\s*<td[^>]*>([^<]+)</td>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        return None

    def _extract_respondent(self, html: str) -> Optional[str]:
        patterns = [
            r'Respondent["\']?\s*:\s*["\']?([^"\'<\n]{3,300})',
            r'Appellee["\']?\s*:\s*["\']?([^"\'<\n]{3,300})',
            r'<td[^>]*>Respondent</td>\s*<td[^>]*>([^<]+)</td>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        return None

    def _extract_judgment_date(self, html: str) -> Optional[datetime]:
        patterns = [
            r'Decided\s+on["\']?\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'Date["\']?\s*:\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
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
            r'Judge["\']?\s*:\s*([^<\n]+)',
            r'Bench["\']?\s*:\s*([^<\n]+)',
        ]
        names = []
        for pattern in patterns:
            names.extend(re.findall(pattern, html))
        return "; ".join(n.strip() for n in names[:3]) if names else None

    def _extract_citation(self, html: str) -> Optional[str]:
        patterns = [
            r'\(\d{4}\)\s+\d+\s+SCC\s+\d+',
            r'\(\d{4}\)\s+\d+\s+SCR\s+\d+',
            r'Citation["\']?\s*:\s*([^\n<]{5,100})',
            r'<b>([^<]*\(\d{4}\)[^<]*)</b>',
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
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            if matches:
                text = re.sub(r'<[^>]+>', ' ', matches[0])
                text = re.sub(r'\s+', ' ', text).strip()[:5000]
                if len(text) > 100:
                    return text
        return None

    def _extract_matter_type(self, html: str) -> Optional[str]:
        keywords = {
            "constitutional": "constitutional",
            "criminal": "criminal",
            "civil": "civil",
            "commercial": "commercial",
            "labour": "labour",
            "tax": "tax",
            "administrative": "administrative",
        }
        html_lower = html.lower()
        for keyword, matter_type in keywords.items():
            if keyword in html_lower:
                return matter_type
        return "general"

    def _extract_year(self, judgment_date: Optional[datetime], url: str) -> int:
        if judgment_date:
            return judgment_date.year
        m = self._PDF_PATTERN.search(url)
        if m:
            return int(m.group(1))
        year_matches = re.findall(r'/(\d{4})/', url)
        if year_matches:
            y = int(year_matches[0])
            if 1950 <= y <= datetime.now(timezone.utc).year:
                return y
        return datetime.now(timezone.utc).year

    def _extract_source_doc_id(self, url: str) -> Optional[str]:
        m = self._PDF_PATTERN.search(url)
        if m:
            return m.group(2)
        m = re.search(r'/judgments?/(\d+)', url)
        if m:
            return m.group(1)
        return None

    def _extract_subject_tags(self, html: str) -> Optional[str]:
        tag_map = {
            "constitutional": "constitutional",
            "criminal": "criminal",
            "civil": "civil",
            "commercial": "commercial",
            "labour": "labour",
            "tax": "tax",
            "administrative": "administrative",
            "bail": "bail",
            "writ": "writ",
            "appeal": "appeal",
            "section 138": "cheque_bounce",
            "property": "property",
            "matrimonial": "matrimonial",
            "consumer": "consumer",
        }
        hl = html.lower()
        tags = [tag for kw, tag in tag_map.items() if kw in hl]
        return json.dumps(list(dict.fromkeys(tags))) if tags else None
