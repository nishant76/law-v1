"""
Loads P&H HC filing format examples from data/draft_examples/.
Returns a short excerpt (~2500 chars) to inject into the filing drafter prompt
so the LLM produces properly formatted Punjab/Haryana court filings.
"""

import json
import pathlib
import re
from functools import lru_cache
from typing import Optional

_CATALOG_PATH = pathlib.Path("data/draft_examples/catalog.json")
_EXAMPLES_DIR = pathlib.Path("data/draft_examples")

# Ordered from most-specific to least-specific
_TYPE_KEYWORDS: list[tuple[str, str]] = [
    (r"bail\s+cancel|cancel\w*\s+bail", "CRM-M_BAIL_CANCEL"),
    (r"anticipatory\s+bail|438\s+crpc|482\s+bnss|apprehend\w*\s+arrest", "CRM-M_ANTICIPATORY"),
    (r"quash|482\s+crpc|528\s+bnss|fir\s+quash|compromise\s+quash", "CRM-M_QUASHING"),
    (r"\bcrm\b|bail\s+applic|regular\s+bail|439\s+crpc|483\s+bnss", "CRM-M_BAIL"),
    (r"habeas\s+corpus|crwp|illegal\s+detention|set\s+(at\s+)?liberty", "CRWP"),
    (r"\bcwp\b|civil\s+writ|article\s+226|art\.?\s*226|writ\s+petition", "CWP"),
    (r"\bplaint\b|civil\s+suit|order\s+vii|order\s+37|money\s+suit|recovery\s+suit", "CIVIL_SUIT"),
]

# Per-type: which text file to use and where to start the excerpt.
# start_pattern: regex — excerpt starts at first match; None = start of file.
_TYPE_CONFIG: dict[str, dict] = {
    "CWP": {
        "text_file": "cwp_sample_fatehpal_singh.txt",
        "label": "Civil Writ Petition (CWP) — P&H HC Article 226",
        "start_pattern": None,
        "max_chars": 2500,
    },
    "CRWP": {
        "text_file": "cwp_sudha_bharadwaj_sample.txt",
        "label": "Criminal Writ Petition (CRWP) — P&H HC Habeas Corpus",
        "start_pattern": None,
        "max_chars": 2500,
    },
    "CRM-M_BAIL": {
        "text_file": "quashing_482_compromise_proforma.txt",
        "label": "CRM-M Petition — P&H HC (Index + Format)",
        "start_pattern": r"IN THE HON.BLE HIGH COURT",
        "max_chars": 2500,
    },
    "CRM-M_ANTICIPATORY": {
        "text_file": "quashing_482_compromise_proforma.txt",
        "label": "CRM-M Petition — P&H HC (Index + Format; adapt for s.438 CrPC / s.482 BNSS)",
        "start_pattern": r"IN THE HON.BLE HIGH COURT",
        "max_chars": 2500,
    },
    "CRM-M_QUASHING": {
        "text_file": "quashing_482_compromise_proforma.txt",
        "label": "CRM-M Quashing Petition — P&H HC 482 CrPC",
        "start_pattern": r"IN THE HON.BLE HIGH COURT",
        "max_chars": 2500,
    },
    "CRM-M_BAIL_CANCEL": {
        "text_file": "quashing_482_compromise_proforma.txt",
        "label": "CRM-M Bail Cancellation — P&H HC (Index + Format)",
        "start_pattern": r"IN THE HON.BLE HIGH COURT",
        "max_chars": 2500,
    },
    "CIVIL_SUIT": {
        "text_file": "drafting_pleadings_du_law.txt",
        "label": "Civil Suit Plaint — District Court (CPC Order VII / Order XXXVII)",
        "start_pattern": r"IN THE COURT OF",
        "max_chars": 2500,
    },
}


@lru_cache(maxsize=1)
def _load_catalog() -> dict:
    if _CATALOG_PATH.exists():
        return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return {}


def detect_filing_type(text: str) -> Optional[str]:
    """Return the best-matching filing type key for the user's input."""
    lower = text.lower()
    for pattern, ftype in _TYPE_KEYWORDS:
        if re.search(pattern, lower):
            return ftype
    return None


def _load_excerpt(ftype: str) -> Optional[str]:
    cfg = _TYPE_CONFIG.get(ftype)
    if not cfg:
        return None

    txt_path = _EXAMPLES_DIR / cfg["text_file"]
    if not txt_path.exists():
        return None

    raw = txt_path.read_text(encoding="utf-8")

    start = 0
    if cfg["start_pattern"]:
        m = re.search(cfg["start_pattern"], raw, re.IGNORECASE)
        if m:
            start = m.start()

    excerpt = raw[start : start + cfg["max_chars"]].strip()
    if not excerpt:
        return None

    return f"--- FORMAT REFERENCE ({cfg['label']}) ---\n{excerpt}\n--- END FORMAT REFERENCE ---"


def get_format_example(user_input: str) -> Optional[str]:
    """
    Given the user's filing description, return a format excerpt suitable for
    injecting into the filing drafter prompt, or None if no match.
    """
    ftype = detect_filing_type(user_input)

    if ftype is None:
        # Fallback: if P&H HC is mentioned default to CWP format
        if re.search(r"p&?h|punjab.{0,25}haryana|high court.*chandigarh", user_input.lower()):
            ftype = "CWP"

    if ftype is None:
        return None

    return _load_excerpt(ftype)


def get_phc_format_rules() -> str:
    """Return the P&H HC mandatory format requirements as a compact text block."""
    catalog = _load_catalog()
    rules = catalog.get("phc_format_requirements", {})
    heading = rules.get("heading", "IN THE HIGH COURT OF PUNJAB AND HARYANA AT CHANDIGARH")
    return (
        "P&H HC MANDATORY FORMAT:\n"
        f'- Heading: "{heading}"\n'
        "- Font: Roman size 14, double spacing, one side of page only\n"
        "- Margins: 1.25\" top/left/right, 0.75\" bottom\n"
        "- Required sections (in order): Index, Memo of Parties, List of Dates, "
        "Petition/Application body (numbered paragraphs), Prayer, Verification, Affidavit\n"
        "- BNSS note: For FIRs on/after 01-Jul-2024 use BNSS sections "
        "(s.438 CrPC → s.482 BNSS; s.439 CrPC → s.483 BNSS; s.482 CrPC → s.528 BNSS)"
    )
