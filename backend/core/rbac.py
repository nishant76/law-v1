"""
RBAC (Role-Based Access Control) — permission decorators and usage limits
Enforces authorization checks and usage quotas per role
"""

import logging
from functools import wraps
from typing import Callable, List, Optional
from fastapi import HTTPException, status

from backend.core.logger import get_logger
from backend.core.dependencies import CurrentUser

logger = get_logger(__name__)


# ===================
# Permissions by Role
# ===================

PERMISSIONS = {
    # Super admin can do everything
    "super_admin": [
        "create_firm",
        "manage_firms",
        "manage_users",
        "access_platform",
        "create_drafts",
        "search_documents",
        "upload_documents",
        "view_analytics",
        "manage_billing",
    ],
    
    # Firm admin manages their firm
    "firm_admin": [
        "manage_users",
        "manage_firm",
        "access_firm_data",
        "create_drafts",
        "search_documents",
        "upload_documents",
        "delete_documents",
        "view_analytics",
        "manage_billing",
    ],
    
    # Lawyers are the main users
    "lawyer": [
        "access_firm_data",
        "create_drafts",
        "search_documents",
        "upload_documents",
        "delete_documents",
        "view_own_matters",
    ],
    
    # Staff can help with administrative tasks
    "staff": [
        "access_firm_data",
        "upload_documents",
        "view_own_matters",
    ],
    
    # Trial users have limited access
    "trial": [
        "create_drafts",  # Limited to 3/month
        "search_documents",  # Limited to 5/month
        "upload_documents",
        "view_own_matters",
    ],
}


# ===================
# Usage Limits
# ===================

USAGE_LIMITS = {
    # Limits per calendar day (local timezone)
    
    "super_admin": {
        "drafts_per_day": 1000,
        "searches_per_day": 1000,
        "extractions_per_day": 1000,
        "exports_per_day": 1000,
    },
    
    "firm_admin": {
        "drafts_per_day": 500,
        "searches_per_day": 500,
        "extractions_per_day": 500,
        "exports_per_day": 500,
    },
    
    "lawyer": {
        "drafts_per_day": 100,
        "searches_per_day": 100,
        "extractions_per_day": 50,
        "exports_per_day": 50,
    },
    
    "staff": {
        "drafts_per_day": 0,
        "searches_per_day": 50,
        "extractions_per_day": 0,
        "exports_per_day": 10,
    },
    
    "trial": {
        # 3 drafts per MONTH, 5 searches per MONTH
        # Tracked at firm level in database
        "drafts_per_month": 3,
        "searches_per_month": 5,
        "extractions_per_month": 0,
    },
}


# ===================
# Permission Checks
# ===================

def require_permission(permission: str):
    """
    Decorator to check if user has required permission
    
    Args:
        permission: Permission name (must exist in PERMISSIONS dict)
        
    Returns:
        Decorated function
        
    Usage:
        @router.post("/create-draft")
        @require_permission("create_drafts")
        async def create_draft(
            current_user: CurrentUser = Depends(get_current_user),
            ...
        ):
            ...
    
    Security:
    - Returns 403 FORBIDDEN if user lacks permission
    - Logs unauthorized access attempts
    - Never reveals what permission was required
    """
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: CurrentUser = None, **kwargs):
            # Get current_user from dependency injection
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                )
            
            # Check permission
            user_permissions = PERMISSIONS.get(current_user.role, [])
            
            if permission not in user_permissions:
                logger.warning(
                    f"Unauthorized access attempt: "
                    f"user {current_user.user_id} ({current_user.role}) "
                    f"tried to access permission '{permission}'"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )
            
            # Call original function
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    
    return decorator


def require_role(allowed_roles: List[str]):
    """
    Decorator to check if user has one of allowed roles
    
    Args:
        allowed_roles: List of allowed role names
        
    Returns:
        Decorated function
        
    Usage:
        @router.put("/users/{user_id}")
        @require_role(["super_admin", "firm_admin"])
        async def update_user(
            user_id: str,
            current_user: CurrentUser = Depends(get_current_user),
            ...
        ):
            ...
    """
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: CurrentUser = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                )
            
            if current_user.role not in allowed_roles:
                logger.warning(
                    f"Unauthorized role access: "
                    f"user {current_user.user_id} ({current_user.role}) "
                    f"tried to access admin endpoint"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    
    return decorator


def check_usage_limit(
    action: str,  # "draft", "search", "extraction", "export"
    current_user: CurrentUser,
    current_usage: int,  # Current count for this action today/month
) -> bool:
    """
    Check if user has remaining quota for an action
    
    Args:
        action: Action type
        current_user: Current user context
        current_usage: How many times user has done this action today/month
        
    Returns:
        True if user is within quota, False if exceeded
        
    Usage:
        limit_key = "drafts_per_day"
        limit = USAGE_LIMITS[current_user.role].get(limit_key, 0)
        
        if current_usage >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily {action} limit reached: {limit}",
            )
    """
    
    try:
        role_limits = USAGE_LIMITS.get(current_user.role, {})
        
        if current_user.role == "trial":
            limit_key = f"{action}_per_month"
        else:
            limit_key = f"{action}_per_day"
        
        limit = role_limits.get(limit_key, 0)
        
        is_within_limit = current_usage < limit
        
        if not is_within_limit:
            logger.info(
                f"Usage limit exceeded for {current_user.user_id}: "
                f"{action} ({current_usage}/{limit})"
            )
        
        return is_within_limit
        
    except Exception as e:
        logger.error(f"Error checking usage limit: {e}")
        return True  # Allow access if limit check fails


# ===================
# Authorization Checks
# ===================

def check_firm_access(
    requested_firm_id: str,
    current_user: CurrentUser,
) -> bool:
    """
    Check if user has access to a firm
    
    Args:
        requested_firm_id: Firm ID being accessed
        current_user: Current user context
        
    Returns:
        True if user can access this firm, False otherwise
    
    Rules:
    - super_admin: can access any firm
    - firm_admin, lawyer, staff: can only access their own firm
    
    Usage:
        if not check_firm_access(firm_id, current_user):
            # IMPORTANT: Return 404 not 403 to hide existence
            raise HTTPException(status_code=404, detail="Not found")
    """
    
    if current_user.role == "super_admin":
        return True
    
    return current_user.firm_id == requested_firm_id


def check_resource_ownership(
    resource_firm_id: str,
    current_user: CurrentUser,
) -> bool:
    """
    Check if resource belongs to user's firm
    
    Args:
        resource_firm_id: Firm ID that owns the resource
        current_user: Current user context
        
    Returns:
        True if user can access resource, False otherwise
    """
    
    return check_firm_access(resource_firm_id, current_user)
