"""
Split the DU Faculty of Law "Drafting, Pleadings and Conveyance" reader
(data/draft_examples/drafting_pleadings_du_law.txt) into individual model
drafts — one file per precedent — so the filing drafter can inject the exact
matching precedent for each filing type.

The book lays the drafts out in a fixed document order, each introduced by an
UPPERCASE heading. We walk those headings in order: each draft runs from its
heading up to the next draft's heading. Output goes to
data/draft_examples/du_book/<slug>.txt plus a manifest.json.

Run:  python scripts/extract_du_drafts.py
Re-run any time the source text changes; it overwrites the du_book/ folder.
"""

import json
import pathlib
import re

_SRC = pathlib.Path("data/draft_examples/drafting_pleadings_du_law.txt")
_OUT_DIR = pathlib.Path("data/draft_examples/du_book")

# Ordered list of (slug, label, heading_regex). Order MUST match the book's
# document order — each draft is sliced from its heading to the next one's.
# Matching is CASE-SENSITIVE: body draft headings are UPPERCASE, while the
# front-matter table of contents lists the same titles in Title Case — matching
# case-sensitively skips the TOC copies. Headings can still repeat as running
# page headers (two UPPERCASE copies a few hundred chars apart); _find_start
# skips a hit whose slice would be too short to be a real draft.
_MARKERS: list[tuple[str, str, str]] = [
    ("recovery_suit_order37", "Suit for Recovery (CPC Order XXXVII summary suit)",
     r"SUIT FOR RECOVERY UNDER ORDER XXXVII"),
    ("permanent_injunction_suit", "Suit for Permanent Injunction",
     r"SUIT FOR PERMANENT INJUNCTION"),
    ("temporary_injunction_app", "Application for Temporary Injunction (O.39 R.1 & 2 CPC)",
     r"APPLICATION FOR TEMPORARY INJUNCTION"),
    ("injunction_order39_r2a", "Application under Order XXXIX Rule 2-A CPC (disobedience)",
     r"APPLICATION UNDER ORDER XXXIX RULE 2-A"),
    ("indigent_person_app", "Application to sue as an Indigent Person (O.33 CPC)",
     r"APPLICATION TO SUE AS AN INDIGENT PERSON"),
    ("ejectment_damages_suit", "Suit for Ejectment and Damages for Wrongful Use/Occupation",
     r"SUIT FOR EJECTMENT AND DAMAGES"),
    ("specific_performance_suit", "Suit for Specific Performance of Contract",
     r"SUIT FOR SPECIFIC PERFORMANCE OF CONTRACT"),
    ("written_statement", "Model Draft Written Statement",
     r"MODEL DRAFT FOR WRITTEN STATEMENT"),
    ("caveat_148a", "Caveat under Section 148-A CPC",
     r"CAVEAT UNDER SECTION 148-A"),
    ("transfer_petition_s25", "Transfer Petition under Section 25 CPC",
     r"TRANSFER PETITION UNDER SECTION 25"),
    ("execution_application", "Execution Application (O.21 CPC)",
     r"EXECUTION APPLICATION"),
    ("rcr_hma_s9", "Petition for Restitution of Conjugal Rights (S.9 HMA)",
     r"PETITION FOR RESTITUTION OF CONJUGAL RIGHTS"),
    ("judicial_separation_hma_s10", "Petition for Judicial Separation (S.10 HMA)",
     r"PETITION FOR JUDICIAL SEPARATION"),
    ("divorce_hma_s13", "Petition for Divorce (S.13 HMA)",
     r"PETITION FOR DISSOLUTION OF MARRIAGE BY A DECREE OF DIVORCE(?! BY)"),
    ("divorce_mutual_consent_s13b", "Petition for Divorce by Mutual Consent (S.13B HMA)",
     r"PETITION FOR DISSOLUTION OF MARRIAGE BY A DECREE OF DIVORCE BY"),
    ("probate_petition", "Petition for Grant of Probate",
     r"PETITION FOR GRANT OF PROBATE"),
    ("letters_of_administration", "Petition for Grant of Letters of Administration",
     r"PETITION FOR GRANT OF LETTERS OF ADMINISTRATION"),
    ("succession_certificate", "Petition for Grant of Succession Certificate",
     r"PETITION FOR THE GRANT OF SUCCESSION CERTIFICATE"),
    ("writ_petition_civil", "Writ Petition (Civil) — Article 226",
     r"WRIT PETITION \(CIVIL\)"),
    ("writ_petition_criminal", "Writ Petition (Criminal) — enforcement of fundamental rights",
     r"WRIT PETITION \(CRL\.?\)"),
    ("slp_civil_a136", "Special Leave Petition (Civil) — Article 136",
     r"SPECIAL LEAVE PETITION \(CIVIL\)"),
    ("slp_criminal_a136", "Special Leave Petition (Criminal) — Article 136",
     r"SPECIAL LEAVE PETITION \(CRIMINAL\)"),
    ("bail_regular", "Application for Grant of (Regular) Bail",
     r"APPLICATION FOR GRANT OF BAIL"),
    ("anticipatory_bail", "Application for Grant of Anticipatory Bail",
     r"APPLICATION FOR THE GRANT OF ANTICIPATORY BAIL"),
    ("ni_138_complaint", "Complaint under Section 138 NI Act",
     r"COMPLAINT UNDER SECTION 138"),
    ("maintenance_125", "Application for Maintenance under Section 125 CrPC",
     r"APPLICATION FOR MAINTENANCE UNDER SECTION 125"),
    ("consumer_complaint", "Complaint under the Consumer Protection Act",
     r"COMPLAINT UNDER THE CONSUMER PROTECTION ACT"),
    ("contempt_petition", "Contempt Petition (Contempt of Courts Act)",
     r"CONTEMPT PETITION"),
    ("domestic_violence", "Complaint under the Protection of Women from Domestic Violence Act",
     r"COMPLAINT UNDER OF THE PROTECTION OF WOMEN FROM DOMESTIC"),
    # ── Part B: Conveyancing — deeds & notices ──
    ("will", "Will (last will and testament)",
     r"THIS IS THE LAST WILL"),
    ("special_poa_sale", "Special Power of Attorney to execute Sale Deed",
     r"SPECIAL POWER TO ATTORNEY TO EXECUTE A SALE DEED"),
    ("agreement_to_sell", "Agreement to Sell (immovable property)",
     r"SALE OF IMMOVABLE PROPERTY"),
    ("sale_deed", "Sale Deed",
     r"SALE DEED\s*\nTHIS SALE DEED"),
    ("lease_deed", "Lease Deed",
     r"LEASE DEED\s*\nTHIS LEASE DEED"),
    ("mortgage_deed", "Mortgage Deed",
     r"MORTAGAGE DEED"),
    ("partnership_deed", "Partnership Deed",
     r"PARTNERSHIP DEED\s*\nTHIS DEED OF PARTNERSHIP"),
    ("dissolution_partnership_deed", "Deed of Dissolution of Partnership",
     r"DEED OF DISSOLUTION"),
    ("relinquishment_deed", "Relinquishment Deed",
     r"RELINQUISHMENT DEED\s*\nTHIS DEED OF RELINQUISHMENT"),
    ("gift_deed", "Gift Deed",
     r"GIFT DEED\s*\nTHIS GIFT DEED"),
    ("notice_106_tpa", "Notice of Ejectment (S.106 Transfer of Property Act)",
     r"NOTICE OF EJECTMENT"),
    ("notice_80_cpc", "Notice of Suit under Section 80 CPC",
     r"NOTICE OF SUIT UNDER SECTION 80"),
    ("notice_138_ni", "Notice under Section 138 NI Act (cheque bounce)",
     r"NOTICE UNDER SECTION 138"),
    ("reply_138_notice", "Reply to Legal Notice (S.138 NI Act)",
     r"REPLY TO LEGAL NOTICE"),
]


