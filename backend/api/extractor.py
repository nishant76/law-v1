"""
PDF Extractor — API endpoints

Endpoints:
  POST /api/v1/extract        — extract from indexed document
  POST /api/v1/extract/upload — upload and extract immediately

Rules (CLAUDE.md):
- JWT required on every endpoint
- firm_id from JWT only — never from request body
- All business logic in pdf_extractor_service.py — zero logic here
- Wrong firm → 404 not 403
- Standardised response shape on every endpoint
"""
import uuid
import json
import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from backend.api.deps import get_db, get_current_user, CurrentUser
from backend.services.pdf_extractor_service import get_pdf_extractor_service
from backend.services.document_service import get_document_service
from backend.services.llm_service import get_llm_service, ModelType
from backend.models.law_document import Document
from backend.core.logger import get_logger
from backend.core.sanitiser import sanitise_document_text

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/extract", tags=["extractor"])


# ---------------------------------------------------------------------------
# Request / Response schemas (Pydantic v2)
# ---------------------------------------------------------------------------

class ExtractRequest(BaseModel):
    document_id: str = Field(..., description="UUID of an indexed document")


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    document_id: str
    messages: list[ChatMessage] = Field(..., min_length=1)


class ChatData(BaseModel):
    answer: str
    confidence: int
    sources: list


class ChatResponse(BaseModel):
    success: bool
    data: Optional[ChatData] = None
    error: Optional[dict] = None
    meta: dict = Field(default_factory=dict)


class ExtractionData(BaseModel):
    document_id: str
    document_type: dict
    identity_fields: dict
    summary: dict
    primary_objective: dict
    case_narrative: Optional[dict] = None
    case_outcome: Optional[str] = None
    key_stakeholders: list
    critical_deadlines: list
    constraints_and_risks: list
    action_items: list
    citations: list


class ExtractResponse(BaseModel):
    success: bool
    data: Optional[ExtractionData] = None
    error: Optional[dict] = None
    meta: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build_extraction_data(result: dict) -> ExtractionData:
    return ExtractionData(
        document_id=result["document_id"],
        document_type=result.get("document_type", {}),
        identity_fields=result.get("identity_fields", {}),
        summary=result.get("summary", {}),
        primary_objective=result.get("primary_objective", {}),
        case_narrative=result.get("case_narrative"),
        case_outcome=result.get("case_outcome"),
        key_stakeholders=result.get("key_stakeholders") or [],
        critical_deadlines=result.get("critical_deadlines") or [],
        constraints_and_risks=result.get("constraints_and_risks") or [],
        action_items=result.get("action_items") or [],
        citations=result.get("citations") or [],
    )


def _request_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured intelligence from an indexed document",
)
async def extract_document_fields(
    body: ExtractRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
            error={"code": "validation_error", "message": str(exc), "action": "check_document_status"},
            meta={"request_id": _request_id(), "version": "v1"},
        )
    except RuntimeError as exc:
        logger.error(f"Extraction error user={current_user.user_id}: {exc}")
        return ExtractResponse(
            success=False,
            error={"code": "extraction_failed", "message": "Extraction failed. Please try again.", "action": "retry"},
            meta={"request_id": _request_id(), "version": "v1"},
        )

    return ExtractResponse(
        success=True,
        data=_build_extraction_data(result),
        meta={"request_id": _request_id(), "version": "v1"},
    )


