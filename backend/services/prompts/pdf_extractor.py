"""
PDF Extractor prompt
Exactly as specified in CLAUDE.md prompt engineering section.

Rules:
- Model: GPT-4o-mini
- All output is structured JSON — never free text
- Per-field confidence scores (0-100)
- Model must NOT guess — null + confidence=0 if field absent
- Changing this prompt = making a PR
"""
from backend.services.prompts.base_prompt import PromptTemplate, ModelType

MODEL = ModelType.GPT4O_MINI

SYSTEM_PROMPT = """You are a legal document data extraction specialist \
for Indian courts. Extract specific structured fields from court orders, \
judgments, and legal documents. Always respond in valid JSON only. \
For each field provide a confidence score 0-100. \
If a field is not clearly present in the document set value to null \
and confidence to 0. Never guess or infer values not explicitly stated."""

USER_PROMPT_TEMPLATE = """Extract structured data from this Indian \
court document.

Document text:
{document_text}

Return JSON with this exact structure:
{{
  "case_number": {{"value": "...", "confidence": 0}},
  "petitioner": {{"value": "...", "confidence": 0}},
  "respondent": {{"value": "...", "confidence": 0}},
  "court": {{"value": "...", "confidence": 0}},
  "date_of_order": {{"value": "YYYY-MM-DD", "confidence": 0}},
  "next_hearing_date": {{"value": "YYYY-MM-DD", "confidence": 0}},
  "relief_granted": {{"value": "...", "confidence": 0}},
  "conditions_imposed": {{"value": ["condition 1", "condition 2"], "confidence": 0}},
  "amount": {{"value": "...", "confidence": 0}},
  "judge_name": {{"value": "...", "confidence": 0}}
}}"""

OUTPUT_SCHEMA = {
    "case_number": {"value": "str or null", "confidence": "int 0-100"},
    "petitioner": {"value": "str or null", "confidence": "int 0-100"},
    "respondent": {"value": "str or null", "confidence": "int 0-100"},
    "court": {"value": "str or null", "confidence": "int 0-100"},
    "date_of_order": {"value": "YYYY-MM-DD or null", "confidence": "int 0-100"},
    "next_hearing_date": {"value": "YYYY-MM-DD or null", "confidence": "int 0-100"},
    "relief_granted": {"value": "str or null", "confidence": "int 0-100"},
    "conditions_imposed": {"value": "list or null", "confidence": "int 0-100"},
    "amount": {"value": "str or null", "confidence": "int 0-100"},
    "judge_name": {"value": "str or null", "confidence": "int 0-100"},
}

# Fields flagged amber in UI when confidence < this threshold (CLAUDE.md: below 75%)
AMBER_CONFIDENCE_THRESHOLD = 75

pdf_extractor_prompt = PromptTemplate(
    system_prompt=SYSTEM_PROMPT,
    user_prompt_template=USER_PROMPT_TEMPLATE,
    model=MODEL,
    version="2026-04-09",
    temperature=0.0,
    max_tokens=800,
    description=(
        "Extract structured fields from Indian court orders, judgments, and legal notices. "
        "Returns per-field value + confidence score. Fields below 75% confidence are amber-flagged."
    ),
)
