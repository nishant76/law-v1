"""
Import P&H HC judgments into the citations DB so they appear in search.

Reads data/judgments/phc/metadata.jsonl, extracts text from each PDF using
pypdf, and upserts Citation records with link_status='self_hosted'.

Search works immediately after import — no embedding or Azure AI Search needed.
The search service uses PostgreSQL FTS + ILIKE on case_name, court, and
judgment_text, all of which we populate here.

Usage:
  python scripts/import_phc_judgments.py
  python scripts/import_phc_judgments.py --limit 50          # test with 50 first
  python scripts/import_phc_judgments.py --dry-run           # parse only, no DB writes
  python scripts/import_phc_judgments.py --skip-text         # skip PDF extraction (faster)
"""
import argparse
import asyncio
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_

from backend.core.database import AsyncSessionLocal, engine
from backend.models.law_citation import Citation

PDF_DIR     = Path("data/judgments/phc")
META_FILE   = PDF_DIR / "metadata.jsonl"
DEST_DIR    = Path("data/judgments")   # where Citation.blob_path points


def extract_text(pdf_path: Path, max_chars: int = 50_000) -> str:
    """Extract text from PDF using pypdf. Returns empty string on failure."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        parts = []
        for page in reader.pages:
            text = page.extract_text() or ""
            parts.append(text)
            if sum(len(p) for p in parts) >= max_chars:
                break
        return "\n".join(parts)[:max_chars]
    except Exception as e:
        return ""


def make_citation_key(row: dict) -> str:
    """Stable unique key for a judgment row."""
    return f"PHC-{row['case_type']}-{row['case_no']}-{row['case_year']}-{row['order_date'].replace('-', '')}"


def make_case_name(row: dict) -> str:
    pet = (row.get("petitioner") or "").strip().title()
    res = (row.get("respondent") or "").strip().title()
    if pet and res:
        return f"{pet} v. {res}"
    return pet or res or f"{row['case_type']} {row['case_no']}/{row['case_year']}"


def parse_date(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def run(limit: int, dry_run: bool, skip_text: bool):
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    # Load metadata
    rows = []
    with open(META_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    if limit:
        rows = rows[:limit]

    print(f"Records to process: {len(rows)}")
    if dry_run:
        print("[DRY RUN] — no DB writes")
        for r in rows[:5]:
            print(f"  {make_citation_key(r)}  |  {make_case_name(r)}")
        print(f"  ... and {len(rows)-5} more")
        return

    imported = updated = skipped = failed = 0
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        for i, row in enumerate(rows, 1):
            try:
                citation_key = make_citation_key(row)
                src_pdf = PDF_DIR / row["filename"]

                if not src_pdf.exists():
                    print(f"  [{i}] MISSING PDF: {row['filename']}")
                    failed += 1
                    continue

                # Check if already imported
                existing = (await session.execute(
                    select(Citation).where(
                        and_(Citation.citation_key == citation_key, Citation.deleted_at.is_(None))
                    )
                )).scalar_one_or_none()

                c = existing or Citation()
                c.citation_key   = citation_key
                c.case_name      = make_case_name(row)
                c.court          = "Punjab and Haryana High Court"
                c.year           = int(row["case_year"])
                c.petitioner     = (row.get("petitioner") or "").strip().title() or None
                c.respondent     = (row.get("respondent") or "").strip().title() or None
                c.judgment_date  = parse_date(row["order_date"])
                c.primary_citation = f"{row['case_type']} No. {row['case_no']} of {row['case_year']}"
                c.official_source  = "P&H HC"
                c.source_url       = row.get("source_url")
                c.link_status      = "self_hosted"
                c.link_checked_at  = now
                c.scraped_at       = now
                c.matter_type      = _guess_matter_type(row["case_type"])
                c.subject_tags     = row["case_type"]  # e.g. "CRWP", "CWP", "CRM-M"

                # Extract PDF text for full-text search
                if not skip_text:
                    c.judgment_text = extract_text(src_pdf) or None

                if not existing:
                    session.add(c)

                await session.flush()  # get c.id for new rows

                # Copy PDF to dest with UUID filename (blob_path pattern)
                dest_pdf = DEST_DIR / f"{c.id}.pdf"
                if not dest_pdf.exists():
                    shutil.copy2(src_pdf, dest_pdf)
                c.blob_path = f"judgments/{c.id}.pdf"

                if existing:
                    updated += 1
                else:
                    imported += 1

                if i % 50 == 0 or i == len(rows):
                    await session.commit()
                    print(f"  [{i}/{len(rows)}] imported={imported} updated={updated} failed={failed}", end="\r")

            except Exception as e:
                print(f"\n  [{i}] ERROR {row.get('filename')}: {e}")
                failed += 1
                await session.rollback()

        await session.commit()

    await engine.dispose()

    print(f"\n\nDone.")
    print(f"  Imported : {imported}")
    print(f"  Updated  : {updated}")
    print(f"  Failed   : {failed}")
    print(f"  Total    : {imported + updated}")
    print(f"\nRun a search in the app — P&H HC June 2026 judgments are now live.")


def _guess_matter_type(case_type: str) -> str:
    """Map P&H HC case type codes to our matter_type taxonomy."""
    ct = case_type.upper()
    if ct in ("CRM-M", "CRM-A", "CRA", "CRMM", "CRMA"):
        return "criminal"
    if ct in ("CWP", "CRWP"):
        return "writ"
    if ct in ("RSA", "RFA", "FAO"):
        return "civil"
    if ct in ("ITA", "ITREF"):
        return "tax"
    if ct in ("MAT", "MATA"):
        return "matrimonial"
    if ct in ("EL", "ELA"):
        return "election"
    if ct in ("CO", "CP"):
        return "company"
    if ct in ("ARB", "ARB-P"):
        return "arbitration"
    return "civil"  # sensible default


def main():
    parser = argparse.ArgumentParser(description="Import P&H HC judgments into search DB")
    parser.add_argument("--limit", type=int, default=0, help="Max records (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no DB writes")
    parser.add_argument("--skip-text", action="store_true",
                        help="Skip PDF text extraction (imports metadata only, faster)")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.dry_run, args.skip_text))


if __name__ == "__main__":
    main()
