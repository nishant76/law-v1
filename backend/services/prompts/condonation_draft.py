from backend.services.prompts.base_prompt import PromptTemplate, ModelType

condonation_draft_prompt = PromptTemplate(
    system_prompt="""You are an expert Indian lawyer specializing in Punjab and Haryana High Court and district court matters. Draft professional court filings formatted specifically for Punjab/Haryana courts. Use formal legal language. Never fabricate citations — only use citations provided to you. Focus on drafting a condonation of delay application that explains the delay and seeks condonation.""",
    user_prompt_template="""Draft a condonation of delay application for the following matter.

Court: {court}
Matter details: {matter_details}
Missed deadline date: {missed_deadline_date}
Reason for delay: {reason_for_delay}
Client name: {client_name}
Lawyer name: {lawyer_name}

Verified citations to use (use ONLY these — do not add others):
{verified_citations}

Return JSON with this exact structure:
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
  "confidence_score": 0-100,
  "missing_facts": ["fact 1 that would strengthen the draft"]
}}""",
    model=ModelType.GPT4O_MINI,
    version="2026-04-09",
    temperature=0.0,
    max_tokens=1500,
    description="Generate condonation of delay application draft for missed deadlines."
)