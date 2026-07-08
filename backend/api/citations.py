"""
Citations API — serves the self-hosted judgment PDF and on-demand AI summary.

The primary "View Judgment" link points here, NOT at the raw government URL,
so it can never break (LAUNCH QUALITY MANDATE). We serve our own copy of the
public-domain judgment (Copyright Act §52(1)(q)). The official government link
is exposed separately as a secondary "View on official source" link.
"""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.models.law_citation import Citation
from backend.services.llm_service import get_llm_service, ModelType
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/citations", tags=["citations"])

# Same local store the verifier writes to. blob_path is storage-agnostic — when
# we move to Azure Blob, swap this body for a blob download/redirect.
JUDGMENT_DIR = Path(__file__).parent.parent.parent / "data" / "judgments"

_SUMMARY_SYSTEM = (
    "You are a legal research assistant for Indian lawyers. "
    "Summarise judgments concisely so a lawyer can quickly decide relevance."
)

_SUMMARY_USER = """\
Summarise this Indian court judgment in 2–3 sentences for a lawyer deciding whether to cite it.
Cover: (1) what the dispute is about, (2) the key legal point decided, (3) the outcome.
Be specific. Do not start with "This judgment".

{text}"""


@router.get("/{citation_id}/pdf")
async def get_citation_pdf(
    citation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Stream our self-hosted copy of the judgment PDF."""
    try:
        cid = uuid.UUID(citation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")

    stmt = select(Citation).where(Citation.id == cid, Citation.deleted_at.is_(None))
    citation = (await db.execute(stmt)).scalar_one_or_none()

    if citation is None or not citation.blob_path or citation.link_status != "self_hosted":
        # Never reveal partial state — a citation without a working copy is a 404.
        raise HTTPException(status_code=404, detail="Judgment not available")

    file_path = JUDGMENT_DIR / f"{cid}.pdf"
    if not file_path.exists():
        logger.warning(f"blob_path set but file missing for citation {cid}: {file_path}")
        raise HTTPException(status_code=404, detail="Judgment not available")

    safe_name = (citation.citation_key or str(cid)).replace("/", "-")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"{safe_name}.pdf",
    )


@router.get("/{citation_id}/summary")
async def get_citation_summary(
    citation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return a 2–3 sentence AI summary of the judgment.
    Generated on first request via GPT-4o-mini and cached in citations.summary.
    Returns {"summary": null} when no text is available.
    """
    try:
        cid = uuid.UUID(citation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")

    stmt = select(Citation).where(Citation.id == cid, Citation.deleted_at.is_(None))
    citation = (await db.execute(stmt)).scalar_one_or_none()
    if citation is None:
        raise HTTPException(status_code=404, detail="Not found")

    # Return cached summary immediately
    if citation.summary:
        return {"summary": citation.summary}

    if not citation.judgment_text:
        return {"summary": None}

    try:
        llm = get_llm_service()
        text_snippet = citation.judgment_text[:3500]
        raw = await llm.call_completion(
            system_prompt=_SUMMARY_SYSTEM,
            user_prompt=_SUMMARY_USER.format(text=text_snippet),
            model=ModelType.GPT4O_MINI,
            temperature=0.0,
            max_tokens=160,
        )
        summary: Optional[str] = raw.strip() if raw else None
    except Exception as e:
        logger.warning(f"get_citation_summary: LLM failed for {cid}: {e}")
        summary = None

    if summary:
        citation.summary = summary
        await db.commit()

    return {"summary": summary}
