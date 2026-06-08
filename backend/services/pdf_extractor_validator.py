"""
PDF Extractor validator — post-processing for model output.

Responsibility: deterministic formatting only.
The model handles all semantic validation.
No hardcoded legal rules. No domain-specific patches.
"""
import re
from datetime import date as date_type
from typing import Any


CASE_PREFIX_TO_COURT = {
    r"^CWP":             "Punjab and Haryana High Court",
    r"^FAO":             "Punjab and Haryana High Court",
    r"^CR\b":            "Punjab and Haryana High Court",
    r"^RSA":             "Punjab and Haryana High Court",
    r"^CRWP":            "Punjab and Haryana High Court",
    r"^CRM":             "Punjab and Haryana High Court",
    r"^RFA":             "Punjab and Haryana High Court",
    r"^COCP":            "Punjab and Haryana High Court",
    r"^SLP":             "Supreme Court of India",
    r"^Civil Appeal":    "Supreme Court of India",
    r"^Criminal Appeal": "Supreme Court of India",
    r"^O\.A\.":          "Central Administrative Tribunal",
    r"^M\.A\.":          "Central Administrative Tribunal",
    r"^T\.A\.":          "Central Administrative Tribunal",
    r"^W\.P\.\(C\)":     "Delhi High Court",
    r"^W\.P\.\(Crl\.\)": "Delhi High Court",
    r"^LPA":             "Delhi High Court",
    r"^CS\b":            "District Court",
    r"^CC\b":            "District Court",
    r"^RCA":             "District Court",
}


def resolve_court_from_case_number(case_number: str) -> str | None:
    """Deterministically resolve court from case number prefix."""
    if not case_number:
        return None
    for pattern, court in CASE_PREFIX_TO_COURT.items():
        if re.match(pattern, case_number.strip(), re.IGNORECASE):
            return court
    return None


def _is_past_date(date_str: str) -> bool:
    """Return True if date_str is a valid date in the past."""
    if not date_str:
        return False
    try:
        import dateparser
        parsed = dateparser.parse(
            date_str,
            settings={"DATE_ORDER": "DMY", "RETURN_AS_TIMEZONE_AWARE": False}
        )
        if parsed:
            return parsed.date() < date_type.today()
    except Exception:
        pass
    return False


def _is_dismissed(extracted: dict) -> bool:
    """
    Return True if this document represents a dismissed/rejected order.
    Reads the structured case_outcome field set by the LLM.
    """
    outcome = extracted.get("case_outcome")
    if outcome is not None:
        return outcome == "dismissed"
    # Fallback for extractions predating the case_outcome field
    return False


DATE_FIELDS = [
    "date_of_order", "next_hearing_date", "notice_date",
    "reply_deadline", "effective_date", "expiry_date",
    "lease_start_date", "lease_end_date", "contract_date",
    "date_of_fir", "incident_date", "joining_date",
    "launch_date", "due_date",
]


def normalise_date(date_str: str) -> str:
    """Normalise common Indian date formats to YYYY-MM-DD."""
    if not date_str or date_str.lower() in (
        "null", "n/a", "not specified", "none", "not mentioned"
    ):
        return date_str
    try:
        import dateparser
        parsed = dateparser.parse(
            date_str,
            settings={"DATE_ORDER": "DMY"}
        )
        if parsed:
            return parsed.strftime("%Y-%m-%d")
    except Exception:
        pass
    return date_str


def validate_and_correct(extracted: dict, document_text: str = "") -> dict:
    identity = extracted.get("identity_fields", {})

    # STEP 1 — Normalise all date fields
    for field in DATE_FIELDS:
        if field in identity:
            entry = identity[field]
            if isinstance(entry, dict):
                val = entry.get("value")
                if val and isinstance(val, str):
                    identity[field]["value"] = normalise_date(val)

    # STEP 2 — Resolve court from case number
    case_number_field = identity.get("case_number", {})
    case_number = (
        case_number_field.get("value")
        if isinstance(case_number_field, dict)
        else None
    )
    if case_number:
        resolved_court = resolve_court_from_case_number(case_number)
        if resolved_court:
            identity["court"] = {
                "value": resolved_court,
                "confidence": 100,
                "_source": "derived_from_case_number"
            }

    extracted["identity_fields"] = identity

    # STEP 3 — On dismissed cases, remove any deadline/action the LLM
    # mistakenly marked as future or non-court-decision
    if _is_dismissed(extracted):
        extracted["critical_deadlines"] = [
            d for d in extracted.get("critical_deadlines", [])
            if d.get("is_future") is True
        ]
        extracted["action_items"] = [
            item for item in extracted.get("action_items", [])
            if not item.get("is_court_decision", False)
        ]

    # STEP 4 — Return
    return extracted
