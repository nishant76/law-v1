"""
Dependency injection functions for API endpoints
Re-exports from backend.core.dependencies for easier imports
"""
import uuid as _uuid

from fastapi import HTTPException, status

from backend.core.dependencies import get_db, get_current_user, get_optional_user, CurrentUser

__all__ = [
    "get_db",
    "get_current_user",
    "get_optional_user",
    "CurrentUser",
    "parse_uuid_or_404",
]


def parse_uuid_or_404(value: str, resource: str = "Resource") -> _uuid.UUID:
    """
    Parse a path/body id into a UUID, or raise 404.

    A malformed id is a lookup that cannot succeed, so it gets the same answer as
    an id belonging to another firm: 404, never 403, never 500 (CLAUDE.md — never
    reveal existence, and never return a raw exception). Without this,
    `uuid.UUID("nonsense")` raises ValueError deep in a service and surfaces as a
    500 "Failed to …", which reads as a server fault rather than a bad request.
    """
    try:
        return _uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found"
        )
