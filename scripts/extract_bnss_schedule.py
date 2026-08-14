"""
Extract the BNSS 2023 First Schedule, Part I ("Offences under the Bharatiya
Nyaya Sanhita") into structured, per-row-traceable records.

Source PDF (government primary source, public domain statute text):
  https://upload.indiacode.nic.in/schedulefile
    ?aid=AC_CEN_5_23_00049_202346_1719552320687&rid=1191
  ("173 THE FIRST SCHEDULE — CLASSIFICATION OF OFFENCES")

Method — NOTHING is inferred from memory:
  * Column x-boundaries are taken from the table header rule rectangles present
    on every page (verified identical): the six columns Section / Offence /
    Punishment / Cognizable-or-Non-cognizable / Bailable-or-Non-bailable /
    By-what-Court-triable.
  * Each word is assigned to a column by its x-centre.
  * Words are clustered into visual lines by y (tolerance-based, not fixed
    bucket rounding) so a section number and its offence text stay on one line.
  * A new offence row begins on any line whose Section column holds a section
    token (digits, optional letter, optional "(n)" sub-clause). Blank-section
    lines are continuations appended cell-by-cell.

Run:
  python3 scripts/extract_bnss_schedule.py <path-to-first-schedule.pdf> <out.json>
Re-runnable and deterministic.
"""
import json
import re
import sys

import pdfplumber

# The six column labels, in order. Column x-boundaries are NOT hardcoded: they
# vary page to page and are read from each page's own header rule rectangles
# (see page_dividers). This is what keeps punishment text from bleeding into the
# cognizable column, and vice-versa.
COL_NAMES = ["section", "offence", "punishment", "cognizable", "bailable", "court"]

# A section token: digits, optional trailing letter, optional "(n)" / "(a)"
# sub-clause where the sub-clause may be a number OR a letter (e.g. 210(a)).
SEC_RE = re.compile(r"^\d+[A-Za-z]?(\([0-9A-Za-z]+\))?$")
Y_TOL = 5.0  # px: words within this vertical distance are one visual line


def page_dividers(page):
    """Seven x-values (6 columns) from the page's horizontal header rules, or
    None if this page has no 6-column header (e.g. the Part II page)."""
    rects = [r for r in page.rects if r["height"] < 1.5]
    xs = sorted({round(r["x0"]) for r in rects} | {round(r["x1"]) for r in rects})
    if len(xs) == 7 and xs[0] < 90 and xs[-1] > 530:
        return xs
    return None


def col_of(x_center, dividers):
    for i in range(6):
        if dividers[i] <= x_center < dividers[i + 1]:
            return i
    return None


def cluster_lines(words):
    """Group words into visual lines by top-coordinate proximity."""
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    lines = []
    cur, anchor = [], None
    for w in words:
        if anchor is None or abs(w["top"] - anchor) <= Y_TOL:
            cur.append(w)
            anchor = w["top"] if anchor is None else anchor
        else:
            lines.append(cur)
            cur, anchor = [w], w["top"]
    if cur:
        lines.append(cur)
    return lines


def line_cells(line_words, dividers):
    cells = ["", "", "", "", "", ""]
    for w in sorted(line_words, key=lambda w: w["x0"]):
        ci = col_of((w["x0"] + w["x1"]) / 2, dividers)
        if ci is None:
            continue
        cells[ci] = (cells[ci] + " " + w["text"]).strip()
    return cells


def is_number_header(line_words):
    """The '1 2 3 4 5 6' column-number row (digits may not align to columns)."""
    toks = [w["text"] for w in line_words]
    return bool(toks) and all(t in {"1", "2", "3", "4", "5", "6"} for t in toks)


def is_text_header(cells):
    j = " ".join(cells).lower()
    return ("by what court" in j) or (
        cells[0].strip().lower() == "section" and "offence" in cells[1].lower()
    )


_BAIL_TOKEN = re.compile(r"^(non-?)?bailable", re.I)
_COURT_KW = re.compile(r"session|magistrate", re.I)


