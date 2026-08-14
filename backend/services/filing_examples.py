"""
Supplies a FORMAT REFERENCE excerpt for the filing drafter prompt so the LLM
matches the structure/heading sequence of a real precedent for the filing type.

Two sources of precedents:
  1. Real Punjab & Haryana High Court filings (data/draft_examples/*.txt) — used
     for the High-Court-level types (writ, regular/anticipatory bail, quashing).
     These are actual filed documents, better than any textbook for HC format.
  2. The University of Delhi Faculty of Law drafting reader, pre-split into one
     model draft per filing type (data/draft_examples/du_book/*.txt, produced by
     scripts/extract_du_drafts.py) — used for every district / family / consumer /
     NI-Act / property / deed type, which previously had NO example at all.

DU book drafts are July-2020 (pre-BNS/BNSS) and Delhi-oriented: they ground the
model on STRUCTURE ONLY. The correct forum heading and current BNSS section
numbers come from the prompt's COURT-SPECIFIC FORMAT RULES / BNSS table, not from
these examples — the reference label says so explicitly.
"""

import json
import pathlib
import re
from functools import lru_cache
from typing import Optional

_CATALOG_PATH = pathlib.Path("data/draft_examples/catalog.json")
_EXAMPLES_DIR = pathlib.Path("data/draft_examples")
_DU_DIR = _EXAMPLES_DIR / "du_book"

# Cap on how much of a precedent to inject. Enough for a complete short draft;
# the few very long DU drafts (transfer petition, criminal writ) are truncated.
_DU_MAX_CHARS = 6000
_PHC_MAX_CHARS = 2500

# ── Real P&H High Court samples (kept as primary for HC-level filings) ──────────
# key -> (text_file, label, start_pattern|None)
_PHC_CONFIG: dict[str, tuple[str, str, Optional[str]]] = {
    "CWP": (
        "cwp_sample_fatehpal_singh.txt",
        "Civil Writ Petition (CWP) — P&H HC Article 226",
        None,
    ),
    "CRWP": (
        "cwp_sudha_bharadwaj_sample.txt",
        "Criminal Writ Petition (CRWP) — P&H HC Habeas Corpus",
        None,
    ),
    "CRM-M_BAIL": (
        "phc_crm_m_bail_sample.txt",
        "CRM-M Regular Bail — P&H HC (s.439 CrPC / s.483 BNSS)",
        None,
    ),
    "CRM-M_ANTICIPATORY": (
        "anticipatory_bail_438_crpc_guide.txt",
        "Anticipatory Bail — s.438 CrPC / s.482 BNSS (format guide)",
        None,
    ),
    "CRM-M_QUASHING": (
        "quashing_482_compromise_proforma.txt",
        "CRM-M Quashing Petition — P&H HC (s.482 CrPC / s.528 BNSS)",
        r"IN THE HON.BLE HIGH COURT",
    ),
    "CRM-M_BAIL_CANCEL": (
        "phc_bail_cancellation_crm_m.txt",
        "CRM-M Bail Cancellation — P&H HC",
        r"IN THE HON.BLE HIGH COURT",
    ),
}

