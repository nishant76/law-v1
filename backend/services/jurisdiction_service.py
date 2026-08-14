"""
Jurisdiction lookup service — verified offence → court mapping.

Reads the VERIFIED structured data in data/jurisdiction/bnss_first_schedule.json
(built from the official BNSS 2023 First Schedule on indiacode.nic.in — see that
file's manifest and scripts/extract_bnss_schedule.py). This service exposes that
data to the Strategic Filing Drafter and the Legal Process Guide so those
features determine the trial court from the STATUTE, not from an LLM's memory.

Per the launch-quality mandate and Feature 10 (curated-not-AI jurisdiction data),
nothing here is inferred. Two lookup paths:

  * lookup_section()  — exact BNS section (e.g. "103", "356(2)"): returns the
    Schedule row(s) verbatim (offence, punishment, cognizable, bailable,
    triable_by, court_tier, source_ref).
  * court_tier_for_punishment() — the BNSS general rule (First Schedule Part II /
    Ss.22-23): map a maximum punishment to the trial-court tier. Used as a
    fallback for offences under OTHER laws not in Part I (e.g. NI Act s.138),
    where only the punishment is known.

Public functions:
  lookup_section(bns_section)          -> list[dict]
  search_offences(keyword, limit)      -> list[dict]
  court_tier_for_punishment(max_years) -> str (enum)
  court_tier_label(tier)               -> human-readable court name
  manifest()                           -> dict (source, dates, counts)
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional

from backend.core.logger import get_logger

logger = get_logger(__name__)

# data/jurisdiction/bnss_first_schedule.json, resolved from this file's location
# (…/backend/services/jurisdiction_service.py -> repo root is parents[2]).
_DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data" / "jurisdiction" / "bnss_first_schedule.json"
)

# court_tier enum values emitted by the data builder.
TIER_COURT_OF_SESSION = "COURT_OF_SESSION"
TIER_MAGISTRATE_FIRST_CLASS = "MAGISTRATE_FIRST_CLASS"
TIER_MAGISTRATE_SECOND_CLASS = "MAGISTRATE_SECOND_CLASS"
TIER_ANY_MAGISTRATE = "ANY_MAGISTRATE"
TIER_ABETMENT_DEPENDENT = "ABETMENT_DEPENDENT"
TIER_OFFENCE_DEPENDENT = "OFFENCE_DEPENDENT"
TIER_SPECIAL_COMMITTAL = "SPECIAL_COMMITTAL"

# Human-readable court names for the enums (for filing headings / UI).
_TIER_LABELS: Dict[str, str] = {
    TIER_COURT_OF_SESSION: "Court of Session",
    TIER_MAGISTRATE_FIRST_CLASS: "Judicial Magistrate of the First Class "
                                 "(triable by CJM/JMFC under BNSS S.21)",
    TIER_MAGISTRATE_SECOND_CLASS: "Judicial Magistrate of the Second Class",
    TIER_ANY_MAGISTRATE: "Any Magistrate",
    TIER_ABETMENT_DEPENDENT: "Same court as the abetted offence",
    TIER_OFFENCE_DEPENDENT: "Same court as the underlying offence",
    TIER_SPECIAL_COMMITTAL: "The court in which the offence is committed "
                            "(subject to BNSS Chapter XXVIII)",
}


class JurisdictionDataError(Exception):
    """The verified jurisdiction data file is missing or malformed."""


# ---------------------------------------------------------------------------
# Lazy, thread-safe load of the verified data (read once, cached).
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_cache: Optional[dict] = None


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    with _lock:
        if _cache is not None:
            return _cache
        if not _DATA_PATH.exists():
            raise JurisdictionDataError(
                f"Jurisdiction data not found at {_DATA_PATH}. "
                "Run scripts/extract_bnss_schedule.py + build_jurisdiction_json.py."
            )
        try:
            data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise JurisdictionDataError(f"Malformed jurisdiction data: {exc}")
        offences = data.get("offences") or []
        # index by base section number ("356(2)" -> "356") and by exact key
        by_base: Dict[str, List[dict]] = {}
        by_exact: Dict[str, List[dict]] = {}
        for o in offences:
            sec = o["bns_section"]
            base = re.match(r"\d+", sec).group()
            by_base.setdefault(base, []).append(o)
            by_exact.setdefault(sec, []).append(o)
        _cache = {
            "manifest": data.get("manifest", {}),
            "offences": offences,
            "by_base": by_base,
            "by_exact": by_exact,
        }
        logger.info(
            "Loaded BNSS jurisdiction data: %d offence rows, %d base sections",
            len(offences), len(by_base),
        )
        return _cache


def _normalize_section(bns_section: str) -> str:
    """'S.103' / 'Section 103' / '103 BNS' -> '103'; keep sub-clause if given."""
    s = str(bns_section).strip()
    m = re.search(r"\d+\s*(\([0-9A-Za-z]+\))?", s)
    return re.sub(r"\s+", "", m.group()) if m else s


# ---------------------------------------------------------------------------
# Public lookups
# ---------------------------------------------------------------------------
def lookup_section(bns_section: str) -> List[dict]:
    """Return the verified Schedule row(s) for a BNS section.

    Accepts a base section ("103") — returns every sub-scenario row — or an
    exact sub-clause key ("356(2)"). Empty list if the section is not an
    offence-creating section in the First Schedule (e.g. a definition section).
    """
    data = _load()
    key = _normalize_section(bns_section)
    if key in data["by_exact"]:
        return list(data["by_exact"][key])
    base = re.match(r"\d+", key)
    if base and base.group() in data["by_base"]:
        return list(data["by_base"][base.group()])
    return []


def search_offences(keyword: str, limit: int = 20) -> List[dict]:
    """Case-insensitive substring search over the offence descriptions."""
    kw = keyword.strip().lower()
    if not kw:
        return []
    data = _load()
    hits = [o for o in data["offences"] if kw in o["offence"].lower()]
    return hits[:limit]


def court_tier_for_punishment(
    max_imprisonment_years: float,
    death: bool = False,
    life: bool = False,
) -> str:
    """General BNSS trial-court rule (First Schedule Part II / Ss.22-23), for
    offences under OTHER laws not individually listed in Part I:

        death / life / imprisonment > 7 years  -> Court of Session
        imprisonment 3 to 7 years               -> Magistrate of the first class
        imprisonment < 3 years or fine only     -> Any Magistrate

    This is the verbatim rule from Part II of the First Schedule (verified from
    the source PDF). Use ONLY when the specific offence is not in lookup_section
    (e.g. NI Act s.138 cheque bounce). Boundary reading follows the Schedule:
    exactly 3 years -> first class; exactly 7 years -> first class; above 7 ->
    Session.
    """
    years = max_imprisonment_years or 0
    if death or life or years > 7:
        return TIER_COURT_OF_SESSION
    if years >= 3:  # 3 up to and including 7 years
        return TIER_MAGISTRATE_FIRST_CLASS
    return TIER_ANY_MAGISTRATE


def court_tier_label(tier: Optional[str]) -> Optional[str]:
    """Human-readable court name for a court_tier enum, or None if unknown."""
    if not tier:
        return None
    return _TIER_LABELS.get(tier)


def manifest() -> dict:
    """Source URL, retrieval date and record counts for the verified data."""
    return dict(_load()["manifest"])


# ---------------------------------------------------------------------------
# Prompt grounding — inject verified rows into the filing drafter / process guide
# ---------------------------------------------------------------------------
# Offence nouns to scan a free-text brief for. Each is a substring that appears
# in the Schedule's own offence descriptions, so it can be fed to search_offences.
_OFFENCE_KEYWORDS = [
    "murder", "culpable homicide", "dowry death", "abetment of suicide",
    "attempt to commit culpable homicide", "attempt to murder", "grievous hurt",
    "hurt", "acid", "dacoity", "robbery", "extortion", "snatching", "theft",
    "criminal breach of trust", "cheating", "forgery", "counterfeit",
    "kidnapping", "abduction", "rape", "sexual harassment", "voyeurism",
    "stalking", "outrage", "assault", "criminal intimidation", "defamation",
    "mischief", "criminal trespass", "house-trespass", "wrongful confinement",
    "wrongful restraint", "cruelty",
]

# Explicit BNS section references in the brief ("BNS 318(4)", "u/s 318",
# "section 318", "s. 318"). Deliberately requires a section-word cue so it does
# not match stray numbers (amounts, dates, FIR numbers).
_SECTION_REF = re.compile(
    r"(?:\bBNS\b|\bBharatiya\s+Nyaya\b|\bsection\b|\bsec\b|\bu/s\b|\bs\.)\s*\.?\s*"
    r"(\d{1,3}[A-Za-z]?(?:\(\d+[A-Za-z]?\))?)",
    re.I,
)

_CHEQUE_HINT = re.compile(r"cheque|dishonou?r|\b138\b|negotiable instrument", re.I)


def grounding_block(text: str, max_rows: int = 8) -> str:
    """Build a VERIFIED-JURISDICTION prompt block for a free-text filing brief.

    Scans the brief for explicit BNS section references and offence nouns, looks
    each up in the verified First Schedule data, and returns a formatted block
    the drafter can trust for section numbers + trial court. Returns "" when
    nothing matches. NI Act s.138 (cheque bounce) is not a BNS offence, so it is
    handled by an explicit note rather than a Schedule row.
    """
    if not text:
        return ""
    seen: Dict[str, dict] = {}

    def add(rows):
        for r in rows:
            seen.setdefault(r["bns_section"], r)

    for m in _SECTION_REF.finditer(text):
        add(lookup_section(m.group(1)))
    low = text.lower()
    for kw in _OFFENCE_KEYWORDS:
        if kw in low:
            add(search_offences(kw, limit=3))

    lines: List[str] = []
    for r in list(seen.values())[:max_rows]:
        if not r.get("verified") or not r.get("court_tier"):
            continue
        court = court_tier_label(r["court_tier"]) or r.get("triable_by") or "?"
        bits = [f"triable by {court}"]
        if r.get("cognizable") is not None:
            bits.append("cognizable" if r["cognizable"] else "non-cognizable")
        if r.get("bailable") is not None:
            bits.append("bailable" if r["bailable"] else "non-bailable")
        yrs = r.get("max_imprisonment_years")
        if yrs == 1000:
            bits.append("punishable with death")
        elif yrs == 999:
            bits.append("punishable with life imprisonment")
        elif yrs:
            bits.append(f"max imprisonment ~{yrs} years")
        lines.append(f"- BNS {r['bns_section']} — {r['offence']} — " + "; ".join(bits) + ".")

    if _CHEQUE_HINT.search(text):
        lines.append(
            "- NI Act s.138 (cheque dishonour) — NOT a Bharatiya Nyaya Sanhita "
            "offence; triable by a Judicial Magistrate of the First Class at the "
            "place where the cheque was presented for payment (payee's bank branch)."
        )

    if not lines:
        return ""
    header = (
        "VERIFIED JURISDICTION DATA (from the official BNSS 2023 First Schedule — "
        "these BNS section numbers and trial courts are authoritative and OVERRIDE "
        "any section number you may recall; do NOT substitute a different number):"
    )
    footer = (
        "If the offence you actually need is not in this list, do NOT guess its BNS "
        "section number — refer to the offence by name and add a note to "
        "strategy_notes that the exact section must be verified before filing."
    )
    return header + "\n" + "\n".join(lines) + "\n" + footer
