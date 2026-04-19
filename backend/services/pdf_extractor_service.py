"""
PDF Extractor Service
Business logic for PDF Extractor (Feature #5 in CLAUDE.md).

Flow:
  extract_fields(document_id, firm_id)
    1. Load document — verify firm ownership (404 if wrong firm)
    2. Sanitise OCR text (GAP-001)
    3. Call GPT-4o-mini via LLMService with pdf_extractor prompt
    4. Parse JSON, add amber flags for fields below 75% confidence
    5. Return ExtractionResult

Rules:
- All AI calls through LLMService only
- firm_id from JWT — never trusted from caller outside service
- Never log document content or PII (GAP-032)
- Amber threshold: < 75% confidence (CLAUDE.md Feature #5)
"""
import json
import uuid
import asyncio
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.law_document import Document, DocumentStatus
from backend.services.llm_service import get_llm_service, LLMService, ModelType
from backend.services.prompts.pdf_extractor import pdf_extractor_prompt, AMBER_CONFIDENCE_THRESHOLD
from backend.core.logger import get_logger
from backend.core.sanitiser import sanitise_document_text

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class ExtractedField:
    """Single extracted field with value and confidence"""

    def __init__(self, field_name: str, value, confidence: int):
        self.field_name = field_name
        self.value = value
        self.confidence = confidence
        # Amber flag: present but below threshold
        self.amber = (value is not None) and (confidence < AMBER_CONFIDENCE_THRESHOLD)

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "confidence": self.confidence,
            "amber": self.amber,
        }


class ExtractionResult:
    """Full extraction result for a document"""

    # Fields the prompt returns (matches OUTPUT_SCHEMA in pdf_extractor.py)
    EXPECTED_FIELDS = [
        "case_number",
        "petitioner",
        "respondent",
        "court",
        "date_of_order",
        "next_hearing_date",
        "relief_granted",
        "conditions_imposed",
        "amount",
        "judge_name",
    ]

    def __init__(self, document_id: str, fields: dict[str, ExtractedField]):
        self.document_id = document_id
        self.fields = fields

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "fields": {name: field.to_dict() for name, field in self.fields.items()},
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_extraction_json(raw_response: str) -> dict:
    """
    Parse LLM JSON response. Strip markdown fences if present.
    Returns dict mapping field_name → {value, confidence}.
    """
    text = raw_response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error(f"Failed to parse extraction JSON: {exc} — raw={text[:200]}")
        raise ValueError(f"LLM returned non-JSON response: {exc}") from exc

    return data


def _build_extraction_result(document_id: str, parsed: dict) -> ExtractionResult:
    """
    Convert raw parsed dict to ExtractionResult with amber flags.
    Falls back to value=None, confidence=0 for any missing field.
    """
    fields: dict[str, ExtractedField] = {}
    for field_name in ExtractionResult.EXPECTED_FIELDS:
        raw = parsed.get(field_name, {})
        if isinstance(raw, dict):
            value = raw.get("value")
            confidence = int(raw.get("confidence", 0))
        else:
            value = None
            confidence = 0
        fields[field_name] = ExtractedField(field_name, value, confidence)
    return ExtractionResult(document_id=document_id, fields=fields)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class PDFExtractorService:

    def __init__(self, llm_service: LLMService):
        self._llm = llm_service

    async def extract_fields(
        self,
        db: AsyncSession,
        document_id: str,
        firm_id: str,
    ) -> ExtractionResult:
        """
        Extract structured fields from an already-indexed document.

        Args:
            db:          Async DB session
            document_id: UUID of the document
            firm_id:     Firm ID from JWT — used for ownership check

        Returns:
            ExtractionResult with per-field values and confidence scores.
            Fields with confidence < 75% have amber=True.

        Raises:
            ValueError:  Document not found / wrong firm / not indexed
            RuntimeError: LLM call failed
        """
        # ------------------------------------------------------------------
        # 1. Load document and verify firm ownership
        # ------------------------------------------------------------------
        stmt = select(Document).where(
            Document.id == uuid.UUID(document_id),
            Document.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        doc: Optional[Document] = result.scalar_one_or_none()

        if doc is None or str(doc.firm_id) != firm_id:
            raise ValueError("Document not found")

        if doc.status != DocumentStatus.INDEXED:
            raise ValueError(
                f"Document is not yet indexed (status={doc.status.value}). "
                "Please wait for indexing to complete before extracting fields."
            )

        if not doc.ocr_text:
            raise ValueError(
                "Document has no extracted text. "
                "Re-upload the document or check if OCR failed."
            )

        # ------------------------------------------------------------------
        # 2. Sanitise (GAP-001)
        # ------------------------------------------------------------------
        safe_text = sanitise_document_text(doc.ocr_text)

        # ------------------------------------------------------------------
        # 3. Call LLM
        # ------------------------------------------------------------------
        logger.info(f"Extracting fields document={document_id} firm={firm_id}")

        try:
            raw_response = await asyncio.wait_for(
                self._llm.call_completion(
                    system_prompt=pdf_extractor_prompt.system_prompt,
                    user_prompt=pdf_extractor_prompt.format_user_prompt(
                        document_text=safe_text
                    ),
                    model=ModelType.GPT4O_MINI,
                    temperature=0.0,
                    max_tokens=pdf_extractor_prompt.max_tokens,
                    firm_id=firm_id,
                    timeout=90,
                ),
                timeout=90.0
            )
        except asyncio.TimeoutError:
            logger.error(f"AI request timed out after 90s for PDF extraction document={document_id}")
            raise RuntimeError("AI request timed out — please try again")
        except Exception as exc:
            logger.error(f"LLM failed for extraction document={document_id}: {exc}")
            raise RuntimeError(f"Field extraction failed: {exc}") from exc

        # ------------------------------------------------------------------
        # 4. Parse and return with amber flags
        # ------------------------------------------------------------------
        try:
            parsed = _parse_extraction_json(raw_response)
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc

        extraction = _build_extraction_result(document_id, parsed)

        amber_fields = [
            name for name, f in extraction.fields.items() if f.amber
        ]
        if amber_fields:
            logger.info(
                f"Amber fields document={document_id}: {amber_fields}"
                # note: not logging values — GAP-032 (no PII in logs)
            )

        return extraction


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_pdf_extractor_service: Optional[PDFExtractorService] = None


def get_pdf_extractor_service() -> PDFExtractorService:
    global _pdf_extractor_service
    if _pdf_extractor_service is None:
        _pdf_extractor_service = PDFExtractorService(llm_service=get_llm_service())
    return _pdf_extractor_service
