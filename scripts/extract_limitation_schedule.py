"""
Extract THE SCHEDULE (Periods of Limitation) of the Limitation Act, 1963 into
structured, per-row-traceable records.

Source PDF (government primary source, public-domain statute text):
  https://www.indiacode.nic.in/bitstream/123456789/1565/5/A1963-36.pdf
  ("THE SCHEDULE (PERIODS OF LIMITATION) [See sections 2(j) and 3]")

Why coordinates and not text lines
----------------------------------
The Schedule is a three-column table (Description of suit / Period of
limitation / Time from which period begins to run). Plain text extraction
interleaves the three columns line by line, which silently welds one article's
period onto another's description. So, exactly as scripts/extract_bnss_schedule.py
does, column x-boundaries are read from each page's own header rule rectangles
and every word is assigned to a column by its x-centre.

NOTHING is inferred from memory: each cell is the PDF's own text at its column
x-position. A row whose period cannot be parsed into a machine-comparable
duration keeps its verbatim text and is marked verified:false — the reading
service skips those rather than guessing a date.

Run:
  python3 scripts/extract_limitation_schedule.py data/limitation/limitation_schedule.json
Re-runnable and deterministic.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = REPO_ROOT / "data" / "limitation" / "source" / "limitation_1963.pdf"
SOURCE_URL = "https://www.indiacode.nic.in/bitstream/123456789/1565/5/A1963-36.pdf"

COL_NAMES = ["description", "period", "starts_from"]

# Identifies a Schedule page by its column header.
#
# "Period of limitation" is NOT usable for this: the three headers are laid out
# side by side, so extraction interleaves them as
# "Description of suit | Period of | Time from which ... \n limitation", and the
# phrase never appears contiguously. The first header survives intact, so match
# that — plus the Second/Third Division variant which says "application".
SCHEDULE_PAGE_RE = re.compile(
    r"Description\s+of\s+(suit|application)", re.IGNORECASE
)

# An article number opens a row: "1.", "21.", "113." — optionally with a letter.
ART_RE = re.compile(r"^(\d+[A-Za-z]?)\.?$")

# Division / Part headings inside the Schedule carry no article of their own.
# Checked against EVERY cell, not just the description: a heading is centred
# across the table, so its words land in whichever columns they overlap and
# would otherwise be welded onto the previous article's period.
# NOTE: this must NOT match on "period of limitation" or "time from which".
# Article 112's own text reads "When the period of limitation would begin to
# run...", so those phrases silently deleted a real article. The column header
# row is already excluded by its "Description of suit/application" cell.
HEADING_RE = re.compile(
    r"(FIRST|SECOND|THIRD)\s+DIVISION|PART\s+[IVXL]+\.?—|Description\s+of\s+(suit|application)"
    r"|^[IVXL]+—",
    re.IGNORECASE,
)

# Amendment footnotes sit at the foot of each page ("24. Subs. by Act 53 of
# 1964, s. 3 ..."). Their leading number looks exactly like an article number,
# so without this they are parsed as spurious articles.
FOOTNOTE_RE = re.compile(
    r"\b(Subs\.|Ins\.|Omitted|Rep\.|w\.e\.f\.|Added by|Renumbered)\b|\bby Act \d+ of \d{4}\b",
    re.IGNORECASE,
)

# Spelled-out durations used throughout the Schedule.
WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirty": 30, "sixty": 60, "ninety": 90,
}
PERIOD_RE = re.compile(
    r"\b(" + "|".join(WORD_NUMBERS) + r"|\d+)\s+(year|years|month|months|day|days)\b",
    re.IGNORECASE,
)


def page_dividers(page) -> Optional[List[float]]:
    """
    The two x-positions separating the Schedule's three columns, read from the
    page's own header rule.

    The rule is drawn as a run of wide spans (the cells) broken by very narrow
    rects (the separators). The separator centres ARE the column boundaries.
    Pages vary: some carry an extra separator because the article number sits in
    its own narrow gutter, so the DESCRIPTION|PERIOD and PERIOD|STARTS_FROM
    boundaries are the last two — the article gutter, where present, belongs
    with the description.
    """
    rules = [r for r in page.rects if (r["bottom"] - r["top"]) < 2]
    if not rules:
        return None
    tops = sorted({round(r["top"], 1) for r in rules})
    band = [r for r in rules if abs(r["top"] - tops[0]) < 1.0]
    separators = sorted(
        (r["x0"] + r["x1"]) / 2 for r in band if (r["x1"] - r["x0"]) < 1.5
    )
    if len(separators) < 2:
        return None
    return separators[-2:]


def extract_rows(pdf_path: Path) -> List[Dict]:
    rows: List[Dict] = []
    current: Optional[Dict] = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            # The column header wraps ("Period of / limitation") on some pages,
            # so this must tolerate the line break — a literal match silently
            # dropped a whole page of articles.
            if not SCHEDULE_PAGE_RE.search(text):
                continue

            # Column boundaries: derived per page from its own rules where
            # possible, else the boundaries observed on the Schedule pages.
            div = page_dividers(page)
            if div is None:
                # No readable header rule: skip rather than split on guessed
                # coordinates, which would silently mix columns.
                print(f"  ! page {page.page_number}: no column rule found — skipped",
                      file=sys.stderr)
                continue
            b_desc, b_period = div

            words = page.extract_words(use_text_flow=False)
            # Cluster into visual lines by y using a TOLERANCE, not fixed bucket
            # rounding: rounding puts two words 1.5pt apart into different
            # buckets depending on where the boundary falls, which silently
            # dropped the opening line of an article (Art. 65 lost its period
            # and half its description that way).
            line_groups: List[List[dict]] = []
            for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
                if line_groups and abs(w["top"] - line_groups[-1][0]["top"]) <= 2.5:
                    line_groups[-1].append(w)
                else:
                    line_groups.append([w])

            for group in line_groups:
                lws = sorted(group, key=lambda w: w["x0"])
                cells = {c: [] for c in COL_NAMES}
                for w in lws:
                    xc = (w["x0"] + w["x1"]) / 2
                    if xc < b_desc:
                        cells["description"].append(w["text"])
                    elif xc < b_period:
                        cells["period"].append(w["text"])
                    else:
                        cells["starts_from"].append(w["text"])

                desc = " ".join(cells["description"]).strip()
                per = " ".join(cells["period"]).strip()
                frm = " ".join(cells["starts_from"]).strip()
                if not (desc or per or frm):
                    continue
                joined = " ".join((desc, per, frm))
                if HEADING_RE.search(joined) or FOOTNOTE_RE.search(joined):
                    continue

                # A new article begins when the description opens with "N."
                first = desc.split(" ", 1)[0] if desc else ""
                m = ART_RE.match(first.rstrip("."))
                if m and first.endswith("."):
                    if current:
                        rows.append(current)
                    current = {
                        "article": m.group(1),
                        "description": desc[len(first):].strip(),
                        "period_text": per,
                        "starts_from": frm,
                    }
                elif current:
                    # Continuation line — append cell by cell.
                    if desc:
                        current["description"] += " " + desc
                    if per:
                        current["period_text"] += " " + per
                    if frm:
                        current["starts_from"] += " " + frm

    if current:
        rows.append(current)
    return rows


def parse_period(text: str) -> Optional[Dict]:
    """Turn 'Three years.' into a machine-comparable duration, or None."""
    if not text:
        return None
    m = PERIOD_RE.search(text)
    if not m:
        return None
    raw, unit = m.group(1).lower(), m.group(2).lower()
    n = WORD_NUMBERS.get(raw, None)
    if n is None:
        try:
            n = int(raw)
        except ValueError:
            return None
    unit = unit.rstrip("s")
    return {"value": n, "unit": unit}


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def tidy_period(text: str) -> str:
    """
    Trim the period cell to the statutory phrase.

    Centred Part/Division headings and footnote markers occasionally overlap
    this narrow column, leaving crumbs like "Three years. RELATING" or
    "Two years. 18". The duration itself parses correctly regardless, but the
    verbatim text is shown to a lawyer, so cut it at the end of the period
    sentence.
    """
    if not text:
        return text
    m = PERIOD_RE.search(text)
    if not m:
        return text
    end = m.end()
    tail = text[end:end + 1]
    return text[:end + (1 if tail == "." else 0)].strip()


def main(out_path: str) -> int:
    if not PDF_PATH.exists():
        print(f"Missing source PDF: {PDF_PATH}", file=sys.stderr)
        return 1

    raw = extract_rows(PDF_PATH)
    records: List[Dict] = []
    for r in raw:
        desc, per, frm = clean(r["description"]), tidy_period(clean(r["period_text"])), clean(r["starts_from"])
        duration = parse_period(per)
        # A row is only usable for computing a date when we could read BOTH a
        # duration and the event it runs from. Otherwise it is kept verbatim
        # and flagged, never guessed.
        verified = bool(duration and desc and frm)
        records.append({
            "article": r["article"],
            "description": desc,
            "period_text": per,
            "period": duration,
            "starts_from": frm,
            "source_ref": f"Limitation Act 1963, Schedule, Art. {r['article']}",
            "verified": verified,
            **({} if verified else {"unverified_reason": "period or trigger not machine-readable"}),
        })

    payload = {
        "manifest": {
            "title": "Limitation Act, 1963 — THE SCHEDULE (Periods of Limitation)",
            "source_url": SOURCE_URL,
            "source_document": "THE LIMITATION ACT, 1963 (Act 36 of 1963), THE SCHEDULE [See sections 2(j) and 3]",
            "retrieved_date": date.today().isoformat(),
            "built_by": "scripts/extract_limitation_schedule.py",
            "columns_source": "Description of suit/application | Period of limitation | Time from which period begins to run — read per row at their column x-positions.",
            "total_records": len(records),
            "verified_records": sum(1 for r in records if r["verified"]),
            "unverified_records": sum(1 for r in records if not r["verified"]),
            "computation_note": (
                "period + starts_from give the raw limitation window ONLY. Sections 4 "
                "(court closed), 12 (time for obtaining a copy), 14, 17 and 18 "
                "(acknowledgement) can all extend it, and none of them are encoded here. "
                "Any computed date must therefore be presented as provisional and "
                "verified before filing."
            ),
            "licence_note": "Public-domain statute text (Copyright Act s.52(1)(q)).",
        },
        "articles": records,
    }

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {out} — {len(records)} articles "
          f"({payload['manifest']['verified_records']} verified)")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else str(
        REPO_ROOT / "data" / "limitation" / "limitation_schedule.json"
    )
    raise SystemExit(main(target))
