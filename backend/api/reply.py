"""
Reply API endpoints — Smart Reply Generator

Endpoints:
  POST /api/v1/reply/upload              — upload notice file → extract allegations (one call)
  POST /api/v1/reply/generate            — generate reply from allegation stances
  GET  /api/v1/reply/{draft_id}/export   — download reply as .docx

Rules (CLAUDE.md):
- JWT required on every endpoint
- firm_id from JWT only — never from request body
- All business logic in reply_service.py — zero logic here
- Wrong firm → 404 not 403
- Standardised response shape on every endpoint
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user, CurrentUser
from backend.services.reply_service import get_reply_service
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/reply", tags=["reply"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AllegationItem(BaseModel):
    point_number: int
    allegation: str
    legal_basis_claimed: Optional[str] = None


class NoticeExtractionData(BaseModel):
    document_id: str
    sender: Optional[str] = None
    recipient: Optional[str] = None
    notice_date: Optional[str] = None
    notice_type: str = "other"
    allegations: List[AllegationItem] = []


class AllegationResponse(BaseModel):
    point_number: int
    allegation: str = ""
    stance: str = "deny"   # admit | deny | partial
    grounds: str = ""
    legal_basis_claimed: Optional[str] = None


class GenerateReplyRequest(BaseModel):
    document_id: str
    allegation_responses: List[AllegationResponse] = Field(..., min_length=1)


class ReplyGeneratedData(BaseModel):
    draft_id: str
    reply_text: str


class RewriteGroundsRequest(BaseModel):
    allegation: str = ""
    stance: str = "deny"
    facts: str = Field(..., min_length=1)


class StandardResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None
    meta: dict = Field(default_factory=dict)


def _request_id() -> str:
    return str(uuid.uuid4())


def _meta() -> dict:
    return {"request_id": _request_id(), "version": "v1"}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    status_code=status.HTTP_200_OK,
    summary="Upload legal notice and extract allegations in one call",
)
async def upload_and_extract(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a legal notice PDF/DOCX and extract all allegations immediately."""
    MAX_BYTES = 50 * 1024 * 1024
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()

    if ext not in ("pdf", "docx"):
        return StandardResponse(
            success=False,
            error={"code": "unsupported_format", "message": "Only PDF and DOCX files are supported.", "action": "upload_supported_format"},
            meta=_meta(),
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_BYTES:
        return StandardResponse(
            success=False,
            error={"code": "file_too_large", "message": "File exceeds 50 MB limit.", "action": "reduce_file_size"},
            meta=_meta(),
        )

    service = get_reply_service()

    # Store document for later use in generate
    document_id = "direct"
    try:
        from backend.services.document_service import get_document_service
        doc_service = get_document_service()
        doc = await doc_service.store_document_in_db(
            session=db,
            firm_id=str(current_user.firm_id),
            matter_id=None,
            filename=file.filename or "notice",
            file_type=ext,
            file_size_bytes=len(file_bytes),
            blob_path=f"reply/{current_user.firm_id}/{file.filename}",
            user_id=str(current_user.user_id),
        )
        # Extract text and store on doc for generate step
        raw_text = ""
        if ext == "pdf":
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(file_bytes))
            raw_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == "docx":
            from docx import Document as DocxDocument
            import io
            doc_obj = DocxDocument(io.BytesIO(file_bytes))
            raw_text = "\n".join(p.text for p in doc_obj.paragraphs)
        await doc_service.update_document_indexed(
            session=db,
            document_id=str(doc.id),
            chunk_count=0,
            ocr_text=raw_text,
        )
        document_id = str(doc.id)
    except Exception as exc:
        logger.warning(f"Could not persist reply notice doc (non-fatal): {exc}")

    try:
        extraction = await service.extract_allegations_from_bytes(
            file_bytes=file_bytes,
            file_ext=ext,
            firm_id=str(current_user.firm_id),
        )
    except ValueError as exc:
        return StandardResponse(
            success=False,
            error={"code": "validation_error", "message": str(exc), "action": "check_file"},
            meta=_meta(),
        )
    except RuntimeError as exc:
        logger.error(f"Reply upload extraction error user={current_user.user_id}: {exc}")
        return StandardResponse(
            success=False,
            error={"code": "extraction_failed", "message": "Could not extract allegations. Please try again.", "action": "retry"},
            meta=_meta(),
        )

    return StandardResponse(
        success=True,
        data={"document_id": document_id, **extraction},
        meta=_meta(),
    )


@router.post(
    "/generate",
    status_code=status.HTTP_200_OK,
    summary="Generate complete formal reply from allegation stances",
)
async def generate_reply(
    body: GenerateReplyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a complete formal reply to the legal notice."""
    service = get_reply_service()
    try:
        draft_id, reply_text = await service.generate_reply(
            document_id=body.document_id,
            firm_id=str(current_user.firm_id),
            allegation_responses=[r.model_dump() for r in body.allegation_responses],
            session=db,
        )
    except ValueError as exc:
        return StandardResponse(
            success=False,
            error={"code": "validation_error", "message": str(exc), "action": "retry"},
            meta=_meta(),
        )
    except RuntimeError as exc:
        logger.error(f"Reply generation error user={current_user.user_id}: {exc}")
        return StandardResponse(
            success=False,
            error={"code": "generation_failed", "message": "Reply generation failed. Please try again.", "action": "retry"},
            meta=_meta(),
        )

    return StandardResponse(
        success=True,
        data={"draft_id": draft_id, "reply_text": reply_text},
        meta=_meta(),
    )


@router.post(
    "/rewrite-grounds",
    status_code=status.HTTP_200_OK,
    summary="Rewrite a lawyer's rough factual notes into formal legal grounds",
)
async def rewrite_grounds(
    body: RewriteGroundsRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Improve the language of the lawyer's notes — never adds facts or citations."""
    service = get_reply_service()
    try:
        rewritten = await service.rewrite_grounds(
            allegation=body.allegation,
            stance=body.stance,
            facts=body.facts,
            firm_id=str(current_user.firm_id),
        )
    except ValueError as exc:
        return StandardResponse(
            success=False,
            error={"code": "validation_error", "message": str(exc), "action": "retry"},
            meta=_meta(),
        )
    except RuntimeError as exc:
        logger.error(f"Grounds rewrite error user={current_user.user_id}: {exc}")
        return StandardResponse(
            success=False,
            error={"code": "rewrite_failed", "message": "Could not rewrite the notes. Please try again.", "action": "retry"},
            meta=_meta(),
        )

    return StandardResponse(success=True, data={"rewritten_grounds": rewritten}, meta=_meta())


@router.get(
    "/{draft_id}/export",
    summary="Download reply draft as .docx",
    responses={
        200: {
            "content": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}},
            "description": "Word document (.docx) containing the reply",
        }
    },
)
async def export_reply_docx(
    draft_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_reply_service()
    try:
        file_bytes = await service.export_reply_docx(
            draft_id=draft_id,
            firm_id=str(current_user.firm_id),
            session=db,
        )
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Reply docx export error draft={draft_id}: {exc}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Export failed. Please try again.")

    return Response(
        content=file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="reply_{draft_id}.docx"'},
    )
