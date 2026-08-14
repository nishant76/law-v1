"""
Extract the special-act provisions the Strategic Filing Drafter must never get
wrong, verbatim, from the OFFICIAL India Code bare-act PDFs.

Why this exists
---------------
docs/drafting_correctness_audit.md, section 4, lists the "landmines": statutory
bars and mandatory pleadings where a wrong or missing answer voids the filing
(NDPS s.37, PMLA s.45, UAPA s.43D(5), s.12A Commercial Courts, s.80 CPC,
s.69 Partnership, s.14 HMA, s.142 NI). Before this script those lived only in
the model's memory — and a real NDPS bail draft was caught omitting s.37, the
quantity classification, and the Special Court entirely.

Method — NOTHING is written from memory
---------------------------------------
  * Each act PDF is downloaded from its India Code bitstream URL (public-domain
    statute text, Copyright Act s.52(1)(q)).
  * Text is taken from the PDF's own text layer via pdfplumber. Any act whose
    PDF has no usable text layer is REPORTED AND SKIPPED, never hand-typed.
  * For each wanted provision a start marker and an end marker (the heading of
    the following section) are located in the extracted text; the slice between
    them is the verbatim provision. If either marker is not found the provision
    is recorded with verified:false and an empty quote — the reading service
    drops unverified rows, so an extraction failure degrades to silence rather
    than to a guess.
  * Marginal footnote lines (amendment history, e.g. "1. Subs. by Act 9 of
    2001, s. 16, ...") and bare page numbers are stripped: they interleave with
    the statutory text in these PDFs and are not part of the provision.

Run:
    python3 scripts/extract_special_acts.py data/special_acts/special_acts.json

Re-runnable and deterministic. Network access required (downloads are cached in
data/special_acts/source/).
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "data" / "special_acts" / "source"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# --------------------------------------------------------------------------
# The acts, and the provisions wanted from each.
#
# `start` is matched against the extracted text. `end` is the marker at which
# the provision stops (normally the next section's heading). Both are literal
# substrings — no regex — so a marker either matches the statute's own words or
# the provision is flagged unverified.
# --------------------------------------------------------------------------
ACTS: List[Dict] = [
    {
        "act_id": "ndps_1985",
        "act": "Narcotic Drugs and Psychotropic Substances Act, 1985",
        "act_number": "Act 61 of 1985",
        "handle": "https://www.indiacode.nic.in/handle/123456789/1791",
        "pdf_url": "https://www.indiacode.nic.in/bitstream/123456789/1791/5/a1985-61.pdf",
        "filename": "ndps_1985.pdf",
        "provisions": [
            {
                "section": "37",
                "label": "Offences to be cognizable and non-bailable",
                "start": "37. Offences to be cognizable and non-bailable.—",
                "end": "38. Offences by companies.—",
            },
            {
                "section": "36A",
                "label": "Offences triable by Special Courts",
                "start": "36A. Offences triable by Special Courts.—",
                "end": "36B. Appeal and revision.—",
            },
            {
                "section": "2(viia)",
                "label": "Definition — commercial quantity",
                "start": "(viia) “commercial quantity”",
                "end": "(viib) “controlled delivery”",
            },
            {
                "section": "2(xxiiia)",
                "label": "Definition — small quantity",
                "start": "(xxiiia) “small quantity”",
                "end": "(xxiv) “to import inter-State”",
            },
        ],
    },
    {
        "act_id": "pmla_2002",
        "act": "Prevention of Money-Laundering Act, 2002",
        "act_number": "Act 15 of 2003",
        "handle": "https://www.indiacode.nic.in/handle/123456789/2036",
        "pdf_url": "https://www.indiacode.nic.in/bitstream/123456789/2036/5/A2003-15.pdf",
        "filename": "pmla_2002.pdf",
        "provisions": [
            {
                "section": "45",
                "label": "Offences to be cognizable and non-bailable",
                "start": "45. Offences to be cognizable and non-bailable.—",
                "end": "46. Application of Code of Criminal Procedure, 1973 to proceedings before",
            },
        ],
    },
    {
        "act_id": "uapa_1967",
        "act": "Unlawful Activities (Prevention) Act, 1967",
        "act_number": "Act 37 of 1967",
        "handle": "https://www.indiacode.nic.in/handle/123456789/1470",
        "pdf_url": "https://www.indiacode.nic.in/bitstream/123456789/1470/3/A1967-37.pdf",
        "filename": "uapa_1967.pdf",
        "provisions": [
            {
                "section": "43D",
                "label": "Modified application of certain provisions of the Code",
                "start": "43D. Modified application of certain provisions of the Code.—",
                "end": "43E. Presumption as to offence under section 15.—",
            },
        ],
    },
    {
        "act_id": "ni_1881",
        "act": "Negotiable Instruments Act, 1881",
        "act_number": "Act 26 of 1881",
        "handle": "https://www.indiacode.nic.in/handle/123456789/2189",
        "pdf_url": "https://www.indiacode.nic.in/bitstream/123456789/2189/1/a1881-26.pdf",
        "filename": "ni_1881.pdf",
        "provisions": [
            {
                "section": "138",
                "label": "Dishonour of cheque for insufficiency, etc., of funds in the account",
                "start": "138. Dishonour of cheque for insufficiency, etc., of funds in the account.—",
                "end": "139. Presumption in favour of holder.—",
            },
            {
                "section": "142",
                "label": "Cognizance of offences",
                "start": "142. Cognizance of offences.—",
                "end": "143. Power of Court to try cases summarily.—",
            },
        ],
    },
    {
        "act_id": "cca_2015",
        "act": "Commercial Courts Act, 2015",
        "act_number": "Act 4 of 2016",
        "handle": "https://www.indiacode.nic.in/handle/123456789/2156",
        "pdf_url": "https://www.indiacode.nic.in/bitstream/123456789/2156/1/a2016-04.pdf",
        "filename": "cca_2015.pdf",
        "provisions": [
            {
                "section": "12A",
                "label": "Pre-Institution Mediation and Settlement",
                "start": "12A. Pre-Institution Mediation and Settlement—",
                "end": "13. Appeals from decrees of Commercial Courts and Commercial Divisions.—",
            },
        ],
    },
    {
        "act_id": "cpc_1908",
        "act": "Code of Civil Procedure, 1908",
        "act_number": "Act 5 of 1908",
        "handle": "https://www.indiacode.nic.in/handle/123456789/2191",
        "pdf_url": (
            "https://www.indiacode.nic.in/bitstream/123456789/11087/1/"
            "the_code_of_civil_procedure,_1908.pdf"
        ),
        "filename": "cpc_1908.pdf",
        "provisions": [
            {
                "section": "80",
                "label": "Notice",
                "start": "80. Notice—",
                "end": "81. Exemption from arrest and personal appearance—",
            },
        ],
    },
    {
        "act_id": "partnership_1932",
        "act": "Indian Partnership Act, 1932",
        "act_number": "Act 9 of 1932",
        "handle": "https://www.indiacode.nic.in/handle/123456789/2394",
        "pdf_url": "https://www.indiacode.nic.in/bitstream/123456789/2394/1/aA1932-9.pdf",
        "filename": "partnership_1932.pdf",
        "provisions": [
            {
                "section": "69",
                "label": "Effect of non-registration",
                "start": "69. Effect of non-registration.—",
                "end": "70. Penalty for furnishing false particulars.—",
            },
        ],
    },
    {
        "act_id": "hma_1955",
        "act": "Hindu Marriage Act, 1955",
        "act_number": "Act 25 of 1955",
        "handle": "https://www.indiacode.nic.in/handle/123456789/1560",
        "pdf_url": "https://www.indiacode.nic.in/bitstream/123456789/1560/1/A1955-25Eng.pdf",
        "filename": "hma_1955.pdf",
        "provisions": [
            {
                "section": "14",
                "label": "No petition for divorce to be presented within one year of marriage",
                "start": "14. No petition for divorce to be presented within one year of marriage.—",
                "end": "15. Divorced persons when may marry again.—",
            },
        ],
    },
]

# Footnote / page-furniture lines that interleave with statutory text in the
# India Code PDFs. These are NOT part of the provision.
# NOTE: no trailing \b — the alternatives ending in "." (Subs., Ins., Rep.)
# are followed by a space, and "." → " " is not a word boundary, so a \b here
# would silently match nothing and leak amendment footnotes into the quote.
_FOOTNOTE_RE = re.compile(
    r"^\s*\d+\.\s+(Subs\.|Ins\.|Omitted\b|Rep\.|Added\b|Renumbered\b|"
    r"Certain words\b|The words\b|Cl\.|Sec\.|Vide\b|Now\b|Earlier\b|Substituted\b)",
    re.IGNORECASE,
)
_PAGE_NUM_RE = re.compile(r"^\s*\d{1,3}\s*$")


def download(url: str, dest: Path) -> bool:
    """Fetch a PDF into `dest` unless already cached. Returns success."""
    if dest.exists() and dest.stat().st_size > 10_000:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
    except Exception as exc:  # noqa: BLE001 — report, never fabricate
        print(f"  ! download failed: {exc}", file=sys.stderr)
        return False
    if not data.startswith(b"%PDF"):
        print(f"  ! not a PDF ({len(data)} bytes) — skipping", file=sys.stderr)
        return False
    dest.write_bytes(data)
    return True


def pdf_text(path: Path) -> str:
    """Full text layer of a PDF, footnotes and page numbers removed."""
    with pdfplumber.open(path) as pdf:
        pages = [(p.extract_text() or "") for p in pdf.pages]
    lines: List[str] = []
    for page in pages:
        for line in page.split("\n"):
            if _FOOTNOTE_RE.match(line) or _PAGE_NUM_RE.match(line):
                continue
            lines.append(line)
    return "\n".join(lines)


def normalise(text: str) -> str:
    """Collapse the PDF's hard line wrapping into readable paragraphs."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def extract_provision(text: str, start: str, end: str) -> Optional[str]:
    """The verbatim slice between two literal markers, or None."""
    i = text.find(start)
    if i < 0:
        return None
    j = text.find(end, i + len(start))
    if j < 0:
        return None
    return normalise(text[i:j])


