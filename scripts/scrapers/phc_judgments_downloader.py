"""
P&H High Court Judgment Downloader
===================================
Downloads all judgments from the Punjab & Haryana High Court for a given
date range via their internal API (reverse-engineered from new.phhc.gov.in).

API:    https://livedb9010.phhc.gov.in/public/judgments/free-text-search
PDFs:   https://livedb9010.phhc.gov.in/public/judgments/order-pdf?...

Usage:
  # Download all June 2026 judgments
  python scripts/scrapers/phc_judgments_downloader.py --from 2026-06-01 --to 2026-06-21

  # Dry run — list only, no download
  python scripts/scrapers/phc_judgments_downloader.py --from 2026-06-01 --to 2026-06-21 --dry-run

  # Custom output directory
  python scripts/scrapers/phc_judgments_downloader.py --from 2026-06-01 --to 2026-06-21 --out data/judgments/phc

Output structure:
  data/judgments/phc/
    metadata.jsonl          ← one JSON record per judgment (for DB import)
    CRWP_7212_2026_2026-06-19.pdf
    CWP_1234_2026_2026-06-01.pdf
    ...
"""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

_API_BASE = "https://livedb9010.phhc.gov.in"
_SEARCH_URL = f"{_API_BASE}/public/judgments/free-text-search"
_PAGE_SIZE = 50  # API supports up to 50 per page

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://new.phhc.gov.in",
    "Referer": "https://new.phhc.gov.in/",
}


