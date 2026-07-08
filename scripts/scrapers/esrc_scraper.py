#!/usr/bin/env python3
"""
eSCR (Supreme Court Reports) CLI scraper
Data sourced from official Government of India court websites.
All judgment text is public domain under Section 52(1)(q) of the Copyright Act 1957.
No commercial data is scraped.

Usage:
    python scripts/scrapers/esrc_scraper.py --limit 100 --update-only
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime, timezone
from calendar import monthrange
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.services.scrapers.esrc_scraper import ESCRScraper
from backend.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('esrc_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def _parse_date_args(args) -> tuple:
    date_from = date_to = None
    if args.month and args.year:
        year, month = args.year, args.month
        last_day = monthrange(year, month)[1]
        date_from = datetime(year, month, 1, tzinfo=timezone.utc)
        date_to = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    else:
        if args.from_date:
            date_from = datetime.strptime(args.from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.to_date:
            date_to = datetime.strptime(args.to_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
    return date_from, date_to


async def main():
    parser = argparse.ArgumentParser(description='eSCR (Supreme Court) Judgment Scraper')
    parser.add_argument('--limit', type=int, default=100,
                        help='Maximum number of judgments to scrape (default: 100)')
    parser.add_argument('--update-only', action='store_true',
                        help='Only add new judgments, skip existing ones')
    parser.add_argument('--month', type=int, choices=range(1, 13), metavar='MONTH',
                        help='Month number (1-12) — use with --year to filter by calendar month')
    parser.add_argument('--year', type=int, default=datetime.now().year,
                        help='Year (default: current year) — used with --month')
    parser.add_argument('--from-date', dest='from_date', metavar='YYYY-MM-DD',
                        help='Only import judgments on or after this date')
    parser.add_argument('--to-date', dest='to_date', metavar='YYYY-MM-DD',
                        help='Only import judgments on or before this date')

    args = parser.parse_args()
    date_from, date_to = _parse_date_args(args)

    logger.info("Starting eSCR scraper CLI")
    logger.info(f"Target limit: {args.limit}")
    logger.info(f"Update only: {args.update_only}")
    if date_from or date_to:
        logger.info(f"Date filter: {date_from.date() if date_from else '—'} → {date_to.date() if date_to else '—'}")
    
    try:
        # Create async database engine
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
        )
        
        # Create session factory
        async_session = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        # Run scraper
        async with async_session() as session:
            async with ESCRScraper(session) as scraper:
                result = await scraper.scrape_all(
                    limit=args.limit,
                    date_from=date_from,
                    date_to=date_to,
                )
                
                # Print results
                logger.info("=" * 80)
                logger.info("SCRAPER RESULTS")
                logger.info("=" * 80)
                logger.info(f"Success: {result.get('success')}")
                logger.info(f"Source: {result.get('source')}")
                logger.info(f"Judgments Added: {result.get('added')}")
                logger.info(f"Judgments Skipped: {result.get('skipped')}")
                logger.info(f"Total Processed: {result.get('total')}")
                
                if result.get('errors'):
                    logger.warning(f"Errors encountered ({len(result['errors'])}):")
                    for error in result['errors'][:10]:  # Show first 10 errors
                        logger.warning(f"  - {error}")
        
        # Close engine
        await engine.dispose()
        logger.info("eSCR scraper completed successfully")
        return 0 if result.get('success') else 1
        
    except Exception as e:
        logger.error(f"Fatal error in eSCR scraper: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
