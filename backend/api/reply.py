"""
Reply API endpoints
Handles Smart Reply Generator workflow: extract allegations, get legal grounds, generate reply
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from backend.api.deps import get_current_user, get_db
from backend.services.reply_service import get_reply_service
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/reply/extract-allegations", response_model=dict)
async def extract_allegations(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 1: Extract allegations from legal notice

    Args:
        document_id: ID of the uploaded legal notice document

    Returns:
        Extracted allegations with metadata
    """
    try:
        service = get_reply_service()
        result = await service.extract_allegations(
            document_id=document_id,
            firm_id=current_user["firm_id"],
            session=db,
        )

        return {
            "success": True,
            "data": result,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to extract allegations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract allegations",
        )


@router.post("/reply/legal-grounds", response_model=dict)
async def get_legal_grounds(
    allegation: str,
    matter_type: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Get legal grounds for denying an allegation

    Args:
        allegation: The allegation text
        matter_type: Type of matter (property, cheque, employment, etc.)

    Returns:
        Suggested legal grounds with citations
    """
    try:
        service = get_reply_service()
        result = await service.get_legal_grounds(
            allegation=allegation,
            matter_type=matter_type,
            firm_id=current_user["firm_id"],
            session=db,
        )

        return {
            "success": True,
            "data": result,
        }

    except Exception as e:
        logger.error(f"Failed to get legal grounds: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get legal grounds",
        )


@router.post("/reply/generate", response_model=dict)
async def generate_reply(
    document_id: str,
    allegation_responses: List[Dict[str, Any]],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3: Generate complete reply incorporating lawyer's decisions

    Args:
        document_id: Original notice document ID
        allegation_responses: List of {"point_number": int, "stance": "admit/deny/partial", "grounds": str}

    Returns:
        Generated reply draft details
    """
    try:
        service = get_reply_service()
        draft = await service.generate_reply(
            document_id=document_id,
            firm_id=current_user["firm_id"],
            allegation_responses=allegation_responses,
            session=db,
        )

        return {
            "success": True,
            "data": {
                "draft_id": str(draft.id),
                "title": draft.title,
                "status": draft.status.value,
                "confidence_score": draft.confidence_score,
            },
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to generate reply: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate reply",
        )


@router.get("/reply/{draft_id}/export")
async def export_reply_docx(
    draft_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export reply draft as .docx file

    Args:
        draft_id: Draft ID to export

    Returns:
        DOCX file download
    """
    try:
        service = get_reply_service()
        docx_content = await service.export_reply_docx(
            draft_id=draft_id,
            firm_id=current_user["firm_id"],
            session=db,
        )

        # Return as downloadable file
        return StreamingResponse(
            io.BytesIO(docx_content),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=reply_{draft_id}.docx"},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to export DOCX: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export DOCX",
        )