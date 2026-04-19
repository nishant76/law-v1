"""
Celery tasks for citation scraping
Data sourced from official Government of India court websites.
All judgment text is public domain under Section 52(1)(q) of the Copyright Act 1957.
No commercial data is scraped.
"""

import asyncio
import logging
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.services.scrapers.esrc_scraper import ESCRScraper
from backend.services.scrapers.phc_scraper import PHCScraper
from backend.core.config import settings

logger = logging.getLogger(__name__)


@shared_task(name="citations.scraper_update", bind=True, max_retries=2, time_limit=3600)
def scraper_update(self):
    """
    Daily cron job to scrape new judgments from government sources:
    - eSCR (Supreme Court Reports) from main.sci.gov.in
    - P&H HC judgments from highcourtchd.gov.in
    
    Runs daily at 02:00 UTC (7:30 AM IST)
    Target: 5,000 SC + 5,000 P&H HC = 10,000 total judgments before launch
    
    Only adds new judgments; deduplicates on source_url
    """
    try:
        logger.info("Starting daily scraper_update task")
        
        # Run async scraper logic
        result = asyncio.run(_run_scrapers())
        
        logger.info(f"Scraper update completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in scraper_update task: {e}", exc_info=True)
        # Retry after 1 minute
        raise self.retry(exc=e, countdown=60, max_retries=2)


async def _run_scrapers():
    """Run both government court scrapers and collect results"""
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
        
        results = {}
        
        # Run eSCR scraper (target: 5,000 judgments)
        try:
            logger.info("Running eSCR scraper...")
            async with async_session() as session:
                async with ESCRScraper(session) as scraper:
                    esrc_result = await scraper.scrape_all(limit=5000)
                    results['esrc'] = esrc_result
                    logger.info(f"eSCR scraper result: added={esrc_result.get('added')}, "
                               f"skipped={esrc_result.get('skipped')}, "
                               f"errors={len(esrc_result.get('errors', []))}")
        except Exception as e:
            logger.error(f"Error running eSCR scraper: {e}", exc_info=True)
            results['esrc'] = {
                'success': False,
                'source': 'eSCR',
                'message': str(e),
                'added': 0,
                'skipped': 0,
                'errors': [str(e)]
            }
        
        # Run P&H HC scraper (target: 5,000 judgments)
        try:
            logger.info("Running P&H HC scraper...")
            async with async_session() as session:
                async with PHCScraper(session) as scraper:
                    phc_result = await scraper.scrape_all(limit=5000)
                    results['phc'] = phc_result
                    logger.info(f"P&H HC scraper result: added={phc_result.get('added')}, "
                               f"skipped={phc_result.get('skipped')}, "
                               f"errors={len(phc_result.get('errors', []))}")
        except Exception as e:
            logger.error(f"Error running P&H HC scraper: {e}", exc_info=True)
            results['phc'] = {
                'success': False,
                'source': 'P&H HC',
                'message': str(e),
                'added': 0,
                'skipped': 0,
                'errors': [str(e)]
            }
        
        # Close engine
        await engine.dispose()
        
        # Aggregate results
        total_added = (results.get('esrc', {}).get('added', 0) + 
                      results.get('phc', {}).get('added', 0))
        total_skipped = (results.get('esrc', {}).get('skipped', 0) + 
                        results.get('phc', {}).get('skipped', 0))
        total_errors = (len(results.get('esrc', {}).get('errors', [])) + 
                       len(results.get('phc', {}).get('errors', [])))
        
        aggregated = {
            'success': results.get('esrc', {}).get('success') and results.get('phc', {}).get('success'),
            'total_added': total_added,
            'total_skipped': total_skipped,
            'total_errors': total_errors,
            'sources': results
        }
        
        logger.info(f"Daily scraper_update completed: added={total_added}, "
                   f"skipped={total_skipped}, errors={total_errors}")
        
        return aggregated
        
    except Exception as e:
        logger.error(f"Fatal error in _run_scrapers: {e}", exc_info=True)
        return {
            'success': False,
            'message': str(e),
            'total_added': 0,
            'total_skipped': 0,
            'total_errors': 1,
            'sources': {}
        }

