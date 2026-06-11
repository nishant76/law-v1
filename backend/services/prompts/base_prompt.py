"""
Base class for prompt templates
Ensures all prompts follow CLAUDE.md rules:
- Version controlled
- Testable
- Safe from injection attacks
"""
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ModelType(str, Enum):
    """Supported LLM models"""
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
    GPT52 = "gpt-5.2"
    GPT5_2 = "gpt-5.2"
    GPT5_5 = "gpt-5.5"


class PromptTemplate:
    """
    Base class for all prompt templates
    
    Every prompt must:
    1. Inherit from PromptTemplate
    2. Specify system_prompt
    3. Specify user_prompt_template (with {placeholders})
    4. Specify model (GPT4O or GPT4O_MINI)
    5. Specify version (date format YYYY-MM-DD)
    6. Include test cases
    
    Usage:
        from backend.services.prompts import document_extract
        
        response = await llm_service.call(
            system_prompt=document_extract.system_prompt,
            user_prompt=document_extract.user_prompt_template.format(
                document_content=sanitised_text
            ),
            model=document_extract.model,
            temperature=document_extract.temperature
        )
    """
    
    def __init__(
        self,
        system_prompt: str,
        user_prompt_template: str,
        model: ModelType,
        version: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        description: Optional[str] = None,
    ):
        """
        Initialize prompt template
        
        Args:
            system_prompt: System instructions for the model
            user_prompt_template: User message with {placeholders}
            model: Model to use (GPT4O or GPT4O_MINI)
            version: Version date (YYYY-MM-DD format)
            temperature: Randomness (0.0=deterministic, 1.0=creative)
            max_tokens: Maximum tokens in response (None=default)
            top_p: Nucleus sampling parameter
            description: Optional description of this prompt's purpose
        """
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.model = model
        self.version = version
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.description = description
        
        # Validation
        self._validate_version(version)
        self._validate_temperature(temperature)
    
    def _validate_version(self, version: str):
        """Validate version format (YYYY-MM-DD)"""
        try:
            datetime.strptime(version, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Version must be in YYYY-MM-DD format, got '{version}'"
            )
    
    def _validate_temperature(self, temperature: float):
        """Validate temperature in range [0, 1]"""
        if not 0.0 <= temperature <= 1.0:
            raise ValueError(
                f"Temperature must be between 0.0 and 1.0, got {temperature}"
            )
    
    def format_user_prompt(self, **kwargs) -> str:
        """
        Format user prompt template with provided arguments
        
        Args:
            **kwargs: Values for {placeholders} in user_prompt_template
            
        Returns:
            Formatted user prompt string
            
        Raises:
            KeyError: If placeholder in template not provided in kwargs
        """
        try:
            return self.user_prompt_template.format(**kwargs)
        except KeyError as e:
            raise ValueError(
                f"Missing required placeholder: {e}. "
                f"Expected: {self._get_placeholders()}"
            )
    
    def _get_placeholders(self) -> list:
        """Extract placeholder names from template"""
        import re
        placeholders = re.findall(r'\{(\w+)\}', self.user_prompt_template)
        return list(set(placeholders))  # Unique placeholders
    
    def get_config(self) -> Dict[str, Any]:
        """Get full prompt configuration as dict"""
        return {
            "system_prompt": self.system_prompt,
            "user_prompt_template": self.user_prompt_template,
            "model": self.model.value,
            "version": self.version,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "description": self.description,
        }
    
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"PromptTemplate("
            f"model={self.model.value}, "
            f"version={self.version}, "
            f"temp={self.temperature}"
            f")"
        )


# ============================================================================
# EXAMPLE PROMPT (to be moved to separate feature-specific files)
# ============================================================================

# Document field extraction prompt
extract_document_fields_prompt = PromptTemplate(
    system_prompt="""You are an expert legal document analyzer specializing in Indian law.
Your task is to extract structured information from legal documents with high accuracy.
Always respond in valid JSON format.
If a field cannot be found in the document, set its value to null.
Never make up or infer information not explicitly stated in the document.""",
    
    user_prompt_template="""Please analyze this legal document and extract the following fields:
- case_number: The unique identifier for the case (e.g., "SLP(C) 2024-001")
- case_name: Full name of the case (petitioner vs respondent)
- court: The court in which the case was filed
- judge_name: Name of the judge who decided the case (if available)
- filing_date: Date when the case was filed (YYYY-MM-DD format)
- hearing_date: Date of the next or most recent hearing
- parties: List of parties involved
- subject_matter: What the case is about
- outcome: Final decision/outcome of the case

Document text:
{document_content}

Respond with ONLY valid JSON, no other text.""",
    
    model=ModelType.GPT4O_MINI,
    version="2024-04-08",
    temperature=0.0,  # Deterministic for extraction
    max_tokens=500,
    description="Extract structured fields from legal documents"
)


# Case synopsis generation prompt
case_synopsis_prompt = PromptTemplate(
    system_prompt="""You are an expert legal summarizer specializing in Indian law.
Your task is to create clear, concise summaries of legal cases.
Focus on the essential facts, legal issues, and final decision.
Use simple, plain language that a paralegal would understand.
Always respond in valid JSON format.""",
    
    user_prompt_template="""Please summarize this legal document and provide:
- parties: The names of the petitioner and respondent
- facts: 2-3 key facts that led to the case
- legal_issues: The main legal questions the court had to decide
- held: The court's decision and reasoning
- citations: Any statutes or previous cases cited (list them)

Document:
{document_content}

Respond with ONLY valid JSON, no other text.""",
    
    model=ModelType.GPT4O_MINI,
    version="2024-04-08",
    temperature=0.1,  # Mostly deterministic with slight variation
    max_tokens=1000,
    description="Generate case synopsis from judgment or petition"
)
