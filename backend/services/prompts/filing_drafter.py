from backend.services.prompts.base_prompt import PromptTemplate, ModelType
import os

# Strategic Filing Drafter prompt
# Production: GPT4O  |  Development/test: GPT4O_MINI (cheaper, faster)
_use_mini = os.getenv("ENVIRONMENT", "development").lower() != "production"
MODEL = ModelType.GPT4O_MINI if _use_mini else ModelType.GPT4O

SYSTEM_PROMPT = """You are an expert Indian lawyer specialising in
Punjab and Haryana High Court and district court matters with 20 years
of experience. Draft professional court filings formatted specifically
for Punjab/Haryana courts. Use formal legal language.
Never fabricate citations — only use citations provided to you.
Always follow the filing objective specified by the lawyer."""

USER_PROMPT_TEMPLATE = """Draft a {filing_type} for the following matter.

Filing objective: {objective}
(Win on merits / Delay proceedings / Challenge jurisdiction /
Seek settlement / Preserve appeal rights)
Adapt your entire drafting strategy to this objective.

Court: {court}
Client: {client_name}
Facts: {facts}
Relief sought: {relief}

Verified citations to use (use ONLY these — do not add others):
{verified_citations}

Return JSON:
{{
  "draft_sections": {{
    "court_heading": "...",
    "parties_section": "...",
    "facts_section": "...",
    "grounds_section": "...",
    "prayer_section": "...",
    "verification": "..."
  }},
  "citations_used": ["citation 1", "citation 2"],
  "strategy_notes": "brief note on how objective influenced drafting",
  "completeness_score": 0-100,
  "missing_facts": ["fact 1 that would strengthen the draft"]
}}"""

filing_drafter_prompt = PromptTemplate(
    system_prompt=SYSTEM_PROMPT,
    user_prompt_template=USER_PROMPT_TEMPLATE,
    model=MODEL,
    version="2026-04-09",
    temperature=0.0,
    max_tokens=2000,
    description="Generate strategic court filings with objective-based drafting and citation verification."
)