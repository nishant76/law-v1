"""
Dependency injection functions for API endpoints
Re-exports from backend.core.dependencies for easier imports
"""

from backend.core.dependencies import get_db, get_current_user, get_optional_user, CurrentUser

__all__ = ["get_db", "get_current_user", "get_optional_user", "CurrentUser"]
