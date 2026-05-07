"""
Case Synopsis Generator — API endpoints

Endpoints:
  POST /api/v1/synopsis/generate       — generate synopsis from document
  GET  /api/v1/synopsis/{synopsis_id}  — retrieve a generated synopsis
  GET  /api/v1/synopsis/{synopsis_id}/export — download as .docx

Rules (CLAUDE.md):
- JWT required on every endpoint
- firm_id from JWT only — never from request body
- All business logic in synopsis_service.py — zero logic here
- Wrong firm → 404 not 403
- Standardised response shape on every endpoint
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.api.deps import get_db, get_current_user, CurrentUser
from backend.services.synopsis_service import get_synopsis_service, SynopsisResult
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/synopsis", tags=["synopsis"])


# ---------------------------------------------------------------------------
# Request / Response schemas (Pydantic v2)
# ---------------------------------------------------------------------------

class GenerateSynopsisRequest(BaseModel):
    document_id: str = Field(..., description="UUID of an indexed document")


class SynopsisData(BaseModel):
    synopsis_id: str
    document_id: str
    case_name: Optional[str]
    petitioner: Optional[str]
    respondent: Optional[str]
    court: Optional[str]
    judgment_date: Optional[str]
    case_number: Optional[str]
    facts: Optional[str]
    issues: list[str]
    held: Optional[str]
    citations_used: list[str]
    relief_granted: Optional[str]
    confidence: int = Field(..., ge=0, le=10, description="AI confidence score 0-10")
    created_at: str

    class Config:
        from_attributes = True


class SynopsisResponse(BaseModel):
    success: bool
    data: Optional[SynopsisData] = None
    error: Optional[dict] = None
    meta: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _synopsis_to_data(result: SynopsisResult) -> SynopsisData:
    return SynopsisData(
        synopsis_id=result.synopsis_id,
        document_id=result.document_id,
        case_name=result.case_name,
        petitioner=result.petitioner,
        respondent=result.respondent,
        court=result.court,
        judgment_date=result.judgment_date,
        case_number=result.case_number,
        facts=result.facts,
        issues=result.issues,
        held=result.held,
        citations_used=result.citations_used,
        relief_granted=result.relief_granted,
        confidence=result.confidence,
        created_at=result.created_at.isoformat(),
    )


def _request_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=SynopsisResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a file and generate synopsis immediately — no prior indexing required",
)
async def generate_synopsis_from_upload(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    MAX_BYTES = 50 * 1024 * 1024
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ("pdf", "docx"):
        return SynopsisResponse(
            success=False,
            error={"code": "unsupported_format", "message": "Only PDF and DOCX files are supported.", "action": "upload_supported_format"},
            meta={"request_id": _request_id(), "version": "v1"},
        )
    file_bytes = await file.read()
    if len(file_bytes) > MAX_BYTES:
        return SynopsisResponse(
            success=False,
            error={"code": "file_too_large", "message": "File exceeds 50 MB limit.", "action": "reduce_file_size"},
            meta={"request_id": _request_id(), "version": "v1"},
        )
    service = get_synopsis_service()
    try:
        result = await service.generate_synopsis_from_bytes(
            file_bytes=file_bytes,
            file_ext=ext,
            firm_id=str(current_user.firm_id),
        )
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("WRONG_DOCUMENT_TYPE:"):
            doc_type = msg.split(":", 1)[1]
            return SynopsisResponse(
                success=False,
                error={
                    "code": "wrong_document_type",
                    "document_type": doc_type,
                    "message": f"This document appears to be a {doc_type.replace('_', ' ')}, not a court judgment or petition.",
                    "action": "use_appropriate_tool",
                },
                meta={"request_id": _request_id(), "version": "v1"},
            )
        logger.error(f"Synopsis upload error user={current_user.user_id}: {exc}", exc_info=True)
        return SynopsisResponse(
            success=False,
            error={"code": "generation_failed", "message": msg, "action": "retry"},
            meta={"request_id": _request_id(), "version": "v1"},
        )
    except RuntimeError as exc:
        logger.error(f"Synopsis upload error user={current_user.user_id}: {exc}", exc_info=True)
        return SynopsisResponse(
            success=False,
            error={"code": "generation_failed", "message": str(exc), "action": "retry"},
            meta={"request_id": _request_id(), "version": "v1"},
        )
    except Exception as exc:
        logger.error(f"Synopsis upload unexpected error: {exc}", exc_info=True)
        return SynopsisResponse(
            success=False,
            error={"code": "generation_failed", "message": str(exc), "action": "retry"},
            meta={"request_id": _request_id(), "version": "v1"},
        )
    return SynopsisResponse(
        success=True,
        data=_synopsis_to_data(result),
        meta={"request_id": _request_id(), "version": "v1"},
    )


@router.post(
    "/generate",
    response_model=SynopsisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate case synopsis from an indexed document",
)
async def generate_synopsis(
    body: GenerateSynopsisRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a structured case synopsis from an already-indexed document.

    - Extracts: parties, facts, issues, held, citations used, relief granted
    - Confidence score 0-10 on every response
    - Stores result in law.drafts for later retrieval and export
    """
    service = get_synopsis_service()
    try:
        result = await service.generate_synopsis(
            db=db,
            document_id=body.document_id,
            firm_id=str(current_user.firm_id),
            user_id=str(current_user.user_id),
        )
    except ValueError as exc:
        # Includes "not found" and "not indexed" errors
        return SynopsisResponse(
            success=False,
            error={
                "code": "validation_error",
                "message": str(exc),
                "action": "check_document_status",
            },
            meta={"request_id": _request_id(), "version": "v1"},
        )
    except RuntimeError as exc:
        logger.error(f"Synopsis generation error user={current_user.user_id}: {exc}")
        return SynopsisResponse(
            success=False,
            error={
                "code": "generation_failed",
                "message": "Synopsis generation failed. Please try again.",
                "action": "retry",
            },
            meta={"request_id": _request_id(), "version": "v1"},
        )

    return SynopsisResponse(
        success=True,
        data=_synopsis_to_data(result),
        meta={"request_id": _request_id(), "version": "v1"},
    )


