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
judgments, petitions, and legal notices. Always respond in valid JSON only. \
Never fabricate information not present in the document. \
If a field cannot be determined, set it to null.

CRITICAL — distinguishing document types:
- If the document is a LEGAL NOTICE (sent by a lawyer/party to another party), \
set court=null and held=null. A lawyer's designation on letterhead \
(e.g. "Advocate, Supreme Court of India") is NOT the court — it is the \
sending advocate's enrolment court. Never use it as the court field.
- If the document is a COURT JUDGMENT or ORDER, extract the court name from \
the heading or cause title, not from any advocate's details.

CITATIONS — extract ALL citations present including:
- Case citations (e.g. "(1997) 4 SCC 664")
- Constitutional provisions (e.g. "Article 19(1)(a)", "Article 21")
- Statutory provisions (e.g. "Rule 133A, Aircraft Rules 1937", "Section 138 NI Act")
- Regulatory instruments (e.g. "CAR Section 3, Series M Part VI, dated 08.09.2017")"""

USER_PROMPT_TEMPLATE = """Analyse this Indian legal document and \
extract structured information.

Document text:
{document_text}

Return JSON with this exact structure:
{{
  "document_type": "one of: judgment | petition | order | legal_notice | contract | affidavit | written_statement | other",
  "case_name": "full case name or notice subject",
  "petitioner": "petitioner / notice sender name",
  "respondent": "respondent / noticee name",
  "court": "court name — null if this is a legal notice not yet filed in court",
  "judgment_date": "YYYY-MM-DD — use notice date if legal notice — null if unknown",
  "case_number": "case number or null",
  "facts": "2-3 sentence summary of facts",
  "issues": ["issue 1", "issue 2"],
  "held": "what the court decided — null if this is a legal notice with no court ruling",
  "citations_used": ["SEARCH THE ENTIRE DOCUMENT and list every single citation found — case citations AND constitutional articles (Art. 14, Art. 19(1)(a), Art. 21 etc.) AND statutory provisions (Rule 133A Aircraft Rules, Section 138 NI Act etc.) AND regulatory instruments (CAR, DGCA circulars etc.) — do not stop after finding 2-3, find all of them"],
  "relief_granted": "For JUDGMENTS: what relief the court granted. For LEGAL NOTICES: list ALL demands made by the sender (compensation amounts, revocation of orders, apologies demanded, costs claimed) — if a demands paragraph exists in the notice this field must not be null",
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
    version="2026-05-07",
    temperature=0.0,
    max_tokens=1500,
    description=(
        "Extract structured case synopsis from Indian court judgment, petition, or legal notice. "
        "Returns case_name, parties, facts, issues, held, citations_used, confidence. "
        "Handles legal notices correctly: court=null, held=null, never confuses "
        "advocate's court designation with the filing court."
    ),
)
