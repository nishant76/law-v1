"""
Search API Routes
GET /api/v1/search/unified — unified search over both sources
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.schemas.search import SearchRequest, SearchResponse
from backend.services.search_service import get_search_service
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("/unified", response_model=SearchResponse)
async def unified_search(
    request: Request,
    search_request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> SearchResponse:
    """
    Unified search over both public judgments and own files
    
    Query BOTH sources simultaneously:
    - "from_your_files": Own indexed documents (if firm_id present)
    - "from_public_judgments": Public judgment citations
    
    Filters (optional):
    - outcome: "favour_petitioner", "favour_respondent", "bail_granted", "bail_refused"
    - court: Court name (e.g. "Punjab High Court")
    - year_from, year_to: Year range
    - matter_type: "criminal", "civil", "commercial", etc.
    
    Returns:
    - Results clearly labeled by source
    - Relevance scores
    - Source URLs for public judgments
    - Confidence scores for own files
    """
    
    try:
        # Validate query
        if not search_request.query or len(search_request.query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
        
        query = search_request.query.strip()
        firm_id = current_user.firm_id
        
        logger.info(
            f"Search request: '{query[:50]}...' from user {current_user.user_id} "
            f"(firm: {firm_id})"
        )
        
        # Initialize search service
        search_service = get_search_service(db)
        
        # Perform unified search
        result = await search_service.unified_search(
            query=query,
            filters=search_request.filters,
            firm_id=firm_id,
            top_per_source=search_request.limit,
        )
        
        # Check for errors
        if not result.get("success"):
            logger.error(f"Search failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail="Search failed. Please try again.")
        
        # Check performance target (< 3 seconds)
        if result.get("duration_ms", 0) > 3000:
            logger.warning(
                f"Search took {result['duration_ms']:.0f}ms (target <3000ms): {query}"
            )
        
        # Transform to response schema
        response = SearchResponse(
            success=True,
            query=query,
            from_your_files=result.get("from_your_files", []),
            from_public_judgments=result.get("from_public_judgments", []),
            total_results=result.get("total_results", 0),
            duration_ms=result.get("duration_ms", 0),
        )
        
        logger.info(
            f"Search completed: {len(response.from_your_files)} own files, "
            f"{len(response.from_public_judgments)} public judgments in {response.duration_ms:.0f}ms"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in unified_search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed. Please try again.")


@router.get("/suggest", response_model=Dict[str, Any])
async def search_suggestions(
    q: str = Query(..., min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get search suggestions/autocomplete based on query prefix
    Returns:
    - Common searches from own files
    - Common searches from public judgments
    - Case name suggestions
    """
    
    try:
        logger.info(f"Search suggestions for: '{q}' (user: {current_user.id})")
        
        # TODO: Implement search suggestions from local DB
        # For MVP, return empty suggestions
        
        return {
            "success": True,
            "query": q,
            "suggestions": [
                {"text": "Section 138 cheque bounce penalty", "type": "common_search"},
                {"text": "Contract cancellation grounds", "type": "common_search"},
            ],
        }
        
    except Exception as e:
        logger.error(f"Error in search_suggestions: {e}")
        return {
            "success": False,
            "query": q,
            "error": str(e),
            "suggestions": [],
        }