@router.post(
    "/upload",
    response_model=ExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a file and extract intelligence immediately — no indexing required",
)
async def extract_from_upload(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    MAX_BYTES = 50 * 1024 * 1024

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ("pdf", "docx"):
        return ExtractResponse(
            success=False,
            error={"code": "unsupported_format", "message": "Only PDF and DOCX files are supported.", "action": "upload_supported_format"},
            meta={"request_id": _request_id(), "version": "v1"},
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_BYTES:
        return ExtractResponse(
            success=False,
            error={"code": "file_too_large", "message": "File exceeds 50 MB limit.", "action": "reduce_file_size"},
            meta={"request_id": _request_id(), "version": "v1"},
        )

    service = get_pdf_extractor_service()
    try:
        result, raw_text = await service.extract_fields_from_bytes(
            file_bytes=file_bytes,
            file_ext=ext,
            firm_id=str(current_user.firm_id),
        )
    except ValueError as exc:
        return ExtractResponse(
            success=False,
            error={"code": "validation_error", "message": str(exc), "action": "check_file"},
            meta={"request_id": _request_id(), "version": "v1"},
        )
    except RuntimeError as exc:
        logger.error(f"Direct extraction error user={current_user.user_id}: {exc}")
        return ExtractResponse(
            success=False,
            error={"code": "extraction_failed", "message": "Extraction failed. Please try again.", "action": "retry"},
            meta={"request_id": _request_id(), "version": "v1"},
        )

    # Save the extracted text immediately so /extract/chat works without Celery.
    try:
        doc_service = get_document_service()
        doc = await doc_service.store_document_in_db(
            session=db,
            firm_id=str(current_user.firm_id),
            matter_id=None,
            filename=file.filename or "upload",
            file_type=ext,
            file_size_bytes=len(file_bytes),
            blob_path=f"extractor/{current_user.firm_id}/{file.filename}",
            user_id=str(current_user.user_id),
        )
        await doc_service.update_document_indexed(
            session=db,
            document_id=str(doc.id),
            chunk_count=0,
            ocr_text=raw_text,
        )
        result["document_id"] = str(doc.id)
    except Exception as exc:
        logger.warning(f"Could not persist extractor doc for chat (non-fatal): {exc}")
        # Chat won't be available but extraction result is still returned.

    return ExtractResponse(
        success=True,
        data=_build_extraction_data(result),
        meta={"request_id": _request_id(), "version": "v1"},
    )


@router.post(
    "/upload/stream",
    summary="Upload and extract with real-time SSE progress",
)
async def extract_from_upload_stream(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Runs the extraction as a background asyncio task and sends heartbeat
    SSE events every 2 seconds while it runs. Heartbeats force nginx/proxy
    buffers to flush so the client sees stage updates immediately.

    SSE event types:
      progress  {"stage": "reading"|"analysing"|"generating", "message": str, "pct"?: int}
      result    {"data": <ExtractionData dict>}
      error     {"code": str, "message": str}
      done      {}
    """
    MAX_BYTES = 50 * 1024 * 1024

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    file_bytes = await file.read()

    def _sse(payload: dict) -> str:
        # Pad to 256 bytes so proxies that buffer on minimum-chunk-size flush immediately
        line = f"data: {json.dumps(payload)}"
        padding = max(0, 256 - len(line) - 4)
        return line + (" " * padding) + "\n\n"

    async def generate():
        if ext not in ("pdf", "docx"):
            yield _sse({"type": "error", "code": "unsupported_format",
                        "message": "Only PDF and DOCX files are supported."})
            yield _sse({"type": "done"})
            return

        if len(file_bytes) > MAX_BYTES:
            yield _sse({"type": "error", "code": "file_too_large",
                        "message": "File exceeds 50 MB limit."})
            yield _sse({"type": "done"})
            return

        # ── Fire extraction as a background task ─────────────────────────────
        # This lets the generator keep running (heartbeats) while the LLM works.
        service = get_pdf_extractor_service()
        task = asyncio.create_task(
            service.extract_fields_from_bytes(
                file_bytes=file_bytes,
                file_ext=ext,
                firm_id=str(current_user.firm_id),
            )
        )

        # Immediate first event — arrives at browser in < 1 s
        yield _sse({"type": "progress", "stage": "reading",
                    "message": "Reading document…"})

        # Let the event loop hand control to the task for a moment
        await asyncio.sleep(0.05)
        yield _sse({"type": "progress", "stage": "analysing",
                    "message": "Analysing with AI…"})

        # ── Heartbeat loop — every 2 s until task completes ───────────────────
        # Regular yields force nginx / any proxy to flush its write buffer.
        elapsed = 0
        EXPECTED_SECONDS = 35   # conservative estimate for progress %
        while not task.done():
            await asyncio.sleep(2)
            elapsed += 2
            pct = min(int(elapsed / EXPECTED_SECONDS * 100), 94)
            yield _sse({"type": "progress", "stage": "generating",
                        "message": "Extracting fields…", "pct": pct})

        # ── Task finished — get result ────────────────────────────────────────
        try:
            result, raw_text = task.result()
        except ValueError as exc:
            yield _sse({"type": "error", "code": "validation_error", "message": str(exc)})
            yield _sse({"type": "done"})
            return
        except Exception as exc:
            logger.error(f"Stream extraction error user={current_user.user_id}: {exc}")
            yield _sse({"type": "error", "code": "extraction_failed",
                        "message": "Extraction failed. Please try again."})
            yield _sse({"type": "done"})
            return

        # ── Persist for /extract/chat ─────────────────────────────────────────
        try:
            doc_service = get_document_service()
            doc = await doc_service.store_document_in_db(
                session=db,
                firm_id=str(current_user.firm_id),
                matter_id=None,
                filename=file.filename or "upload",
                file_type=ext,
                file_size_bytes=len(file_bytes),
                blob_path=f"extractor/{current_user.firm_id}/{file.filename}",
                user_id=str(current_user.user_id),
            )
            await doc_service.update_document_indexed(
                session=db,
                document_id=str(doc.id),
                chunk_count=0,
                ocr_text=raw_text or "",
            )
            result["document_id"] = str(doc.id)
        except Exception as exc:
            logger.warning(f"Could not persist streamed doc for chat: {exc}")

        extraction = _build_extraction_data(
            {"document_id": result.get("document_id", "direct"), **result}
        )
        yield _sse({"type": "result", "data": extraction.model_dump()})
        yield _sse({"type": "done"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",       # nginx: disable proxy buffering
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question about an indexed document",
)
async def chat_with_document(
    body: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).where(
        Document.id == uuid.UUID(body.document_id),
        Document.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    doc: Optional[Document] = result.scalar_one_or_none()

    if doc is None or str(doc.firm_id) != str(current_user.firm_id):
        return ChatResponse(
            success=False,
            error={"code": "not_found", "message": "Document not found.", "action": "check_document_id"},
            meta={"request_id": _request_id(), "version": "v1"},
        )

    if not doc.ocr_text:
        return ChatResponse(
            success=False,
            error={"code": "no_text", "message": "Document has no extractable text.", "action": "re_upload"},
            meta={"request_id": _request_id(), "version": "v1"},
        )

    safe_text = sanitise_document_text(doc.ocr_text)

    # ── Context window: use full document text up to 100,000 chars ────────────
    # GPT-4o-mini supports 128k tokens (~96k words / ~480k chars).
    # Previous limit of 12,000 chars was cutting 11-page court orders in half —
    # pages 5-11 (where legal analysis typically lives) were never seen.
    # 100,000 chars comfortably fits any court document up to ~60 pages.
    doc_context = safe_text[:100_000]

    system_prompt = (
        "You are a senior legal research assistant for Indian lawyers practising in "
        "Punjab, Haryana and Chandigarh courts.\n\n"
        "You answer questions about the document provided below.\n\n"

        "RULES:\n"
        "1. CONCEPTUAL EQUIVALENCE — check whether the concept is present under "
        "different terminology before saying not found.\n"
        "   • 'vicarious liability'  = employer liable before MACT, recovery from "
        "employee, Corporation paid compensation\n"
        "   • 'natural justice'      = opportunity of hearing, show cause notice, "
        "audi alteram partem\n"
        "   • 'estoppel'             = cannot change stand, Section 115 Evidence Act\n"
        "   • 'res judicata'         = matter already decided, cannot reopen\n"
        "2. NEVER FABRICATE — do not infer beyond what the document states.\n"
        "3. CITE THE DOCUMENT — mention paragraph, heading, or page when visible.\n"
        "4. COMPLETELY UNRELATED question — set answer to the single sentence "
        "'This document does not cover that topic.' and confidence to 0.\n\n"
        "Always respond with valid JSON only. No markdown. No preamble.\n\n"
        "Response format:\n"
        "{\n"
        '  "answer": "your answer here",\n'
        '  "confidence": 8,\n'
        '  "concept_found_as": "exact terminology the document uses, or null",\n'
        '  "sources": [{"location": "para 5 / page 3 / heading X"}]\n'
        "}\n\n"
        "Confidence scale: 10=exact phrase present, 8=concept clearly present under "
        "different term, 6=partially addressed, 4=tangential, 2=barely related, "
        "0=not present or unrelated.\n\n"
        f"Document content:\n{doc_context}"
    )

    # Keep last 10 messages to control token cost
    history = body.messages[-10:]
    llm_messages = [{"role": msg.role, "content": msg.content} for msg in history]

    llm = get_llm_service()
    try:
        raw = await asyncio.wait_for(
            llm.call_chat_completion(
                system_prompt=system_prompt,
                messages=llm_messages,
                model=ModelType.GPT4O_MINI,
                temperature=0.0,
                max_tokens=1000,
                firm_id=str(current_user.firm_id),
                timeout=60,
            ),
            timeout=65.0,
        )
    except asyncio.TimeoutError:
        return ChatResponse(
            success=False,
            error={"code": "timeout", "message": "Request timed out. Please try again.", "action": "retry"},
            meta={"request_id": _request_id(), "version": "v1"},
        )
    except Exception as exc:
        logger.error(f"Chat error user={current_user.user_id}: {exc}")
        return ChatResponse(
            success=False,
            error={"code": "chat_failed", "message": "Could not answer. Please try again.", "action": "retry"},
            meta={"request_id": _request_id(), "version": "v1"},
        )

    # Parse structured JSON response — confidence comes from the model, not keyword scanning
    import json as _json, re as _re
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = _re.sub(r"^```[a-z]*\n?", "", cleaned)
            cleaned = _re.sub(r"\n?```$", "", cleaned.strip())
        parsed = _json.loads(cleaned)
        answer = parsed.get("answer", raw)
        confidence = int(parsed.get("confidence", 8))
        sources = parsed.get("sources", [])
    except Exception:
        # LLM returned plain text — use as-is with neutral confidence
        answer = raw
        confidence = 8
        sources = []

    return ChatResponse(
        success=True,
        data=ChatData(answer=answer, confidence=confidence, sources=sources),
        meta={"request_id": _request_id(), "version": "v1"},
    )