def main(out_path: str) -> int:
    records: List[Dict] = []
    failures: List[str] = []

    for act in ACTS:
        print(f"* {act['act']}")
        pdf_path = SOURCE_DIR / act["filename"]
        if not download(act["pdf_url"], pdf_path):
            failures.append(f"{act['act_id']}: download failed")
            for prov in act["provisions"]:
                records.append(_unverified(act, prov, "source PDF unavailable"))
            continue

        try:
            text = pdf_text(pdf_path)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! parse failed: {exc}", file=sys.stderr)
            failures.append(f"{act['act_id']}: parse failed")
            for prov in act["provisions"]:
                records.append(_unverified(act, prov, "PDF text layer unreadable"))
            continue

        for prov in act["provisions"]:
            quote = extract_provision(text, prov["start"], prov["end"])
            if quote is None:
                print(f"  ! s.{prov['section']}: markers not found", file=sys.stderr)
                failures.append(f"{act['act_id']} s.{prov['section']}: markers not found")
                records.append(_unverified(act, prov, "provision markers not found in PDF"))
                continue
            print(f"  - s.{prov['section']}: {len(quote)} chars")
            records.append({
                "act_id": act["act_id"],
                "act": act["act"],
                "act_number": act["act_number"],
                "section": prov["section"],
                "label": prov["label"],
                "text": quote,
                "source_url": act["pdf_url"],
                "source_handle": act["handle"],
                "retrieved_date": date.today().isoformat(),
                "verified": True,
            })

    payload = {
        "manifest": {
            "title": "Special-act statutory bars and mandatory pleadings — verbatim provisions",
            "purpose": (
                "Ground the Strategic Filing Drafter on the statutory landmines listed in "
                "docs/drafting_correctness_audit.md section 4, so section numbers and bar "
                "conditions come from the bare act rather than from model memory."
            ),
            "source": "India Code (indiacode.nic.in) official bare-act PDFs",
            "licence_note": (
                "Statute text is public domain under the Copyright Act s.52(1)(q). "
                "No commercial commentary is used."
            ),
            "built_by": "scripts/extract_special_acts.py",
            "built_date": date.today().isoformat(),
            "total_records": len(records),
            "verified_records": sum(1 for r in records if r["verified"]),
            "unverified_records": sum(1 for r in records if not r["verified"]),
            "extraction_failures": failures,
            "quantity_table_status": (
                "NOT INCLUDED. The NDPS small/commercial quantity table (S.O. 1055(E), "
                "19-10-2001) is published only as a scanned image PDF at "
                "https://www.cbn.gov.in/pdf/qtynotif.pdf; OCR of that scan drops and "
                "corrupts values (e.g. heroin's small-quantity column is lost entirely). "
                "Per the launch-quality mandate no quantity is guessed: "
                "special_acts_service instead REQUIRES the drafter to obtain the seized "
                "quantity from the lawyer and to flag the classification as unverified. "
                "Replace this with a real extraction once a text-layer or machine-readable "
                "gazette copy is obtained."
            ),
        },
        "provisions": records,
    }

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"\nWrote {out} — {len(records)} records "
          f"({payload['manifest']['verified_records']} verified)")
    if failures:
        print("FAILURES (recorded as unverified, never guessed):")
        for f in failures:
            print(f"  - {f}")
    return 0


def _unverified(act: Dict, prov: Dict, reason: str) -> Dict:
    """A provision we could not extract. Empty text; the service will skip it."""
    return {
        "act_id": act["act_id"],
        "act": act["act"],
        "act_number": act["act_number"],
        "section": prov["section"],
        "label": prov["label"],
        "text": "",
        "source_url": act["pdf_url"],
        "source_handle": act["handle"],
        "retrieved_date": date.today().isoformat(),
        "verified": False,
        "unverified_reason": reason,
    }


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else str(
        REPO_ROOT / "data" / "special_acts" / "special_acts.json"
    )
    raise SystemExit(main(target))
