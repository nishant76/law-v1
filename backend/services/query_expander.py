"""
Legal Query Expander — expands a lawyer's query into related Indian legal terms
before vector search, preventing vocabulary mismatch between query and document.

Problem solved:
  Query:    "vicarious liability"
  Document: "MACT award", "employer took stand", "recovery from employee"
  Without expansion → 0 results. With expansion → correct match.

The expander generates 6-8 semantically related terms/phrases that a judge
or lawyer might use instead of the query term, specifically for Indian law
(Punjab / Haryana district court + P&H HC context).
"""
import asyncio
import json
import re
from typing import List, Optional

from backend.services.llm_service import get_llm_service, ModelType
from backend.core.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Static synonym table — zero-latency for the most common mismatches.
# Keyed by lowercase canonical concept → list of related terms.
# ---------------------------------------------------------------------------
_LEGAL_SYNONYMS: dict[str, List[str]] = {
    "vicarious liability": [
        "employer liability", "master servant rule", "respondeat superior",
        "MACT employer", "recovery from employee", "employer held liable",
        "principal agent liability", "employee negligence employer",
        "employer responsible for driver",
    ],
    "natural justice": [
        "audi alteram partem", "hear the other side", "opportunity of hearing",
        "principles of fairness", "show cause notice", "opportunity to reply",
        "nemo judex in causa sua",
    ],
    "res judicata": [
        "matter already decided", "issue estoppel", "final judgment bar",
        "decided in previous proceedings", "cannot reopen decided matter",
    ],
    "limitation": [
        "time barred", "delay in filing", "condonation of delay",
        "period of limitation", "suit barred by time", "Article 65", "Article 58",
    ],
    "injunction": [
        "stay order", "interim relief", "restrain defendant", "status quo",
        "prohibitory order", "Order 39 Rule 1", "Order 39 Rule 2",
    ],
    "specific performance": [
        "enforce agreement", "compel execution", "agreement to sell enforcement",
        "Section 10 Specific Relief Act", "decree for performance",
    ],
    "estoppel": [
        "cannot change stand", "bound by earlier statement", "Section 115",
        "Indian Evidence Act estoppel", "approbate and reprobate",
    ],
    "maintainability": [
        "not maintainable", "no cause of action", "suit barred",
        "jurisdiction objection", "preliminary objection", "Order 7 Rule 11",
    ],
    "bail": [
        "Section 437", "Section 439", "anticipatory bail", "Section 438",
        "bail application", "custody", "remand", "released on bail",
    ],
    "service matter": [
        "departmental proceedings", "punishment order", "charge sheet",
        "disciplinary inquiry", "increment stopped", "dismissal from service",
        "service rules violation",
    ],
}


async def expand_query(query: str, use_llm: bool = True) -> List[str]:
    """
    Return a deduplicated list starting with the original query,
    followed by related legal terms.

    Strategy:
      1. Check the static synonym table first (instant, zero cost).
      2. If no static match and use_llm=True, call GPT-4o-mini once.
      3. Always include the original query at position 0.
      4. Fall back to [query] if everything fails — never raise.

    Args:
        query:    The lawyer's original question / search phrase.
        use_llm:  Set False in tests or when latency matters more than recall.

    Returns:
        List of strings — original query + related terms, deduplicated.
    """
    q_lower = query.lower().strip()
    terms: List[str] = [query]

    # ── Step 1: static table ─────────────────────────────────────────────────
    for key, synonyms in _LEGAL_SYNONYMS.items():
        if key in q_lower or any(s.lower() in q_lower for s in synonyms):
            for s in synonyms:
                if s.lower() != q_lower and s not in terms:
                    terms.append(s)
            break  # One match per query is enough

    if len(terms) > 1:
        logger.debug(f"query_expander: static match for '{query[:60]}' → {len(terms)} terms")
        return terms

    # ── Step 2: LLM expansion ────────────────────────────────────────────────
    if not use_llm:
        return terms

    try:
        llm = get_llm_service()
        system_prompt = (
            "You are a legal terminology expert for Indian courts "
            "(Punjab, Haryana, district courts and P&H High Court). "
            "Given a legal query, return 6-8 related terms, concepts, "
            "or phrases that Indian judges and lawyers use when discussing "
            "the same topic. Include both English legal terms and common "
            "plain-language equivalents. Return JSON only."
        )
        user_prompt = (
            f'Query: "{query}"\n\n'
            "Return JSON:\n"
            '{"terms": ["term1", "term2", "term3", ...]}\n\n'
            "Include synonyms, related Indian legal provisions, and plain-language "
            "equivalents. Do NOT include the original query itself."
        )

        response = await asyncio.wait_for(
            llm.call_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=ModelType.GPT4O_MINI,
                temperature=0.0,
                max_tokens=200,
            ),
            timeout=5.0,  # Never block search for more than 5s
        )

        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned.strip()).strip()

        data = json.loads(cleaned)
        for t in data.get("terms", []):
            if t and t.lower() != q_lower and t not in terms:
                terms.append(t)

        logger.info(
            f"query_expander: LLM expanded '{query[:50]}' → {len(terms)} terms"
        )

    except asyncio.TimeoutError:
        logger.warning("query_expander: LLM timeout — using original query only")
    except Exception as e:
        logger.warning(f"query_expander: expansion failed ({e}) — using original query only")

    return terms


def build_expanded_query_string(terms: List[str]) -> str:
    """
    Combine expanded terms into a single search string for FTS/ILIKE.
    Returns just the first term (original query) if expansion is empty.
    """
    if not terms:
        return ""
    # Use the first 4 terms to keep the search string focused
    return " ".join(terms[:4])
