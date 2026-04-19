#!/usr/bin/env python3
"""
P&H HC (Punjab and Haryana High Court) CLI scraper
Data sourced from official Government of India court websites.
All judgment text is public domain under Section 52(1)(q) of the Copyright Act 1957.
No commercial data is scraped.

Usage:
    python scripts/scrapers/phc_scraper.py --limit 100 --update-only
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.services.scrapers.phc_scraper import PHCScraper
from backend.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phc_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description='P&H HC (High Court) Judgment Scraper')
    parser.add_argument('--limit', type=int, default=100,
                        help='Maximum number of judgments to scrape (default: 100)')
    parser.add_argument('--update-only', action='store_true',
                        help='Only add new judgments, skip existing ones')
    
    args = parser.parse_args()
    
    logger.info("Starting P&H HC scraper CLI")
    logger.info(f"Target limit: {args.limit}")
    logger.info(f"Update only: {args.update_only}")
    
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
            async with PHCScraper(session) as scraper:
                result = await scraper.scrape_all(limit=args.limit)
                
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
        logger.info("P&H HC scraper completed successfully")
        return 0 if result.get('success') else 1
        
    except Exception as e:
        logger.error(f"Fatal error in P&H HC scraper: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
