"""
Search Enrichment Prompts
Two prompts used by the unified search pipeline:
  1. citation_enrichment_prompt  — per-citation AI summary (cached in DB)
  2. search_analysis_prompt      — overall query-level analysis (fresh per search)

Rules (CLAUDE.md):
  - Both use GPT-4o-mini (never GPT-4o for search)
  - All output is structured JSON only
  - Never fabricate information not present in the document
  - Changing this file = making a PR — add regression tests first
"""
from backend.services.prompts.base_prompt import PromptTemplate, ModelType

# ---------------------------------------------------------------------------
# Prompt 1 — Individual Citation Enrichment
# Cached in law.citations.enrichment JSONB — generated once, reused forever.
# ---------------------------------------------------------------------------

citation_enrichment_prompt = PromptTemplate(
    system_prompt=(
        "You are a legal document analyst specialising in Indian law, "
        "specifically Punjab and Haryana High Court and district court matters. "
        "Analyse Indian court judgments and return structured metadata. "
        "Always respond in valid JSON only. "
        "Never fabricate information not present in the provided text. "
        "If a field cannot be determined from the text, set it to null."
    ),
    user_prompt_template=(
        "Analyse this Indian court judgment and return structured metadata.\n\n"
        "Case: {case_name}\n"
        "Court: {court}\n"
        "Year: {year}\n\n"
        "Document text (may be truncated):\n"
        "{document_text}\n\n"
        "Search query that retrieved this case:\n"
        "{query}\n\n"
        "Return JSON with this exact structure:\n"
        "{{\n"
        '  "facts": "2 sentence summary of the key facts",\n'
        '  "issue": "the core legal question decided by the court",\n'
        '  "reasoning": "the court\'s key reasoning in 2 sentences",\n'
        '  "ratio": "the binding legal principle established",\n'
        '  "relevance": "why this case matches the specific search query above"\n'
        "}}"
    ),
    model=ModelType.GPT4O_MINI,
    version="2026-04-19",
    temperature=0.0,
    max_tokens=500,
    description=(
        "Enrich a single public judgment citation with structured metadata. "
        "Result is cached in law.citations.enrichment and reused across searches."
    ),
)

# ---------------------------------------------------------------------------
# Prompt 2 — Overall Search Analysis
# Generated fresh per search query — never cached (it is query-specific).
# Only called when >= 3 public judgment results are returned.
# ---------------------------------------------------------------------------

search_analysis_prompt = PromptTemplate(
    system_prompt=(
        "You are a senior Punjab and Haryana High Court lawyer with 20 years experience. "
        "Analyse a set of retrieved judgments and provide a concise strategic overview. "
        "Always respond in valid JSON only. "
        "Base your analysis ONLY on the provided cases. "
        "Never fabricate additional cases or facts. "
        "Keep each field to 2 sentences maximum."
    ),
    user_prompt_template=(
        "A lawyer has searched for: {query}\n\n"
        "These are the most relevant judgments found:\n"
        "{cases_summary}\n\n"
        "Provide a concise overall analysis in JSON:\n"
        "{{\n"
        '  "trend": "what pattern do these cases show overall",\n'
        '  "winning_factors": ["factor 1", "factor 2", "factor 3"],\n'
        '  "risk_factors": ["risk 1", "risk 2"],\n'
        '  "strongest_case": "which single case best supports this query and why",\n'
        '  "practical_advice": "one actionable insight for the lawyer"\n'
        "}}"
    ),
    model=ModelType.GPT4O_MINI,
    version="2026-04-19",
    temperature=0.0,
    max_tokens=600,
    description=(
        "Generate an overall strategic analysis across all public judgment results "
        "for a given search query. Called only when >= 3 results. Never cached."
    ),
)
