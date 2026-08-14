"""
Prompt Registry — All LLM Prompts in SuperAdvocate
============================================

This registry documents every prompt used in the system.
Update this file whenever a new prompt is created or modified.

Format:
- Prompt name
- File location
- Model used
- Purpose/description
- Last updated
- Status (active/deprecated)

---

## Extract Document Fields
- File: `base_prompt.py`
- Model: gpt-4o-mini
- Purpose: Extract structured fields (case number, parties, dates, etc) from legal documents
- Fields extracted: case_number, case_name, court, judge_name, filing_date, hearing_date, parties, subject_matter, outcome
- Temperature: 0.0 (deterministic)
- Max tokens: 500
- Last updated: 2024-04-08
- Status: ACTIVE

Test cases (10 minimum required):
- [ ] Extract from Supreme Court judgment
- [ ] Extract from High Court order
- [ ] Extract from District Court decree
- [ ] Handle missing fields gracefully
- [ ] Handle multilingual content
- [ ] Handle special characters in case names
- [ ] Extract from scanned PDF (low quality OCR)
- [ ] Extract from typed document
- [ ] Handle judgment without judge name
- [ ] Extract dates in different formats

---

## Case Synopsis Generation
- File: `base_prompt.py`
- Model: gpt-4o-mini
- Purpose: Generate structured one-pager summary from judgment or petition
- Output format: JSON (parties, facts, legal_issues, held, citations)
- Temperature: 0.1 (mostly deterministic)
- Max tokens: 1000
- Last updated: 2024-04-08
- Status: ACTIVE

Test cases (10 minimum required):
- [ ] Summarize Supreme Court judgment
- [ ] Summarize High Court order
- [ ] Summarize District Court decree
- [ ] Summarize criminal case judgment
- [ ] Summarize civil case judgment
- [ ] Handle long judgments (20+ pages)
- [ ] Extract and list all cited sections
- [ ] Extract and list all cited cases
- [ ] Identify ratio decidendi correctly
- [ ] Test on constitutional cases

---

## Document (Placeholder for future prompts)

### PDF Extractor
- File: `pdf_extractor.py` (NOT YET CREATED)
- Model: gpt-4o-mini
- Purpose: Extract Q&A from PDF and structured field extraction with confidence scores
- Status: NOT YET CREATED
- Planned: Phase 1, after document ingest pipeline

### Smart Reply Generator
- File: `reply_generator.py`
- Model: gpt-4o-mini
- Purpose: Extract allegations from notices and suggest legal grounds with verified citations
- Status: ACTIVE
- Last updated: 2026-04-09

### Filing Drafter
- File: `filing_drafter.py`
- Model: gpt-4o (expensive)
- Purpose: Generate strategic court filings with objective-based drafting and citation verification
- Status: ACTIVE
- Last updated: 2026-04-09

### Legal Process Guide
- File: `legal_process_guide.py`
- Model: gpt-4o-mini
- Purpose: Guide lawyers through court procedures using curated knowledge base data
- Status: ACTIVE
- Last updated: 2026-04-09

### Condonation Draft
- File: `condonation_draft.py`
- Model: gpt-4o-mini
- Purpose: Generate condonation of delay application for missed deadlines
- Status: ACTIVE
- Last updated: 2026-04-09

### Case Summary (RAG)
- File: `rag_synthesis.py`
- Model: gpt-4o-mini
- Purpose: Synthesize answer from retrieved document chunks with confidence scoring
- Status: ACTIVE
- Last updated: 2026-04-09
- Planned: Phase 1

---

## Prompt Management Rules

### Adding a New Prompt

1. Create file in `backend/services/prompts/feature_name.py`
   ```python
   from backend.services.prompts.base_prompt import PromptTemplate, ModelType
   
   my_prompt = PromptTemplate(
       system_prompt="...",
       user_prompt_template="...",
       model=ModelType.GPT4O_MINI,  # or GPT4O
       version="2024-04-08",
       temperature=0.0,
       description="What this prompt does"
   )
   ```

2. Add to `backend/services/prompts/__init__.py`
   ```python
   from backend.services.prompts.feature_name import my_prompt
   __all__ = ["my_prompt"]
   ```

3. Update this REGISTRY.md
4. Create 10 test cases for regression testing
5. Make a PR with title: `[PROMPT] Feature: description`
6. Get code review approval
7. Merge only after all regression tests pass

### Modifying an Existing Prompt

1. Update the prompt in `backend/services/prompts/feature_name.py`
2. Increment the version: `version="2024-04-09"` (date of change)
3. Update REGISTRY.md with new version and change reason
4. Run all regression tests (must pass 100%)
5. Make a PR describing what changed and why
6. Get code review approval before merging

### Using Prompts in Services

CORRECT:
```python
from backend.services.prompts.base_prompt import extract_document_fields_prompt

user_input = sanitise_user_input(raw_input)
formatted_prompt = extract_document_fields_prompt.format_user_prompt(
    document_content=user_input
)
response = await llm_service.call(
    system_prompt=extract_document_fields_prompt.system_prompt,
    user_prompt=formatted_prompt,
    model=extract_document_fields_prompt.model
)
```

WRONG (NEVER):
```python
# Don't inline prompts in service code
response = await llm_service.call(
    system_prompt="You are...",
    user_prompt=f"Extract from: {user_input}"  # No — injection vector!
)
```

### Regression Testing Template

Every prompt needs 10+ test cases:

```python
# backend/tests/test_prompts.py

import pytest
from backend.services.prompts.base_prompt import extract_document_fields_prompt

@pytest.mark.asyncio
async def test_extract_fields_from_sc_judgment():
    """Test extraction from Supreme Court judgment"""
    test_doc = """
    ... Supreme Court judgment text ...
    """
    
    prompt = extract_document_fields_prompt.format_user_prompt(
        document_content=test_doc
    )
    
    # Call LLM and assert
    result = await llm_service.call(...)
    assert result["case_number"] is not None
    assert result["court"] == "Supreme Court of India"
    assert len(result["parties"]) > 0

@pytest.mark.asyncio
async def test_extract_fields_missing_gracefully():
    """Test that missing fields are handled"""
    test_doc = "Partial document without judge name"
    
    prompt = extract_document_fields_prompt.format_user_prompt(
        document_content=test_doc
    )
    
    result = await llm_service.call(...)
    assert result["judge_name"] is None  # Should be null, not error
```

### CI/CD Integration

Before every production deploy:
```bash
# Run all prompt regression tests
pytest tests/test_prompts.py -v

# Must all pass before allowing merge
# Exit code: 0 = all pass, non-zero = fail and block deploy
```

---

## Prompt Versioning Rules

- Format: YYYY-MM-DD (same as git commit date or decision date)
- Never reuse version numbers
- Version change = public record (in git history)
- Cannot change prompt after RC tag is cut

Example version history:
```
Version 2024-04-08: Initial prompt
Version 2024-04-10: Improved field extraction logic
Version 2024-04-15: Added guardrails for PII handling
(Never go back to 2024-04-08 after RC tag cut)
```

---

## Model Selection Reference

| Use Case | Model | Why |
|----------|-------|-----|
| Document extraction | gpt-4o-mini | Fast, cheap, >95% accuracy needed |
| Case synopsis | gpt-4o-mini | Fast, cheap, structured output |
| Field confidence scoring | gpt-4o-mini | Fast, cheap, simple scoring |
| RAG synthesis | gpt-4o-mini | Retrieval synthesis, speed matters |
| Smart reply generation | gpt-4o-mini | Generate options, cheap at scale |
| Filing drafts | gpt-4o | Expensive but must be highest quality |
| Complex legal reasoning | gpt-4o | Strategy, risk analysis, accuracy > speed |
| Citation verification | gpt-4o-mini | Lookup task, doesn't need reasoning |

Conversions:
- gpt-4o-mini: ~₹0.15 per 1M input tokens, ₹0.60 per 1M output
- gpt-4o: ~₹3 per 1M input tokens, ₹6 per 1M output

---

Last updated: 2024-04-08
"""