@router.get(
    "/{synopsis_id}",
    response_model=SynopsisResponse,
    summary="Retrieve a previously generated synopsis",
)
async def get_synopsis(
    synopsis_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a previously generated case synopsis by its ID.
    """
    service = get_synopsis_service()
    try:
        result = await service.get_synopsis(
            db=db,
            synopsis_id=synopsis_id,
            firm_id=str(current_user.firm_id),
        )
    except ValueError as exc:
        return SynopsisResponse(
            success=False,
            error={
                "code": "not_found",
                "message": str(exc),
                "action": "check_synopsis_id",
            },
            meta={"request_id": _request_id(), "version": "v1"},
        )

    return SynopsisResponse(
        success=True,
        data=_synopsis_to_data(result),
        meta={"request_id": _request_id(), "version": "v1"},
    )


@router.get(
    "/{synopsis_id}/export",
    summary="Download synopsis as a formatted .docx file",
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            },
            "description": "Word document (.docx) containing the formatted synopsis",
        }
    },
)
async def export_synopsis_docx(
    synopsis_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export a generated synopsis as a formatted .docx file ready to download.

    Returns the Word document as a binary file download.
    """
    service = get_synopsis_service()
    try:
        file_bytes, filename = await service.export_synopsis_docx(
            db=db,
            synopsis_id=synopsis_id,
            firm_id=str(current_user.firm_id),
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DOCX export dependency (python-docx) not installed.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except RuntimeError as exc:
        logger.error(f"Docx export error synopsis={synopsis_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export failed. Please try again.",
        )

    return Response(
        content=file_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
