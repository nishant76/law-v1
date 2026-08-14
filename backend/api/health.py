"""
Health check endpoint for monitoring and load balancers
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.core.database import get_session
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response"""
    success: bool
    status: str
    database: str
    cache: str
    openai: str
    overall: str
    request_id: Optional[str] = None


@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> HealthResponse:
    """
    Health check endpoint for Azure App Service and monitoring.

    Tests actual connectivity to:
    - Database: SELECT 1 query
    - Redis: PING command
    - Azure OpenAI: Endpoint reachability

    Returns 200 if overall healthy, 503 if any service is down.
    """
    request_id = getattr(request.state, "request_id", None)

    # Test database connectivity
    database_status = await _test_database(session)

    # Test Redis connectivity
    cache_status = await _test_redis()

    # Test Azure OpenAI connectivity
    openai_status = await _test_openai()

    # Determine overall status
    all_healthy = all(status == "ok" for status in [database_status, cache_status, openai_status])
    overall_status = "healthy" if all_healthy else "degraded"

    # Return 503 if any service is down
    if not all_healthy:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: database={database_status}, cache={cache_status}, openai={openai_status}"
        )

    return HealthResponse(
        success=True,
        status="healthy",
        database=database_status,
        cache=cache_status,
        openai=openai_status,
        overall=overall_status,
        request_id=request_id
    )


async def _test_database(session: AsyncSession) -> str:
    """Test database connectivity with SELECT 1"""
    try:
        await session.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return "error"


async def _test_redis() -> str:
    """Test Redis connectivity with PING"""
    try:
        import redis.asyncio as redis

        r = redis.Redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        return "ok"
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return "error"


async def _test_openai() -> str:
    """Test OpenAI API reachability (direct or Azure depending on config)"""
    try:
        import httpx

        if settings.USE_AZURE_OPENAI:
            url = f"{settings.AZURE_OPENAI_ENDPOINT}/openai/deployments/{settings.GPT4O_MINI_DEPLOYMENT}/completions"
            params = {"api-version": settings.AZURE_OPENAI_API_VERSION}
            headers = {"api-key": settings.AZURE_OPENAI_API_KEY}
        else:
            url = "https://api.openai.com/v1/models"
            params = {}
            headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code in [200, 401, 403]:
                return "ok"
            logger.warning(f"Unexpected OpenAI response: {response.status_code}")
            return "error"
    except Exception as e:
        logger.error(f"OpenAI health check failed: {str(e)}")
        return "error"
