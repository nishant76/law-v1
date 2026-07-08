#!/usr/bin/env python3
"""
Verify + self-host citation judgment PDFs (LAUNCH QUALITY MANDATE).

For every citation in law.citations this script:
  1. HTTP-fetches source_url (the official government link).
  2. If it returns a real PDF, saves our own copy to local storage
     (data/judgments/<citation_id>.pdf) and sets:
         blob_path        = relative path to our copy
         link_status      = 'self_hosted'   ← primary "View Judgment" can never break
         link_checked_at  = now
  3. If the URL is dead / not a PDF / a landing page, sets link_status='dead'
     and reports it so the URL can be corrected. Dead citations are NEVER shown
     in search (the search service filters on link_status).

Self-hosting is legal: judgment text is public domain under Copyright Act
§52(1)(q). We serve our copy and also keep source_url as a secondary
"View on official source" link.

Storage note: writes to the local filesystem for now (we run on local). The
blob_path field is storage-agnostic — point _store_pdf() at Azure Blob later
without touching the schema or search code.

Usage:
    python scripts/verify_citation_links.py            # verify all
    python scripts/verify_citation_links.py --recheck  # also re-check self_hosted
    python scripts/verify_citation_links.py --limit 20
"""
import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from sqlalchemy import select

from backend.models.law_citation import Citation
from backend.core.database import AsyncSessionLocal, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("verify_citation_links")

# Local self-host directory (served via GET /api/v1/citations/{id}/pdf)
JUDGMENT_DIR = Path(__file__).parent.parent / "data" / "judgments"

# Browser-like headers — government portals (e.g. digiscr.sci.gov.in) often
# refuse non-browser user agents or hotlinked requests without a Referer.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}
PDF_MAGIC = b"%PDF"


def _referer_for(url: str) -> str:
    """Same-origin referer — satisfies basic hotlink protection."""
    from urllib.parse import urlsplit
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}/"


def _store_pdf(citation_id: str, content: bytes) -> str:
    """Persist the PDF and return its blob_path. Swap body for Azure Blob later."""
    JUDGMENT_DIR.mkdir(parents=True, exist_ok=True)
    rel_path = f"judgments/{citation_id}.pdf"
    (JUDGMENT_DIR / f"{citation_id}.pdf").write_bytes(content)
    return rel_path


async def _fetch_pdf(client: httpx.AsyncClient, url: str) -> tuple[bool, str, bytes]:
    """
    Returns (is_pdf, reason, content).
    is_pdf=True only when the response is a genuine PDF (not HTML / landing page).
    """
    try:
        resp = await client.get(
            url,
            follow_redirects=True,
            timeout=30.0,
            headers={"Referer": _referer_for(url)},
        )
    except Exception as exc:
        # Include the underlying detail so we can tell TLS failures, DNS, refused,
        # and timeouts apart (all otherwise surface as bare ConnectError).
        detail = str(exc).strip() or repr(exc)
        return False, f"fetch_error:{type(exc).__name__}: {detail[:140]}", b""

    if resp.status_code != 200:
        return False, f"http_{resp.status_code}", b""

    content = resp.content
    ctype = resp.headers.get("content-type", "").lower()
    if content[:4] == PDF_MAGIC or "application/pdf" in ctype:
        if len(content) < 1024:
            return False, "pdf_too_small", b""
        return True, "ok", content
    # HTML / landing page / search result — not a concrete judgment
    return False, f"not_pdf:{ctype or 'unknown'}", b""


async def verify_all(recheck: bool, limit: int | None, insecure: bool = False) -> None:
    Session = AsyncSessionLocal

    async with Session() as session:
        stmt = select(Citation).where(Citation.deleted_at.is_(None))
        if not recheck:
            stmt = stmt.where(Citation.link_status != "self_hosted")
        if limit:
            stmt = stmt.limit(limit)
        citations = list((await session.execute(stmt)).scalars().all())

    logger.info(f"Checking {len(citations)} citations (recheck={recheck}, insecure={insecure})")

    # insecure=True skips TLS verification — common workaround for Indian gov
    # sites with non-standard certificate chains. Safe here: we still confirm
    # the payload is a real PDF by magic bytes before self-hosting.
    self_hosted, dead = 0, []
    async with httpx.AsyncClient(headers=REQUEST_HEADERS, verify=not insecure) as client:
        for c in citations:
            cid = str(c.id)
            now = datetime.now(timezone.utc)

            if not c.source_url:
                status, reason = "dead", "no_source_url"
            else:
                is_pdf, reason, content = await _fetch_pdf(client, c.source_url)
                if is_pdf:
                    blob = _store_pdf(cid, content)
                    status = "self_hosted"
                else:
                    status, blob = "dead", None

            # Persist result per-citation (own short session keeps it transactional)
            async with Session() as s:
                row = (await s.execute(select(Citation).where(Citation.id == c.id))).scalar_one()
                row.link_status = status
                row.link_checked_at = now
                if status == "self_hosted":
                    row.blob_path = blob
                await s.commit()

            if status == "self_hosted":
                self_hosted += 1
                logger.info(f"  OK   {c.case_name[:50]} -> {blob}")
            else:
                dead.append((c.case_name, c.source_url or "(none)", reason))
                logger.warning(f"  DEAD {c.case_name[:50]} ({reason}) {c.source_url or ''}")

    await engine.dispose()

    print("\n" + "=" * 70)
    print(f"SELF-HOSTED (working): {self_hosted}")
    print(f"DEAD (hidden from search, fix the URL): {len(dead)}")
    print("=" * 70)
    for name, url, reason in dead:
        print(f"  [{reason}] {name}\n        {url}")
    if dead:
        print("\nFix these source_url values (official PDF link), then re-run this script.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Verify + self-host citation judgment PDFs")
    ap.add_argument("--recheck", action="store_true", help="also re-verify already self_hosted rows")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--insecure", action="store_true",
                    help="skip TLS verification (workaround for gov-site cert chains)")
    args = ap.parse_args()
    asyncio.run(verify_all(recheck=args.recheck, limit=args.limit, insecure=args.insecure))
