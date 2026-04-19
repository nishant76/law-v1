"""
FastAPI dependencies for security and database access
Extracts user context from JWT token and provides database sessions
"""

from typing import Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import AsyncSessionLocal
from backend.core.security import decode_token, UserContext
from backend.core.logger import get_logger

logger = get_logger(__name__)

http_bearer = HTTPBearer(auto_error=False)


class CurrentUser:
    """User context extracted from JWT token"""

    def __init__(self, context: UserContext):
        self.user_id = context.user_id
        self.firm_id = context.firm_id
        self.vertical = context.vertical
        self.role = context.role
        self.plan = context.plan
        self.email = context.email

    def __repr__(self) -> str:
        return f"<CurrentUser(id={self.user_id}, firm={self.firm_id}, role={self.role})>"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session

    Usage:
        @router.get("/endpoint")
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> CurrentUser:
    """
    FastAPI dependency to extract and validate current user from JWT token.
    Uses HTTPBearer so Swagger UI shows the Authorize button instead of a
    plain text field.

    Raises:
        HTTPException 401 if token missing or invalid
    """
    if not credentials:
        logger.warning("No authorization header provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    token_data = decode_token(token, expected_type="access")

    if not token_data:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_user = CurrentUser(token_data)
    logger.debug(f"User authenticated: {current_user}")

    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> Optional[CurrentUser]:
    """
    Extract current user if present, but don't fail if missing.
    Used for endpoints that can work with or without authentication.
    """
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
