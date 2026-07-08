#!/usr/bin/env python3
"""
Import real local judgment PDFs as self-hosted citations (LOCAL DEV ONLY).

Government judgment portals (digiscr.sci.gov.in, etc.) are unreachable from this
dev network, so we cannot fetch + self-host them here. But we already have REAL,
public-domain Punjab/Haryana judgments on disk. This imports those directly:
copies each PDF into data/judgments/<id>.pdf and creates a citation with
link_status='self_hosted' — proving the full search -> View Judgment -> our-copy
loop locally, with no external connectivity.

Real gov-site ingestion (scraper / verify_citation_links.py) runs on the cloud
server later, where those portals are reachable.

All metadata below was verified from the actual PDFs during extraction testing.
Add more entries as you confirm metadata — never guess (LAUNCH QUALITY MANDATE).

Usage:  python scripts/import_local_judgments.py
"""
import asyncio
import logging
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_

from backend.models.law_citation import Citation
from backend.core.database import AsyncSessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("import_local_judgments")

PDF_SRC_DIR = Path(r"D:\NISHANT\test-pdfs")
JUDGMENT_DIR = Path(__file__).parent.parent / "data" / "judgments"

# Real judgments on disk, with metadata verified from the documents themselves.
LOCAL_JUDGMENTS = [
    {
        "file": "CWP-No.-39633-OF-2025-(MANIK-KHURANA-VERSUS-THE-CENTRAL-ADMINISTRATIVE-TRIBUNAL-AND-OTHERS).pdf",
        "citation_key": "PH-CWP-39633-2025",
        "case_name": "Manik Khurana v Central Administrative Tribunal, Chandigarh",
        "petitioner": "Manik Khurana",
        "respondent": "Central Administrative Tribunal, Chandigarh Bench and others",
        "court": "Punjab and Haryana High Court",
        "year": 2025,
        "primary_citation": "CWP No. 39633 of 2025",
        "matter_type": "service",
        "outcome": "dismissed",
        "official_source": "P&H HC",
        "summary": "Writ petition challenging CAT's refusal of interim relief against UPSC's "
                   "enhanced-experience shortlisting for Assistant District Attorney interviews; dismissed.",
    },
    {
        "file": "Jassar display_pdf.pdf",
        "citation_key": "PB-DC-CA-216-2020",
        "case_name": "Anubhav Walia v Col. R.P.S. Brar",
        "petitioner": "Anubhav Walia",
        "respondent": "Col. R.P.S. Brar and another",
        "court": "Court of Additional District Judge, Patiala",
        "year": 2025,
        "primary_citation": "CA CIS No. 216 of 2020",
        "matter_type": "civil",
        "outcome": "dismissed",
        "official_source": "Punjab district court",
        "summary": "First appeal in a possession/injunction suit over 525 sq yd at Stadium Road, Patiala; "
                   "dismissed for failure to prove the suit property's identity and illegal possession.",
    },
    {
        "file": "PBPT010007012024_22_2026-02-27.pdf",
        "citation_key": "PB-DC-CA-48-2024",
        "case_name": "Harpal Singh v Pepsu Road Transport Corporation",
        "petitioner": "Harpal Singh",
        "respondent": "Pepsu Road Transport Corporation, through its Managing Director, Patiala",
        "court": "Court of District Judge, Patiala",
        "year": 2026,
        "primary_citation": "CA No. 48 of 2024",
        "matter_type": "service",
        "outcome": "allowed",
        "official_source": "Punjab district court",
        "summary": "Service appeal; punishment order set aside because the Corporation had earlier taken "
                   "the inconsistent stand before the MACT that the driver was not negligent. Appeal allowed.",
    },
]


async def main() -> None:
    JUDGMENT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    imported, skipped, missing = 0, 0, []

    async with AsyncSessionLocal() as session:
        for j in LOCAL_JUDGMENTS:
            src = PDF_SRC_DIR / j["file"]
            if not src.exists():
                missing.append(j["file"])
                logger.warning(f"  MISSING file: {src}")
                continue

            existing = (await session.execute(
                select(Citation).where(and_(
                    Citation.citation_key == j["citation_key"],
                    Citation.deleted_at.is_(None),
                ))
            )).scalar_one_or_none()

            citation = existing or Citation(citation_key=j["citation_key"])
            citation.case_name = j["case_name"]
            citation.petitioner = j["petitioner"]
            citation.respondent = j["respondent"]
            citation.court = j["court"]
            citation.year = j["year"]
            citation.primary_citation = j["primary_citation"]
            citation.matter_type = j["matter_type"]
            citation.outcome = j["outcome"]
            citation.official_source = j["official_source"]
            citation.summary = j["summary"]
            citation.source_url = None            # no working official URL on this network
            citation.link_status = "self_hosted"  # primary link = our copy below
            citation.link_checked_at = now
            if not existing:
                session.add(citation)

            await session.flush()  # assigns citation.id for new rows

            dest = JUDGMENT_DIR / f"{citation.id}.pdf"
            shutil.copyfile(src, dest)
            citation.blob_path = f"judgments/{citation.id}.pdf"

            imported += 1
            logger.info(f"  {'UPDATED' if existing else 'IMPORTED'}: {j['case_name']} -> {dest.name}")

        await session.commit()

    await engine.dispose()

    print("\n" + "=" * 64)
    print(f"Self-hosted local judgments: {imported}")
    if missing:
        print(f"Missing files (skipped): {len(missing)}")
        for m in missing:
            print(f"  - {m}")
    print("=" * 64)
    print("These now appear in search with a working 'View Judgment' link.")


if __name__ == "__main__":
    asyncio.run(main())
