"""
Case Synopsis Generator prompt
Exactly as specified in CLAUDE.md prompt engineering section.

Rules:
- Model: GPT-4o-mini
- All output is structured JSON — never free text
- Model must admit uncertainty explicitly
- Changing this prompt = making a PR (see PROMPT_ENGINEERING_IMPLEMENTATION.txt)
"""
from backend.services.prompts.base_prompt import PromptTemplate, ModelType

MODEL = ModelType.GPT4O_MINI

SYSTEM_PROMPT = """You are a legal document analyst specialising in \
Indian law, specifically Punjab and Haryana High Court and district \
court matters. Extract structured information from Indian court \
judgments and petitions. Always respond in valid JSON only. \
Never fabricate information not present in the document. \
If a field cannot be determined, set it to null."""

USER_PROMPT_TEMPLATE = """Analyse this Indian court document and \
extract structured information.

Document text:
{document_text}

Return JSON with this exact structure:
{{
  "case_name": "full case name",
  "petitioner": "petitioner name",
  "respondent": "respondent name",
  "court": "court name",
  "judgment_date": "YYYY-MM-DD or null",
  "case_number": "case number or null",
  "facts": "2-3 sentence summary of facts",
  "issues": ["issue 1", "issue 2"],
  "held": "what the court decided",
  "citations_used": ["citation 1", "citation 2"],
  "relief_granted": "what relief was granted or null",
  "confidence": 0-10
}}"""

OUTPUT_SCHEMA = {
    "case_name": str,
    "petitioner": str,
    "respondent": str,
    "court": str,
    "judgment_date": "YYYY-MM-DD or null",
    "case_number": "str or null",
    "facts": str,
    "issues": list,
    "held": str,
    "citations_used": list,
    "relief_granted": "str or null",
    "confidence": "int 0-10",
}

case_synopsis_prompt = PromptTemplate(
    system_prompt=SYSTEM_PROMPT,
    user_prompt_template=USER_PROMPT_TEMPLATE,
    model=MODEL,
    version="2026-04-09",
    temperature=0.0,
    max_tokens=1200,
    description=(
        "Extract structured case synopsis from Indian court judgment or petition. "
        "Returns case_name, parties, facts, issues, held, citations_used, confidence."
    ),
)
