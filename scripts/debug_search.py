#!/usr/bin/env python3
"""
Diagnose citation search end-to-end against the DB the scripts connect to.

Prints: which DB host, how many citations exist, the self_hosted ones, and what
the real search service returns for a query. If this shows results but the app
shows none, the app is pointed at a DIFFERENT database (e.g. Docker Postgres vs
Neon).

Usage:  python scripts/debug_search.py [query]
"""
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal, engine
from backend.models.law_citation import Citation
from backend.services.search_service import get_search_service


async def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "Patiala"

    host = urlsplit(settings.DATABASE_URL).hostname
    print(f"\nDB host the scripts use : {host}")
    print(f"Search query            : '{query}'\n" + "=" * 64)

    async with AsyncSessionLocal() as session:
        total = (await session.execute(
            select(func.count()).select_from(Citation).where(Citation.deleted_at.is_(None))
        )).scalar_one()
        print(f"Total citations (not deleted): {total}")

        rows = (await session.execute(
            select(Citation.case_name, Citation.court, Citation.link_status, Citation.blob_path)
            .where(Citation.deleted_at.is_(None))
        )).all()
        print("\nAll citations (case | court | link_status | blob_path):")
        for r in rows:
            print(f"  - {r[0][:40]:42} | {(r[1] or '')[:30]:32} | {r[2]:11} | {r[3] or '(none)'}")

        self_hosted = [r for r in rows if r[2] == "self_hosted"]
        print(f"\nself_hosted (visible in search): {len(self_hosted)}")

        # Run the real search path
        svc = get_search_service(session)
        results = await svc.search_public_judgments(query=query, _query_vector=[], top=10)
        print(f"\nsearch_public_judgments('{query}') returned: {len(results)}")
        for r in results:
            print(f"  -> {r.get('case_name')}  [{r.get('link_status')}]  judgment_url={r.get('judgment_url')}")

    await engine.dispose()
    print("\n" + "=" * 64)
    if total == 0:
        print("DB is EMPTY here — the importer wrote to a different DB than this one.")
    elif self_hosted and not results:
        print("Data exists but search returned 0 — search/FTS issue.")
    elif results:
        print("Search WORKS here. If the app shows nothing, the APP is on a different DB.")


if __name__ == "__main__":
    asyncio.run(main())