def main() -> None:
    if not _SRC.exists():
        raise SystemExit(f"Source not found: {_SRC}")
    text = _SRC.read_text(encoding="utf-8")

    # Minimum plausible draft length. A shorter slice means the heading matched a
    # running page-header duplicate, not the real draft body — skip to the next hit.
    _MIN_DRAFT = 300

    def _find_start(pattern: str, cursor: int) -> int:
        """First case-sensitive hit at/after cursor whose next heading-free run
        is long enough to be a real draft (skips repeated page-header copies)."""
        for m in re.finditer(pattern, text[cursor:]):
            pos = cursor + m.start()
            # Peek ahead: is there another copy of THIS heading within _MIN_DRAFT?
            nxt = re.search(pattern, text[pos + 1:])
            if nxt and nxt.start() < _MIN_DRAFT:
                continue  # this hit is the header dup; the real body starts at the copy
            return pos
        return -1

    # Find each marker's start position by scanning forward from the previous one.
    found: list[tuple[str, str, int]] = []  # (slug, label, start)
    cursor = 0
    missing: list[str] = []
    for slug, label, pattern in _MARKERS:
        start = _find_start(pattern, cursor)
        if start < 0:
            missing.append(slug)
            continue
        found.append((slug, label, start))
        cursor = start + _MIN_DRAFT  # advance past this heading + any header dup

    # The book terminates every draft with a star separator line ("* * * * *").
    # Trim each slice there so the following draft's heading (whose header-dup we
    # skipped) doesn't leak into this one's tail. Fallback: the "PART B"
    # conveyancing chapter divider (bounds the last Part-A draft cleanly).
    _END_STARS = re.compile(r"\*\s*\*\s*\*")
    _PART_B = re.compile(r"PART\s*[-–\s]*B\b")

    def _trim(body: str) -> str:
        cut = len(body)
        m = _END_STARS.search(body)
        if m:
            cut = min(cut, m.end())
        mb = _PART_B.search(body)
        if mb:
            cut = min(cut, mb.start())
        return body[:cut].rstrip()

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for idx, (slug, label, start) in enumerate(found):
        end = found[idx + 1][2] if idx + 1 < len(found) else len(text)
        body = _trim(text[start:end].strip())
        out_path = _OUT_DIR / f"{slug}.txt"
        out_path.write_text(body, encoding="utf-8")
        manifest.append({
            "slug": slug,
            "label": label,
            "chars": len(body),
            "file": f"du_book/{slug}.txt",
        })
        print(f"  {slug:32s} {len(body):6d} chars  ({label})")

    (_OUT_DIR / "manifest.json").write_text(
        json.dumps({
            "source": "drafting_pleadings_du_law.txt",
            "source_note": (
                "University of Delhi Faculty of Law LL.B. reader LB-502 "
                "(Drafting, Pleadings and Conveyance, July 2020). Public "
                "educational material. Pre-BNS/BNSS: use for FORMAT/structure "
                "only; current section numbers come from the prompt's BNSS table."
            ),
            "drafts": manifest,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"\nExtracted {len(found)} drafts → {_OUT_DIR}")
    if missing:
        print(f"WARNING — markers not found: {missing}")


if __name__ == "__main__":
    main()
