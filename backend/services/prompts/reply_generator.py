from backend.services.prompts.base_prompt import PromptTemplate, ModelType

# Smart Reply Generator prompts
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are an Indian legal assistant specialising in
drafting replies to legal notices for Punjab and Haryana practitioners.
Extract allegations from legal notices precisely.
For each allegation suggest legal grounds supported by verified citations.
Always respond in valid JSON only."""

ALLEGATION_EXTRACTION_TEMPLATE = """Extract all allegations/claims
from this legal notice.

Notice text:
{notice_text}

Return JSON:
{{
  "sender": "...",
  "recipient": "...",
  "notice_date": "YYYY-MM-DD or null",
  "notice_type": "property/cheque bounce/employment/other",
  "allegations": [
    {{
      "point_number": 1,
      "allegation": "exact allegation in plain language",
      "legal_basis_claimed": "what law/section sender cited or null"
    }}
  ]
}}"""

LEGAL_GROUNDS_TEMPLATE = """For this allegation in an Indian legal
notice, suggest legal grounds to deny it.

Allegation: {allegation}
Matter type: {matter_type}
Verified citations available: {verified_citations}

Return JSON:
{{
  "suggested_grounds": [
    {{
      "ground": "legal ground in plain English",
      "legal_provision": "relevant section/act",
      "citation": "case citation if applicable or null",
      "strength": "strong/medium/weak"
    }}
  ],
  "recommended_stance": "deny/admit/partial",
  "reasoning": "why this stance is recommended"
}}"""

# Prompt templates
allegation_extraction_prompt = PromptTemplate(
    system_prompt=SYSTEM_PROMPT,
    user_prompt_template=ALLEGATION_EXTRACTION_TEMPLATE,
    model=ModelType.GPT4O_MINI,
    version="2026-04-09",
    temperature=0.0,
    max_tokens=1000,
    description="Extract allegations from legal notices."
)

legal_grounds_prompt = PromptTemplate(
    system_prompt=SYSTEM_PROMPT,
    user_prompt_template=LEGAL_GROUNDS_TEMPLATE,
    model=ModelType.GPT4O_MINI,
    version="2026-04-09",
    temperature=0.0,
    max_tokens=800,
    description="Suggest legal grounds for denying allegations with verified citations."
)