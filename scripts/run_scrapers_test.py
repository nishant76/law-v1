#!/usr/bin/env python3
"""
Test runner for eSCR, P&H HC, and eCourts scrapers.
Runs all three scrapers with a small batch (--limit 50) to verify
data is being stored correctly in law.citations before full production runs.

Usage (local):
    python scripts/run_scrapers_test.py

Usage (Docker):
    docker compose exec backend python scripts/run_scrapers_test.py

Optional flags:
    --limit N    Number of judgments per scraper (default: 50)
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from backend.services.scrapers.esrc_scraper import ESCRScraper
from backend.services.scrapers.phc_scraper import PHCScraper
from backend.services.scrapers.ecourts_scraper import ECourtsScraper
from backend.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("run_scrapers_test")

PROGRESS_INTERVAL = 10  # log every N judgments during test runs


async def count_citations(session: AsyncSession) -> int:
    result = await session.execute(
        text("SELECT COUNT(*) FROM law.citations WHERE deleted_at IS NULL")
    )
    return result.scalar_one()


async def run_scraper(scraper_cls, session: AsyncSession, limit: int, label: str) -> dict:
    logger.info("=" * 60)
    logger.info(f"Starting {label} (limit={limit})")
    logger.info("=" * 60)

    before = await count_citations(session)

    async with scraper_cls(session) as scraper:
        result = await scraper.scrape_all(limit=limit, progress_interval=PROGRESS_INTERVAL)

    after = await count_citations(session)

    result["citations_in_db_before"] = before
    result["citations_in_db_after"] = after
    result["net_inserted"] = after - before
    return result


async def main(limit: int) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )

    results = {}

    async with async_session() as session:
        results["esrc"] = await run_scraper(ESCRScraper, session, limit, "eSCR scraper")

    async with async_session() as session:
        results["phc"] = await run_scraper(PHCScraper, session, limit, "P&H HC scraper")

    async with async_session() as session:
        results["ecourts"] = await run_scraper(ECourtsScraper, session, limit, "eCourts scraper")

    # Final summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST RUN COMPLETE — FINAL SUMMARY")
    logger.info("=" * 60)

    total_added = 0
    total_skipped = 0
    for key, r in results.items():
        label = r.get("source", key.upper())
        added = r.get("added", 0)
        skipped = r.get("skipped", 0)
        net = r.get("net_inserted", 0)
        errors = len(r.get("errors", []))
        success = r.get("success", False)
        status = "OK" if success else "FAILED"

        logger.info(
            f"  [{status}] {label}: added={added}, skipped={skipped}, "
            f"net_inserted={net}, errors={errors}"
        )

        if r.get("errors"):
            for err in r["errors"][:5]:
                logger.warning(f"         error: {err}")

        total_added += added
        total_skipped += skipped

    logger.info("-" * 60)
    logger.info(f"  TOTAL: added={total_added}, skipped={total_skipped}")
    logger.info("=" * 60)

    await engine.dispose()

    # Exit non-zero if either scraper failed
    if not all(r.get("success") for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test scraper run — small batch")
    parser.add_argument(
        "--limit", type=int, default=50,
        help="Number of judgments to scrape per source (default: 50)"
    )
    args = parser.parse_args()
    asyncio.run(main(args.limit))