# ── Routing table (ordered most-specific first) ────────────────────────────────
# Each route: (detector_regex, kind, ref) where
#   kind == "phc" -> ref is a _PHC_CONFIG key
#   kind == "du"  -> ref is a du_book/<slug>.txt slug
# Detection runs on the lowercased user input; the drafting UI prepends the
# selected Document Type label to the brief, so the label words match here.
_ROUTES: list[tuple[str, str, str]] = [
    # — order-sensitive criminal/bail (specific before general) —
    (r"bail\s+cancel|cancel\w*\s+bail", "phc", "CRM-M_BAIL_CANCEL"),
    (r"anticipatory\s+bail|s\.?\s*438|482\s+bnss|apprehend\w*\s+arrest", "phc", "CRM-M_ANTICIPATORY"),
    (r"quash|s\.?\s*482\s*crpc|528\s+bnss|fir\s+quash", "phc", "CRM-M_QUASHING"),
    (r"habeas\s+corpus|crwp|illegal\s+detention", "phc", "CRWP"),
    (r"regular\s+bail|\bbail\s+application|s\.?\s*439|483\s+bnss|\bcrm-m\b", "phc", "CRM-M_BAIL"),
    (r"writ\s+petition|article\s+226|art\.?\s*226|\bcwp\b", "phc", "CWP"),

    # — cheque bounce (reply BEFORE complaint so it doesn't grab the 138 route) —
    (r"reply\s+to.*138|reply\s+to\s+legal\s+notice", "du", "reply_138_notice"),
    (r"notice\s+under\s+section\s+138|138\s+ni\s+act\s+notice|demand\s+notice.*cheque", "du", "notice_138_ni"),
    (r"section\s+138|cheque\s+bounce|dishonou?r|negotiable\s+instrument", "du", "ni_138_complaint"),

    # — matrimonial / family —
    (r"mutual\s+consent|s\.?\s*13-?b|13b", "du", "divorce_mutual_consent_s13b"),
    (r"divorce|dissolution\s+of\s+marriage|s\.?\s*13\b.*(hma|hindu\s+marriage)", "du", "divorce_hma_s13"),
    (r"judicial\s+separation|s\.?\s*10\b.*(hma|hindu\s+marriage)", "du", "judicial_separation_hma_s10"),
    (r"restitution|conjugal|s\.?\s*9\b.*(hma|hindu\s+marriage)", "du", "rcr_hma_s9"),
    (r"maintenance|s\.?\s*125|s\.?\s*144\b", "du", "maintenance_125"),
    (r"domestic\s+violence|protection\s+of\s+women|\bdv\s+act\b|498", "du", "domestic_violence"),

    # — consumer —
    (r"consumer", "du", "consumer_complaint"),

    # — private complaint (magistrate) —
    (r"private\s+complaint|section\s+223|section\s+200", "du", "ni_138_complaint"),

    # — civil / property (specific before generic plaint) —
    (r"written\s+statement", "du", "written_statement"),
    (r"temporary\s+injunction|o\.?\s*39|order\s+xxxix|order\s+39", "du", "temporary_injunction_app"),
    (r"permanent\s+injunction", "du", "permanent_injunction_suit"),
    (r"execution\s+(petition|application)|o\.?\s*21|order\s+xxi\b", "du", "execution_application"),
    (r"possession|eviction|ejectment", "du", "ejectment_damages_suit"),
    (r"specific\s+performance", "du", "specific_performance_suit"),
    (r"partition", "du", "recovery_suit_order37"),
    (r"transfer\s+petition|s\.?\s*25\s+cpc", "du", "transfer_petition_s25"),
    (r"legal\s+notice|notice\s+under\s+section\s+80|section\s+106|transfer\s+of\s+property", "du", "notice_106_tpa"),
    (r"indigent|forma\s+pauperis", "du", "indigent_person_app"),
    (r"caveat", "du", "caveat_148a"),
    (r"contempt", "du", "contempt_petition"),
    (r"succession\s+certificate", "du", "succession_certificate"),
    (r"letters?\s+of\s+administration", "du", "letters_of_administration"),
    (r"probate", "du", "probate_petition"),
    (r"special\s+leave|slp|article\s+136", "du", "slp_civil_a136"),

    # — conveyancing deeds & notices —
    (r"sale\s+deed|conveyance\s+deed", "du", "sale_deed"),
    (r"agreement\s+to\s+sell|agreement\s+for\s+sale", "du", "agreement_to_sell"),
    (r"lease\s+deed|rent\s+deed", "du", "lease_deed"),
    (r"mortgage\s+deed", "du", "mortgage_deed"),
    (r"dissolution\s+of\s+partnership", "du", "dissolution_partnership_deed"),
    (r"partnership\s+deed", "du", "partnership_deed"),
    (r"relinquishment", "du", "relinquishment_deed"),
    (r"gift\s+deed", "du", "gift_deed"),
    (r"power\s+of\s+attorney|\bpoa\b", "du", "special_poa_sale"),
    (r"\bwill\b|testament", "du", "will"),

    # — generic civil suit / plaint (LAST — the broad catch) —
    (r"\bplaint\b|civil\s+suit|order\s+vii|order\s+37|recovery\s+suit|money\s+suit", "du", "recovery_suit_order37"),
]

_DU_CAVEAT = (
    "use for STRUCTURE and section sequence only — apply the correct forum "
    "heading and current BNSS section numbers per the rules above, not this "
    "example's Delhi court name or pre-2024 CrPC/IPC sections"
)


@lru_cache(maxsize=1)
def _load_catalog() -> dict:
    if _CATALOG_PATH.exists():
        return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return {}


@lru_cache(maxsize=64)
def _load_du_draft(slug: str) -> Optional[str]:
    path = _DU_DIR / f"{slug}.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def _phc_excerpt(key: str) -> Optional[str]:
    cfg = _PHC_CONFIG.get(key)
    if not cfg:
        return None
    text_file, label, start_pattern = cfg
    path = _EXAMPLES_DIR / text_file
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8")
    start = 0
    if start_pattern:
        m = re.search(start_pattern, raw, re.IGNORECASE)
        if m:
            start = m.start()
    excerpt = raw[start:start + _PHC_MAX_CHARS].strip()
    if not excerpt:
        return None
    return f"--- FORMAT REFERENCE ({label}) ---\n{excerpt}\n--- END FORMAT REFERENCE ---"


def _du_excerpt(slug: str) -> Optional[str]:
    body = _load_du_draft(slug)
    if not body:
        return None
    excerpt = body[:_DU_MAX_CHARS].strip()
    label = f"Model draft: {slug.replace('_', ' ')} — {_DU_CAVEAT}"
    return f"--- FORMAT REFERENCE ({label}) ---\n{excerpt}\n--- END FORMAT REFERENCE ---"


def detect_route(text: str) -> Optional[tuple[str, str]]:
    """Return (kind, ref) for the best-matching filing type, or None."""
    lower = text.lower()
    for pattern, kind, ref in _ROUTES:
        if re.search(pattern, lower):
            return (kind, ref)
    return None


def get_format_example(user_input: str) -> Optional[str]:
    """
    Given the user's filing description (with the Document Type label prepended
    by the UI), return a FORMAT REFERENCE block to inject into the drafter
    prompt, or None if nothing matches.
    """
    route = detect_route(user_input)

    if route is None:
        # P&H HC mentioned but no type detected → default to the CWP format.
        if re.search(r"p&?h|punjab.{0,25}haryana|high court.*chandigarh", user_input.lower()):
            route = ("phc", "CWP")

    if route is None:
        return None

    kind, ref = route
    return _phc_excerpt(ref) if kind == "phc" else _du_excerpt(ref)


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
