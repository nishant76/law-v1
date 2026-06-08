"""
Legal Process API — procedural guidance endpoints
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.dependencies import get_current_user, CurrentUser
from backend.core.rbac import require_permission
from backend.services.legal_process_service import get_legal_process_service
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/legal-process", tags=["legal-process"])
legal_process_service = get_legal_process_service()


@router.get("/matter-types", response_model=List[str])
@require_permission("search_documents")
async def list_matter_types(
    current_user: CurrentUser = Depends(get_current_user),
) -> List[str]:
    """
    List all supported matter types

    Args:
        current_user: Current authenticated user

    Returns:
        List of supported matter types
    """
    try:
        matter_types = legal_process_service.list_matter_types()
        return matter_types

    except Exception as e:
        logger.error(f"Failed to list matter types: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve matter types",
        )


@router.post("/procedure", response_model=Dict[str, Any])
@require_permission("search_documents")
async def get_procedure(
    matter_type: str,
    court: str,
    facts: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get procedural guidance for a matter type

    Args:
        matter_type: Type of legal matter
        court: Court name
        facts: Brief facts of the case
        current_user: Current authenticated user

    Returns:
        Structured procedural guidance
    """
    try:
        # Validate input
        if not matter_type or not matter_type.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Matter type is required",
            )

        if not court or not court.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Court is required",
            )

        # Get procedure guidance
        result = await legal_process_service.get_procedure(
            matter_type=matter_type.strip(),
            court=court.strip(),
            facts=facts.strip() if facts else "",
        )

        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error", "Procedure not found"),
                "message": result.get("message", ""),
                "verify_at_registry": result.get("verify_at_registry", True),
            }

        return {
            "success": True,
            "matter_type": result["matter_type"],
            "court": result["court"],
            "guidance": result["guidance"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get procedure for {matter_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve procedural guidance",
        )