async def fetch_page(
    client: httpx.AsyncClient,
    from_date: str,
    to_date: str,
    skip: int,
) -> Dict[str, Any]:
    r = await client.get(
        _SEARCH_URL,
        params={
            "from_date": from_date,
            "to_date": to_date,
            "skip": str(skip),
            "limit": str(_PAGE_SIZE),
        },
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()


async def fetch_all_metadata(
    from_date: str,
    to_date: str,
    client: httpx.AsyncClient,
) -> List[Dict[str, Any]]:
    """Fetch all judgment metadata pages."""
    print(f"Fetching judgment list for {from_date} to {to_date} ...")

    first = await fetch_page(client, from_date, to_date, 0)
    total = int(first.get("total", 0))
    items = first.get("data", [])

    print(f"  Total judgments: {total}")
    if total == 0:
        return []

    # Fetch remaining pages
    pages = (total - len(items) + _PAGE_SIZE - 1) // _PAGE_SIZE
    for i in range(1, pages + 1):
        skip = i * _PAGE_SIZE
        page = await fetch_page(client, from_date, to_date, skip)
        batch = page.get("data", [])
        if not batch:
            break
        items.extend(batch)
        print(f"  Page {i+1}/{pages+1}: {len(items)}/{total} fetched", end="\r")
        await asyncio.sleep(0.3)

    print(f"\n  Metadata fetched: {len(items)} records")
    return items


def safe_filename(item: Dict[str, Any]) -> str:
    ct = (item.get("case_type") or "UNK").replace("/", "-").replace(" ", "_")
    cn = str(item.get("case_no") or "0")
    cy = str(item.get("case_year") or "0")
    od = (item.get("order_date") or "")[:10]  # YYYY-MM-DD
    return f"{ct}_{cn}_{cy}_{od}.pdf"


async def download_pdf(
    client: httpx.AsyncClient,
    url: str,
    dest: Path,
) -> bool:
    """Download a single PDF. Returns True on success."""
    try:
        async with client.stream("GET", url, timeout=60.0) as r:
            if r.status_code == 404:
                return False
            r.raise_for_status()
            content_type = r.headers.get("content-type", "")
            if "pdf" not in content_type and "octet" not in content_type:
                # Some errors come back as HTML 200
                body = await r.aread()
                if b"<html" in body[:100].lower():
                    return False
                dest.write_bytes(body)
                return True
            with open(dest, "wb") as f:
                async for chunk in r.aiter_bytes(chunk_size=65536):
                    f.write(chunk)
        return True
    except (httpx.HTTPError, OSError):
        return False


async def run(
    from_date: str,
    to_date: str,
    out_dir: Path,
    dry_run: bool = False,
    delay: float = 0.5,
    resume: bool = True,
):
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = out_dir / "metadata.jsonl"

    async with httpx.AsyncClient(
        headers=_HEADERS,
        verify=False,
        follow_redirects=True,
    ) as client:
        items = await fetch_all_metadata(from_date, to_date, client)

    if not items:
        print("No judgments found.")
        return

    # Filter out restricted ones
    public = [x for x in items if x.get("cat_restricted") != "Y"]
    restricted = len(items) - len(public)
    print(f"  Public: {len(public)}  |  Restricted (skipped): {restricted}")

    if dry_run:
        print("\n[DRY RUN] First 5 entries:")
        for item in public[:5]:
            print(f"  {safe_filename(item)}  <- {item.get('order_document_url', '')[:80]}")
        print(f"\nWould download {len(public)} PDFs to {out_dir}")
        return

    # Write/append metadata
    existing_files: set = set()
    if resume:
        existing_files = {p.name for p in out_dir.glob("*.pdf")}
        if existing_files:
            print(f"  Resuming — {len(existing_files)} already downloaded, skipping them")

    downloaded = 0
    skipped = 0
    failed: List[str] = []

    async with httpx.AsyncClient(
        headers=_HEADERS,
        verify=False,
        follow_redirects=True,
    ) as client:
        meta_file = open(metadata_path, "a", encoding="utf-8")
        try:
            for idx, item in enumerate(public, 1):
                fname = safe_filename(item)
                dest = out_dir / fname

                if resume and fname in existing_files:
                    skipped += 1
                    continue

                url = item.get("order_document_url") or item.get("order")
                if not url:
                    failed.append(fname)
                    continue

                ok = await download_pdf(client, url, dest)
                if ok:
                    downloaded += 1
                    # Write metadata record
                    meta_file.write(json.dumps({
                        "filename": fname,
                        "case_type": item.get("case_type"),
                        "case_no": item.get("case_no"),
                        "case_year": item.get("case_year"),
                        "petitioner": item.get("pet_name"),
                        "respondent": item.get("res_name"),
                        "order_date": (item.get("order_date") or "")[:10],
                        "source_url": url,
                        "court": "P&H HC",
                    }) + "\n")
                    meta_file.flush()
                else:
                    failed.append(fname)

                if idx % 10 == 0 or idx == len(public):
                    print(
                        f"  [{idx}/{len(public)}] downloaded={downloaded} "
                        f"skipped={skipped} failed={len(failed)}",
                        end="\r",
                    )

                await asyncio.sleep(delay)

        finally:
            meta_file.close()

    print(f"\n\nDone.")
    print(f"  Downloaded : {downloaded}")
    print(f"  Skipped    : {skipped}")
    print(f"  Failed     : {len(failed)}")
    if failed:
        print(f"  Failed files (first 10):")
        for f in failed[:10]:
            print(f"    {f}")
    print(f"  Metadata   : {metadata_path}")
    print(f"  Output dir : {out_dir}")


def main():
    parser = argparse.ArgumentParser(description="P&H HC Judgment Downloader")
    parser.add_argument("--from", dest="from_date", required=True,
                        help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", required=True,
                        help="End date YYYY-MM-DD")
    parser.add_argument("--out", default="data/judgments/phc",
                        help="Output directory (default: data/judgments/phc)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List only, don't download")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Seconds between PDF downloads (default: 0.5)")
    parser.add_argument("--no-resume", action="store_true",
                        help="Re-download already downloaded files")
    args = parser.parse_args()

    asyncio.run(run(
        from_date=args.from_date,
        to_date=args.to_date,
        out_dir=Path(args.out),
        dry_run=args.dry_run,
        delay=args.delay,
        resume=not args.no_resume,
    ))


if __name__ == "__main__":
    main()
