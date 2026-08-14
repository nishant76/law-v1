"""
Special-act lookup service — statutory bars and mandatory pleadings.

Companion to jurisdiction_service. That service answers "which court tries this
BNS offence"; this one answers "what statutory bar or mandatory pleading does
this filing have to deal with, or it is not maintainable".

It reads the VERIFIED verbatim provisions in data/special_acts/special_acts.json
(extracted from the official India Code bare-act PDFs by
scripts/extract_special_acts.py). Nothing here is recalled from memory: the text
the model is shown is the statute's own words, sliced out of the government PDF.

Covers the landmine table in docs/drafting_correctness_audit.md section 4:

  NDPS s.37 (+ s.36A Special Court)   PMLA s.45         UAPA s.43D(5)
  NI s.138 provisos / s.142 limit     CCA s.12A         CPC s.80
  Partnership s.69                    HMA s.14

Known gap, deliberately not papered over
----------------------------------------
The NDPS small/commercial QUANTITY table (S.O. 1055(E)) is not in the data: the
only published copy is a scanned image whose OCR corrupts values. Rather than
guess a threshold — the single highest-consequence number in criminal drafting —
the NDPS block instructs the drafter to obtain the seized quantity from the
lawyer and to flag the classification as requiring verification. See the
manifest's `quantity_table_status`.

Public functions:
  detect_triggers(text)   -> list[str]   (trigger ids present in a brief)
  grounding_block(text)   -> str         (prompt block; "" when nothing applies)
  provision(act_id, sec)  -> dict | None
  manifest()              -> dict
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional

from backend.core.logger import get_logger

logger = get_logger(__name__)

_DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data" / "special_acts" / "special_acts.json"
)

_lock = threading.Lock()
_cache: Optional[Dict] = None


def _load() -> Dict:
    """Load and cache the verified provision data. Missing file is non-fatal."""
    global _cache
    if _cache is not None:
        return _cache
    with _lock:
        if _cache is not None:
            return _cache
        try:
            with _DATA_PATH.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            logger.error("special_acts.json not found at %s — no bar grounding", _DATA_PATH)
            data = {"manifest": {}, "provisions": []}
        except Exception as exc:  # noqa: BLE001
            logger.error("special_acts.json unreadable: %s", exc)
            data = {"manifest": {}, "provisions": []}
        _cache = data
        return _cache


def manifest() -> Dict:
    return _load().get("manifest", {})


def provision(act_id: str, section: str) -> Optional[Dict]:
    """A single verified provision, or None when absent/unverified."""
    for row in _load().get("provisions", []):
        if row.get("act_id") == act_id and row.get("section") == section:
            # Unverified rows carry no text — never surface them.
            return row if row.get("verified") and row.get("text") else None
    return None


# ---------------------------------------------------------------------------
# Triggers
#
# Each trigger names the provisions it needs and the pleading the draft MUST
# contain. `patterns` are matched case-insensitively against the lawyer's brief.
# They are deliberately broad on the act name and narrow on the relief, because
# a missed trigger silently loses a bar while a spurious one only adds a
# paragraph the lawyer can delete.
# ---------------------------------------------------------------------------

_BAIL_HINT = re.compile(
    r"\bbail\b|\banticipatory\b|\bremand\b|\breleased? on bond\b", re.IGNORECASE
)
_SUIT_HINT = re.compile(r"\bsuit\b|\bplaint\b|\bfile a case\b|\brecovery\b", re.IGNORECASE)

_TRIGGERS: List[Dict] = [
    {
        "id": "ndps_bail",
        "label": "NDPS bail — s.37 twin conditions + Special Court",
        "patterns": [r"\bndps\b", r"narcotic", r"psychotropic", r"\bheroin\b",
                     r"\bganja\b", r"\bcharas\b", r"\bopium\b", r"\bcocaine\b",
                     r"\bpoppy husk\b", r"\bsmack\b"],
        "requires": _BAIL_HINT,
        "provisions": [("ndps_1985", "37"), ("ndps_1985", "36A"),
                       ("ndps_1985", "2(viia)"), ("ndps_1985", "2(xxiiia)")],
        "must_plead": [
            "State the seized quantity and expressly classify it as small, "
            "intermediate, or commercial. This determines whether the s.37 bar "
            "applies at all.",
            "If the quantity is COMMERCIAL, or the offence is under s.19, s.24 or "
            "s.27A, address BOTH s.37(1)(b) conditions on their own terms: (i) the "
            "Public Prosecutor has been heard, and (ii) reasonable grounds exist for "
            "believing the accused is not guilty AND is not likely to commit any "
            "offence while on bail. A bail application in a commercial-quantity NDPS "
            "case that does not meet s.37 head-on is fatally defective.",
            "Head the application to the SPECIAL COURT constituted under s.36A, not "
            "to the ordinary Sessions Court.",
            "s.37(2): these limitations are IN ADDITION to the ordinary bail "
            "limitations — do not plead the ordinary test alone.",
        ],
        "must_flag": [
            "The small/commercial quantity thresholds are fixed by the Central "
            "Government notification S.O. 1055(E) dated 19-10-2001. That table is "
            "NOT in this system's verified data. Do NOT state a threshold figure. "
            "If the brief does not give the seized quantity, add it to missing_facts "
            "and add to strategy_notes: 'Quantity classification (small / "
            "intermediate / commercial) must be verified against S.O. 1055(E) before "
            "filing — it decides whether the s.37 bar applies.'",
        ],
    },
    {
        "id": "pmla_bail",
        "label": "PMLA bail — s.45 twin conditions",
        "patterns": [r"\bpmla\b", r"money[- ]laundering", r"money laundering",
                     r"\bed\b(?=\s+(case|matter|summons))", r"enforcement directorate"],
        "requires": _BAIL_HINT,
        "provisions": [("pmla_2002", "45")],
        "must_plead": [
            "Address the s.45 twin conditions expressly: the Public Prosecutor must "
            "be given an opportunity to oppose, and the court must be satisfied there "
            "are reasonable grounds for believing the accused is not guilty and is "
            "not likely to commit any offence on bail.",
            "If the accused falls within the s.45 proviso (person under sixteen, a "
            "woman, sick or infirm, or accused of involvement in a sum of less than "
            "one crore rupees as the proviso specifies), plead that expressly — read "
            "the proviso in the quoted text and rely only on what it actually says.",
            "Head the application to the Special Court designated under the Act.",
        ],
        "must_flag": [],
    },
    {
        "id": "uapa_bail",
        "label": "UAPA bail — s.43D(5) bar and extended remand periods",
        "patterns": [r"\buapa\b", r"unlawful activities", r"terrorist act",
                     r"\bnia\b"],
        "requires": _BAIL_HINT,
        "provisions": [("uapa_1967", "43D")],
        "must_plead": [
            "s.43D(5): bail cannot be granted if the court, on the case diary or the "
            "police report, is of opinion that there are reasonable grounds for "
            "believing the accusation is prima facie true. The application must "
            "attack the prima-facie-true finding on the material itself.",
            "s.43D(2) modifies the default-bail clock — check the extended periods in "
            "the quoted text before pleading any statutory-bail entitlement.",
        ],
        "must_flag": [],
    },
    {
        "id": "ni_138",
        "label": "s.138 NI Act complaint — provisos and s.142 limitation",
        "patterns": [r"\bsection 138\b", r"\bs\.?\s?138\b", r"cheque bounce",
                     r"cheque dishonou?r", r"dishonou?r of cheque",
                     r"negotiable instruments"],
        "requires": None,
        "provisions": [("ni_1881", "138"), ("ni_1881", "142")],
        "must_plead": [
            "Plead each proviso to s.138 as a separate, dated averment: presentation "
            "within validity, the written demand notice within the period the proviso "
            "specifies, and the drawer's failure to pay within the period the proviso "
            "allows. Omitting any one of them makes the complaint liable to be "
            "dismissed at the threshold.",
            "Plead the s.142 requirements: the complaint is in writing by the payee or "
            "holder in due course, and is within the period s.142(b) prescribes from "
            "the accrual of the cause of action.",
            "Read the periods off the quoted statutory text; do not state them from "
            "recollection.",
        ],
        "must_flag": [
            "If the brief does not give the cheque date, presentation date, return-memo "
            "date, notice date, and date of service, list each missing date in "
            "missing_facts — the complaint cannot be verified as within limitation "
            "without them.",
        ],
    },
    {
        "id": "cca_12a",
        "label": "Commercial suit — s.12A pre-institution mediation",
        "patterns": [r"commercial court", r"commercial dispute", r"commercial suit"],
        "requires": None,
        "provisions": [("cca_2015", "12A")],
        "must_plead": [
            "s.12A: unless the suit contemplates urgent interim relief, it CANNOT be "
            "instituted without first exhausting pre-institution mediation. Either "
            "plead compliance and file the settlement/non-starter report, or plead "
            "specifically why urgent interim relief is contemplated.",
        ],
        "must_flag": [],
    },
    {
        "id": "cpc_80",
        "label": "Suit against Government / public officer — s.80 CPC notice",
        "patterns": [r"against the (state|government|union of india)",
                     r"\bstate of (punjab|haryana)\b", r"public officer",
                     r"government department", r"municipal corporation",
                     r"\bunion of india\b"],
        "requires": _SUIT_HINT,
        "provisions": [("cpc_1908", "80")],
        "must_plead": [
            "s.80 CPC: a suit against the Government or a public officer in respect of "
            "an official act cannot be instituted until the notice period in s.80(1) "
            "has expired. Either plead delivery of the notice with its date and the "
            "office it was served on, or invoke s.80(2) and plead the leave sought for "
            "urgent relief.",
        ],
        "must_flag": [],
    },
    {
        "id": "partnership_69",
        "label": "Suit by or on behalf of a firm — s.69 Partnership Act bar",
        "patterns": [r"\bpartnership firm\b", r"\bpartnership\b", r"\bthe firm\b",
                     r"\bpartner(s)? of\b"],
        "requires": _SUIT_HINT,
        "provisions": [("partnership_1932", "69")],
        "must_plead": [
            "s.69: a suit by or on behalf of a firm against a third party is barred "
            "unless the firm is registered AND the persons suing are shown in the "
            "Register of Firms as partners. Plead the registration number and date, "
            "and that the plaintiffs are so shown — or the plaint is liable to be "
            "rejected.",
            "Check the s.69 exceptions in the quoted text before assuming the bar "
            "applies to this particular relief.",
        ],
        "must_flag": [
            "If registration particulars are not in the brief, put them in "
            "missing_facts — they are jurisdictional, not cosmetic.",
        ],
    },
    {
        "id": "hma_14",
        "label": "Divorce within one year of marriage — s.14 HMA bar",
        "patterns": [r"\bdivorce\b", r"\bhindu marriage act\b", r"\bsection 13\b",
                     r"\bs\.?\s?13b\b", r"dissolution of marriage"],
        "requires": None,
        "provisions": [("hma_1955", "14")],
        "must_plead": [
            "s.14: no divorce petition may be presented within one year of the date of "
            "marriage except with the court's leave on the grounds s.14 specifies. If "
            "the marriage date is within one year of filing, the petition MUST carry a "
            "separate application for leave, pleading exceptional hardship or "
            "exceptional depravity as the section requires.",
        ],
        "must_flag": [
            "If the date of marriage is not in the brief, add it to missing_facts — "
            "the s.14 bar cannot be cleared without it.",
        ],
    },
]


def detect_triggers(text: str) -> List[str]:
    """Trigger ids whose subject-matter appears in the brief."""
    if not text:
        return []
    hits: List[str] = []
    for trig in _TRIGGERS:
        if not any(re.search(p, text, re.IGNORECASE) for p in trig["patterns"]):
            continue
        # Some bars only bite for a particular relief (a bail application, a
        # suit). Without that context the mention is incidental.
        requires = trig.get("requires")
        if requires is not None and not requires.search(text):
            continue
        hits.append(trig["id"])
    return hits


def grounding_block(text: str, max_triggers: int = 3) -> str:
    """
    Build the MANDATORY STATUTORY BARS prompt block for a filing brief.

    Returns "" when no bar is engaged, so ordinary filings are not padded with
    irrelevant statute. Provisions are quoted verbatim from the government PDF;
    an unextractable provision is simply absent rather than paraphrased.
    """
    trigger_ids = detect_triggers(text)
    if not trigger_ids:
        return ""

    sections: List[str] = []
    for trig in _TRIGGERS:
        if trig["id"] not in trigger_ids:
            continue
        quoted: List[str] = []
        for act_id, sec in trig["provisions"]:
            row = provision(act_id, sec)
            if row is None:
                continue
            quoted.append(
                f"--- {row['act']} ({row['act_number']}), section {row['section']} "
                f"— {row['label']} ---\n{row['text']}"
            )
        if not quoted:
            # No verified text for this trigger — say nothing rather than
            # assert a bar we cannot evidence.
            logger.warning("special_acts: trigger %s has no verified provisions", trig["id"])
            continue

        parts = [f"### {trig['label']}", "", "STATUTORY TEXT (verbatim, from the bare act):", ""]
        parts += quoted
        parts += ["", "THE DRAFT MUST:"]
        parts += [f"  {i}. {m}" for i, m in enumerate(trig["must_plead"], start=1)]
        if trig["must_flag"]:
            parts += ["", "THE DRAFT MUST ALSO FLAG:"]
            parts += [f"  - {m}" for m in trig["must_flag"]]
        sections.append("\n".join(parts))

        if len(sections) >= max_triggers:
            break

    if not sections:
        return ""

    header = (
        "MANDATORY STATUTORY BARS — VERIFIED STATUTORY TEXT (AUTHORITATIVE)\n"
        "The provisions below were extracted verbatim from the official India Code\n"
        "bare-act PDFs. They OVERRIDE any section number, time period, or condition\n"
        "you recall. A filing that ignores an applicable bar below is not\n"
        "maintainable, so each requirement must appear in the draft — do not treat\n"
        "any of them as optional boilerplate. Quote periods and conditions as the\n"
        "text states them; never state a figure the text does not contain."
    )
    return header + "\n\n" + "\n\n".join(sections) + "\n"
