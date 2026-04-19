"""
PDF Extractor — API endpoints

Endpoints:
  POST /api/v1/extract    — extract structured fields from a document

Rules (CLAUDE.md):
- JWT required on every endpoint
- firm_id from JWT only — never from request body
- All business logic in pdf_extractor_service.py — zero logic here
- Wrong firm → 404 not 403
- Amber flag on fields with confidence < 75% (CLAUDE.md Feature #5)
- Standardised response shape on every endpoint
"""
import uuid
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.api.deps import get_db, get_current_user, CurrentUser
from backend.services.pdf_extractor_service import get_pdf_extractor_service, ExtractionResult
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/extract", tags=["extractor"])


# ---------------------------------------------------------------------------
# Request / Response schemas (Pydantic v2)
# ---------------------------------------------------------------------------

class ExtractRequest(BaseModel):
    document_id: str = Field(..., description="UUID of an indexed document")


class FieldResult(BaseModel):
    value: Optional[object] = None
    confidence: int = Field(..., ge=0, le=100, description="Confidence 0-100")
    amber: bool = Field(..., description="True if confidence < 75 and value present")


class ExtractionData(BaseModel):
    document_id: str
    fields: dict[str, FieldResult]


class ExtractResponse(BaseModel):
    success: bool
    data: Optional[ExtractionData] = None
    error: Optional[dict] = None
    meta: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build_extraction_data(result: ExtractionResult) -> ExtractionData:
    return ExtractionData(
        document_id=result.document_id,
        fields={
            name: FieldResult(
                value=field.value,
                confidence=field.confidence,
                amber=field.amber,
            )
            for name, field in result.fields.items()
        },
    )


def _request_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured fields from an indexed document",
)
async def extract_document_fields(
    body: ExtractRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract structured data from a court order, judgment, contract, or legal notice.

    Returns per-field values with confidence scores (0-100).
    Fields with confidence below 75% are flagged amber — verify before relying on them.

    Fields extracted:
    - case_number, petitioner, respondent, court
    - date_of_order, next_hearing_date
    - relief_granted, conditions_imposed
    - amount, judge_name
    """
    service = get_pdf_extractor_service()
    try:
        result = await service.extract_fields(
            db=db,
            document_id=body.document_id,
            firm_id=str(current_user.firm_id),
        )
    except ValueError as exc:
        return ExtractResponse(
            success=False,
            error={
                "code": "validation_error",
                "message": str(exc),
                "action": "check_document_status",
            },
            meta={"request_id": _request_id(), "version": "v1"},
        )
    except RuntimeError as exc:
        logger.error(f"Extraction error user={current_user.user_id}: {exc}")
        return ExtractResponse(
            success=False,
            error={
                "code": "extraction_failed",
                "message": "Field extraction failed. Please try again.",
                "action": "retry",
            },
            meta={"request_id": _request_id(), "version": "v1"},
        )

    return ExtractResponse(
        success=True,
        data=_build_extraction_data(result),
        meta={"request_id": _request_id(), "version": "v1"},
    )
