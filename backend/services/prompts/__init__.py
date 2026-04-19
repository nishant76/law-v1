"""
Prompt templates for LLM calls
Centralized location for all system and user prompts — version controlled
"""
from backend.services.prompts.base_prompt import PromptTemplate
from backend.services.prompts.rag_synthesis import rag_synthesis_prompt
from backend.services.prompts.case_synopsis import case_synopsis_prompt
from backend.services.prompts.pdf_extractor import pdf_extractor_prompt
from backend.services.prompts.filing_drafter import filing_drafter_prompt
from backend.services.prompts.legal_process_guide import legal_process_guide_prompt

__all__ = [
    "PromptTemplate",
    "rag_synthesis_prompt",
    "case_synopsis_prompt",
    "pdf_extractor_prompt",
    "condonation_draft_prompt",
    "allegation_extraction_prompt",
    "legal_grounds_prompt",
    "filing_drafter_prompt",
    "legal_process_guide_prompt",
]
