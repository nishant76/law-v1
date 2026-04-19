"""
Authentication API Routes
POST /api/v1/auth/register — register new firm
POST /api/v1/auth/login — authenticate and get tokens
POST /api/v1/auth/logout — logout and blacklist token
POST /api/v1/auth/refresh — get new access token from refresh token
POST /api/v1/auth/invite — invite user to firm
POST /api/v1/auth/accept-invite — accept invitation
POST /api/v1/auth/change-password — change password
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field

from backend.api.deps import get_db, get_current_user
from backend.core.dependencies import CurrentUser
from backend.services.auth_service import get_auth_service
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ===================
# Request Schemas
# ===================

class RegisterRequest(BaseModel):
    """Firm registration request"""
    firm_name: str = Field(..., min_length=2, max_length=255, description="Name of law firm or individual practitioner")
    email: EmailStr = Field(..., description="Admin user email")
    password: str = Field(..., min_length=8, max_length=128, description="Admin user password (min 8 chars)")
    plan: Optional[str] = Field("trial", description="Billing plan (trial, solo, small, mid, large)")


class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., description="Refresh token from login response")


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 chars)")


class InviteUserRequest(BaseModel):
    """Invite user request"""
    email: EmailStr = Field(..., description="Email of user to invite")
    role: str = Field(..., description="Role (firm_admin, lawyer, staff)")


class AcceptInviteRequest(BaseModel):
    """Accept invitation request"""
    invite_token: str = Field(..., description="Invite token from email")
    password: str = Field(..., min_length=8, description="Password for new account")
    name: str = Field(..., min_length=2, max_length=255, description="User's full name")


# ===================
# Response Schemas
# ===================

class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User info in responses"""
    id: str
    email: str
    name: str
    role: str
    firm_id: str
    firm_name: str
    plan: str


class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[dict] = None


# ===================
# Endpoints
# ===================

@router.post("/register", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """
    Register a new firm and create admin user
    
    No authentication required for registration
    Creates firm in trial plan with 30 days free access
    """
    
    try:
        logger.info(f"Registration request: {request.firm_name} ({request.email})")
        
        # Initialize auth service
        auth_service = await get_auth_service(db)
        
        # Register firm
        success, message, data = await auth_service.register_firm(
            firm_name=request.firm_name,
            email=request.email,
            password=request.password,
            plan=request.plan,
        )
        
        if not success:
            logger.warning(f"Registration failed: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
        
        return SuccessResponse(
            success=True,
            message=message,
            data=data,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in register endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=SuccessResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """
    Authenticate user and return JWT tokens
    
    No authentication required
    Returns access_token and refresh_token in response
    
    Performance target: < 1 second
    """
    
    try:
        logger.info(f"Login request: {request.email}")
        
        # Initialize auth service
        auth_service = await get_auth_service(db)
        
        # Attempt login
        success, message, data = await auth_service.login(
            email=request.email,
            password=request.password,
        )
        
        if not success:
            logger.warning(f"Login failed for {request.email}: {message}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        
        return SuccessResponse(
            success=True,
            message=message,
            data=data,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    authorization: Optional[str] = Header(None),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    """
    Logout user by blacklisting token
    
    Requires authentication
    Token becomes invalid immediately after logout
    """
    
    try:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header",
            )
        
        # Extract token
        token = authorization.split()[-1]
        
        # Logout is done in dependencies via get_current_user
        # Here we just blacklist the token
        from backend.core.security import blacklist_token
        blacklist_token(token)
        
        logger.info(f"User logged out: {current_user.user_id}")
        
        return SuccessResponse(
            success=True,
            message="Logged out successfully",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in logout endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        )


@router.post("/refresh", response_model=SuccessResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """
    Refresh access token using refresh token
    
    No user authentication required (uses refresh token)
    Returns new access_token
    Refresh token remains valid for additional refreshes
    """
    
    try:
        logger.info("Token refresh request")
        
        # Initialize auth service
        auth_service = await get_auth_service(db)
        
        # Refresh token
        success, message, data = await auth_service.refresh_access_token(
            refresh_token=request.refresh_token,
        )
        
        if not success:
            logger.warning(f"Token refresh failed: {message}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        
        return SuccessResponse(
            success=True,
            message=message,
            data=data,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in refresh endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """
    Change user password
    
    Requires authentication
    All existing tokens are revoked after password change
    User must login again with new password
    """
    
    try:
        logger.info(f"Password change request for user {current_user.user_id}")
        
        # Initialize auth service
        auth_service = await get_auth_service(db)
        
        # Change password
        success, message = await auth_service.change_password(
            user_id=current_user.user_id,
            old_password=request.old_password,
            new_password=request.new_password,
        )
        
        if not success:
            logger.warning(f"Password change failed: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
        
        return SuccessResponse(
            success=True,
            message=message,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in change_password endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed",
        )


@router.post("/invite", response_model=SuccessResponse)
async def invite_user(
    request: InviteUserRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """
    Invite a user to join firm
    
    Requires authentication with firm_admin role
    Sends invitation email to specified address
    Invitee can accept with token from email
    """
    
    try:
        logger.info(f"Invite request from user {current_user.user_id} for {request.email}")
        
        # Check authorization (firm_admin only)
        if current_user.role not in ["super_admin", "firm_admin"]:
            logger.warning(f"Unauthorized invite attempt by {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        # Initialize auth service
        auth_service = await get_auth_service(db)
        
        # Send invitation
        success, message, invite_token = await auth_service.invite_user(
            firm_id=current_user.firm_id,
            email=request.email,
            role=request.role,
            invited_by_user_id=current_user.user_id,
        )
        
        if not success:
            logger.warning(f"Invitation failed: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
        
        # TODO: Send email with invite_token via SendGrid
        
        return SuccessResponse(
            success=True,
            message=message,
            data={"invite_token": invite_token},
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in invite endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invitation failed",
        )


@router.post("/accept-invite", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def accept_invite(
    request: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """
    Accept user invitation and create account
    
    No authentication required (uses invite token)
    Creates new user account with role from invitation
    """
    
    try:
        logger.info("Accept invitation request")
        
        # Initialize auth service
        auth_service = await get_auth_service(db)
        
        # Accept invitation
        success, message, data = await auth_service.accept_invite(
            invite_token=request.invite_token,
            password=request.password,
            name=request.name,
        )
        
        if not success:
            logger.warning(f"Invitation acceptance failed: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
        
        return SuccessResponse(
            success=True,
            message=message,
            data=data,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in accept_invite endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account",
        )
