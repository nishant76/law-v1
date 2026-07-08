"""
Base scraper class for government court websites
Data sourced from official Government of India court websites. 
All judgment text is public domain under Section 52(1)(q) of the Copyright Act 1957. 
No commercial data is scraped.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.models.law_citation import Citation

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for government court website scrapers"""
    
    # Override these in subclasses
    BASE_URL: str = ""
    SOURCE_NAME: str = ""  # e.g., "eSCR" or "P&H HC"
    COURT_NAME: str = ""  # e.g., "Supreme Court" or "Punjab and Haryana High Court"
    RATE_LIMIT_DELAY: float = 3.0  # 1 request per 3 seconds
    USER_AGENT: str = "NikharBot/1.0 (legal-ai-platform)"
    SSL_VERIFY: bool = True  # Set False for Indian govt sites with cert issues
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.robot_parser = RobotFileParser()
        self.citations_added = 0
        self.citations_skipped = 0
        self.errors = []
        self.http_client = None
        
    async def __aenter__(self):
        timeout = httpx.Timeout(30.0, connect=10.0)
        if not self.SSL_VERIFY:
            logger.warning(f"{self.SOURCE_NAME}: SSL verification disabled for {self.BASE_URL}")
        self.http_client = httpx.AsyncClient(
            timeout=timeout,
            verify=self.SSL_VERIFY,
            headers={"User-Agent": self.USER_AGENT},
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.http_client:
            await self.http_client.aclose()
    
    async def check_robots_txt(self) -> bool:
        """Check if we're allowed to scrape via robots.txt"""
        try:
            robots_url = urljoin(self.BASE_URL, "/robots.txt")
            response = await self.http_client.get(robots_url, follow_redirects=True)
            if response.status_code == 200:
                self.robot_parser.parse(response.text.splitlines())
                can_fetch = self.robot_parser.can_fetch(self.USER_AGENT, self.BASE_URL)
                if not can_fetch:
                    logger.warning(f"robots.txt disallows scraping {self.BASE_URL}")
                    return False
            return True
        except Exception as e:
            logger.warning(f"Error checking robots.txt: {e}. Proceeding with caution.")
            return True
    
    async def rate_limited_request(self, url: str, silent_404: bool = False, **kwargs) -> Optional[httpx.Response]:
        """Make HTTP request with rate limiting.

        silent_404: if True, 404 responses are logged at DEBUG level and not
        added to self.errors (used for probing optional/date-based listing URLs).
        """
        try:
            await asyncio.sleep(self.RATE_LIMIT_DELAY)
            response = await self.http_client.get(url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if silent_404 and e.response.status_code == 404:
                logger.debug(f"404 (expected) {url}")
                return None
            error_msg = f"HTTP error fetching {url}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return None
        except httpx.HTTPError as e:
            error_msg = f"HTTP error fetching {url}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return None
        except Exception as e:
            error_msg = f"Unexpected error fetching {url}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return None
    
    @abstractmethod
    async def get_judgment_urls(
        self,
        limit: int = 5000,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[str]:
        """Get list of judgment URLs to scrape. Implement in subclass."""
        pass
    
    @abstractmethod
    async def parse_judgment(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse a judgment page and extract data. Implement in subclass."""
        pass
    
    async def judgment_exists(self, source_url: str) -> bool:
        """Check if judgment already exists in database.

        Uses a savepoint so that a query failure (e.g. schema mismatch) cannot
        abort the parent transaction and corrupt subsequent inserts.
        """
        try:
            async with self.session.begin_nested():
                result = await self.session.execute(
                    select(Citation).where(
                        and_(
                            Citation.source_url == source_url,
                            Citation.deleted_at.is_(None)
                        )
                    )
                )
                return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Error checking if judgment exists: {e}")
            return False
    
    async def store_citation(self, judgment_data: Dict[str, Any], progress_interval: int = 100) -> bool:
        """Store citation in database"""
        try:
            # Check if already exists
            if await self.judgment_exists(judgment_data["source_url"]):
                logger.debug(f"Citation already exists: {judgment_data['source_url']}")
                self.citations_skipped += 1
                return False

            # Generate citation key from court, year, and case name
            citation_key = self._generate_citation_key(judgment_data)

            citation = Citation(
                citation_key=citation_key,
                case_name=judgment_data.get("case_name", ""),
                court=judgment_data.get("court", self.COURT_NAME),
                year=judgment_data.get("year", datetime.utcnow().year),
                petitioner=judgment_data.get("petitioner"),
                respondent=judgment_data.get("respondent"),
                judge_name=judgment_data.get("judge_name"),
                judgment_date=judgment_data.get("judgment_date"),
                judgment_text=judgment_data.get("judgment_text"),
                summary=judgment_data.get("summary"),
                matter_type=judgment_data.get("matter_type"),
                outcome=judgment_data.get("outcome"),
                primary_citation=judgment_data.get("primary_citation"),
                subject_tags=judgment_data.get("subject_tags"),
                official_source=judgment_data.get("official_source", self.SOURCE_NAME),
                source_url=judgment_data.get("source_url"),
                source_doc_id=judgment_data.get("source_doc_id"),
                scraped_at=datetime.now(timezone.utc),
            )

            self.session.add(citation)
            self.citations_added += 1

            if self.citations_added % progress_interval == 0:
                logger.info(f"{self.SOURCE_NAME}: Added {self.citations_added} citations, skipped {self.citations_skipped}")

            return True
        except Exception as e:
            error_msg = f"Error storing citation: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def _generate_citation_key(self, judgment_data: Dict[str, Any]) -> str:
        """Generate unique citation key using source_doc_id when available, UUID otherwise."""
        court_abbr = self._get_court_abbr()
        year = judgment_data.get("year", datetime.utcnow().year)
        source_doc_id = judgment_data.get("source_doc_id")

        if source_doc_id:
            # Stable, deterministic key based on the source's own identifier
            key = f"{court_abbr}-{year}-{source_doc_id}"
        else:
            # Fall back to UUID suffix to guarantee uniqueness
            import uuid as _uuid
            key = f"{court_abbr}-{year}-{_uuid.uuid4().hex[:12]}"

        return key[:100]  # citation_key column is VARCHAR(100)
    
    def _get_court_abbr(self) -> str:
        """Get court abbreviation for citation key"""
        if "Supreme" in self.COURT_NAME:
            return "SC"
        elif "High Court" in self.COURT_NAME:
            return "HC"
        else:
            return "DC"  # District Court
    
    async def scrape_all(
        self,
        limit: int = 5000,
        progress_interval: int = 100,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Main scraping method.

        date_from / date_to: if provided, only judgments whose judgment_date
        falls within [date_from, date_to] are stored.  Judgments with no
        parseable date are stored only when no date filter is active.
        """
        date_filter_active = date_from is not None or date_to is not None
        if date_filter_active:
            logger.info(
                f"{self.SOURCE_NAME}: date filter active — "
                f"from={date_from.date() if date_from else '—'} "
                f"to={date_to.date() if date_to else '—'}"
            )

        try:
            logger.info(f"Starting {self.SOURCE_NAME} scraper (target: {limit} judgments)")

            # Check robots.txt
            if not await self.check_robots_txt():
                return {
                    "success": False,
                    "source": self.SOURCE_NAME,
                    "message": "Robots.txt disallows scraping",
                    "added": 0,
                    "skipped": 0,
                    "errors": self.errors
                }

            # Get list of judgment URLs — pass date range so subclasses can
            # use date-based listing pages instead of the generic recent-only listing
            urls = await self.get_judgment_urls(limit, date_from=date_from, date_to=date_to)
            logger.info(f"{self.SOURCE_NAME}: Found {len(urls)} judgment URLs to scrape")

            date_skipped = 0

            for url in urls:
                try:
                    # Parse judgment
                    judgment_data = await self.parse_judgment(url)
                    if not judgment_data:
                        continue

                    # Date range filter
                    if date_filter_active:
                        jdate: Optional[datetime] = judgment_data.get("judgment_date")
                        if jdate is None:
                            # No date parseable — skip when filter is active
                            date_skipped += 1
                            logger.debug(f"{self.SOURCE_NAME}: skipping (no date) {url}")
                            continue
                        # Make timezone-aware for comparison
                        if jdate.tzinfo is None:
                            jdate = jdate.replace(tzinfo=timezone.utc)
                        if date_from and jdate < date_from:
                            date_skipped += 1
                            continue
                        if date_to and jdate > date_to:
                            date_skipped += 1
                            continue

                    # Store in database
                    await self.store_citation(judgment_data, progress_interval=progress_interval)

                except Exception as e:
                    error_msg = f"Error processing {url}: {e}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
                    continue

                # Stop if we've reached the limit
                if self.citations_added >= limit:
                    break

            if date_filter_active:
                logger.info(f"{self.SOURCE_NAME}: {date_skipped} judgments skipped (outside date range or no date)")
            
            # Commit all changes
            await self.session.commit()
            
            result = {
                "success": True,
                "source": self.SOURCE_NAME,
                "added": self.citations_added,
                "skipped": self.citations_skipped,
                "errors": self.errors,
                "total": self.citations_added + self.citations_skipped
            }
            
            logger.info(f"{self.SOURCE_NAME} scraper completed: {result}")
            return result
            
        except Exception as e:
            error_msg = f"Fatal error in {self.SOURCE_NAME} scraper: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            await self.session.rollback()
            
            return {
                "success": False,
                "source": self.SOURCE_NAME,
                "message": str(e),
                "added": self.citations_added,
                "skipped": self.citations_skipped,
                "errors": self.errors
            }
