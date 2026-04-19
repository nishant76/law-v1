from backend.services.prompts.base_prompt import PromptTemplate, ModelType

# Legal Process Guide prompt
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a procedural guide for Indian lawyers in
Punjab and Haryana courts. Answer ONLY from the provided structured
knowledge base data. Never generate procedural information from memory.
If the specific court procedure is not in the knowledge base,
say so explicitly and direct the lawyer to verify at the court registry."""

USER_PROMPT_TEMPLATE = """A lawyer needs procedural guidance.

Matter type: {matter_type}
Court: {court}
Brief facts: {facts}

Knowledge base data for this matter type and court:
{knowledge_base_data}

Return JSON:
{{
  "steps": [
    {{
      "step_number": 1,
      "action": "what to do",
      "details": "specific details",
      "source": "which law/rule this comes from"
    }}
  ],
  "documents_required": ["document 1", "document 2"],
  "court_fees": "approximate amount or 'verify at registry'",
  "limitation_period": "X days/months/years from Y event",
  "limitation_calculation": "how to calculate",
  "typical_timeline": "how long this matter typically takes",
  "confidence": 0-10,
  "verify_at_registry": true/false
}}"""

legal_process_guide_prompt = PromptTemplate(
    system_prompt=SYSTEM_PROMPT,
    user_prompt_template=USER_PROMPT_TEMPLATE,
    model=ModelType.GPT4O_MINI,
    version="2026-04-09",
    temperature=0.0,
    max_tokens=1500,
    description="Guide lawyers through court procedures using curated knowledge base data."
)