"""
Citation scrapers for government court websites
Data sourced from official Government of India court websites.
All judgment text is public domain under Section 52(1)(q) of the Copyright Act 1957.
No commercial data is scraped.
"""

from backend.services.scrapers.esrc_scraper import ESCRScraper
from backend.services.scrapers.phc_scraper import PHCScraper
from backend.services.scrapers.base_scraper import BaseScraper

__all__ = [
    "BaseScraper",
    "ESCRScraper",
    "PHCScraper",
]