def starts_subscenario(cells):
    """A continuation line that begins a fresh punishment scenario of the SAME
    section (value tiers, "defamation in any other case", first/subsequent
    conviction, etc.), printed without repeating the section number.

    Signature: the line carries its own Bailable/Non-bailable token AND a
    Court-of-Session/Magistrate court. Text-wrap lines of the offence or
    punishment cell carry neither. Abetment rows are excluded automatically:
    their court reads "Court by which offence abetted is triable" — no
    'session'/'magistrate' keyword — and their classification is "According
    as ...", not a bailable token."""
    bail = re.sub(r"\s", "", cells[4])
    return bool(_BAIL_TOKEN.match(bail) and _COURT_KW.search(cells[5]))


def _new_record(section, cells, page, sub=False):
    return {
        "section": section,
        "offence": cells[1],
        "punishment": cells[2],
        "cognizable": cells[3],
        "bailable": cells[4],
        "court": cells[5],
        "page": page,
        "sub_scenario": sub,
    }


def extract(pdf_path):
    pdf = pdfplumber.open(pdf_path)
    part2_page = None
    for i, pg in enumerate(pdf.pages):
        if "OFFENCES AGAINST OTHER LAWS" in (pg.extract_text() or ""):
            part2_page = i
            break

    records, cur = [], None

    def flush():
        nonlocal cur
        if cur:
            records.append(cur)
        cur = None

    last = part2_page if part2_page is not None else len(pdf.pages) - 1
    prev_div = None
    for i in range(0, last + 1):
        pg = pdf.pages[i]
        dividers = page_dividers(pg) or prev_div
        if dividers is None:
            continue
        prev_div = dividers
        # Drop top/bottom margin words (running heads + the schedule's own page
        # numbers at top~732 in the 792-tall page) so they never bleed into a cell.
        words = [w for w in pg.extract_words(keep_blank_chars=False)
                 if 70 < w["top"] < 725]
        for lw in cluster_lines(words):
            if is_number_header(lw):
                continue
            cells = line_cells(lw, dividers)
            if is_text_header(cells):
                continue
            joined = " ".join(cells)
            if "OFFENCES AGAINST OTHER LAWS" in joined:
                flush()
                return records, part2_page, len(pdf.pages)
            sec = cells[0].strip()
            if sec and SEC_RE.match(sec) and any(cells[1:]):
                flush()
                cur = _new_record(sec, cells, i + 1)
            elif cur is not None and starts_subscenario(cells):
                # next punishment scenario of the SAME section, printed without
                # repeating the section number -> its own record + sub flag.
                sub_sec = cur["section"]
                flush()
                cur = _new_record(sub_sec, cells, i + 1, sub=True)
            elif cur is not None:
                for name, idx in (("offence", 1), ("punishment", 2),
                                  ("cognizable", 3), ("bailable", 4), ("court", 5)):
                    if cells[idx]:
                        cur[name] = (cur[name] + " " + cells[idx]).strip()
    flush()
    return records, part2_page, len(pdf.pages)


# ---- glyph-tracking repair -------------------------------------------------
# Some cells render words with each letter spaced out ("C o g n izable").
# Glue runs of >=2 consecutive single-letter tokens (plus a trailing lowercase
# fragment) back into one word. Conservative: leaves normal prose untouched.
def despace(s):
    toks = s.split(" ")
    out, buf = [], []
    for t in toks:
        if len(t) == 1 and t.isalpha():
            buf.append(t)
            continue
        if len(buf) >= 2:
            glued = "".join(buf)
            if t and t[0].islower():
                glued += t
                t = ""
            out.append(glued)
        else:
            out.extend(buf)
        if t:
            out.append(t)
        buf = []
    if len(buf) >= 2:
        out.append("".join(buf))
    else:
        out.extend(buf)
    return " ".join(out)


def main():
    pdf_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "bnss_raw_rows.json"
    recs, p2, npages = extract(pdf_path)
    for r in recs:
        for k in ("offence", "punishment", "cognizable", "bailable", "court"):
            r[k] = re.sub(r"\s+", " ", despace(r[k])).strip()
    print(f"pages={npages} part2_page(0idx)={p2} records={len(recs)}")
    print(f"first section={recs[0]['section']} last section={recs[-1]['section']}")
    with open(out_path, "w") as f:
        json.dump(recs, f, indent=1, ensure_ascii=False)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
