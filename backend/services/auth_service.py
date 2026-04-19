"""
Authentication Service — business logic for auth operations
All auth endpoints delegate to functions in this service
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from backend.models.law_user import User, UserRole
from backend.models.law_firm import Firm
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    blacklist_token,
    blacklist_all_user_tokens,
)
from backend.core.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """Business logic for authentication"""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize auth service
        
        Args:
            session: Database session
        """
        self.db = session
    
    # ===================
    # Firm Registration
    # ===================
    
    async def register_firm(
        self,
        firm_name: str,
        email: str,
        password: str,
        plan: str = "trial",
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Register a new firm and create admin user
        
        Args:
            firm_name: Name of law firm or solo practitioner
            email: Admin user email
            password: Admin user password (plain text)
            plan: Billing plan (trial, solo, small, mid, large)
            
        Returns:
            Tuple of (success: bool, message: str, data: dict or None)
            On success: (True, "Firm registered", {"firm_id": ..., "user_id": ...})
            On error: (False, "Error message", None)
        """
        
        try:
            logger.info(f"Registering new firm: {firm_name} ({email})")
            
            # Check if email already exists
            existing_user = await self._get_user_by_email(email)
            if existing_user:
                logger.warning(f"Email already exists: {email}")
                return False, "Email already registered", None
            
            existing_firm = await self._get_firm_by_email(email)
            if existing_firm:
                logger.warning(f"Firm email already exists: {email}")
                return False, "Email already registered", None
            
            # Validate plan
            valid_plans = ["trial", "solo", "small", "mid", "large"]
            if plan not in valid_plans:
                return False, f"Invalid plan: {plan}", None
            
            # Create firm
            firm = Firm(
                name=firm_name,
                email=email,
                plan=plan,
                trial_started_at=datetime.now(timezone.utc),
                is_active=True,
            )
            self.db.add(firm)
            await self.db.flush()  # Get firm.id
            
            # Create admin user
            user = User(
                firm_id=firm.id,
                name=firm_name,
                email=email,
                password_hash=hash_password(password),
                role=UserRole.FIRM_ADMIN,
                is_active=True,
            )
            self.db.add(user)
            await self.db.flush()
            
            # Commit transaction
            await self.db.commit()
            
            logger.info(f"Firm registered successfully: {firm.id}")
            
            return True, "Firm registered successfully", {
                "firm_id": str(firm.id),
                "user_id": str(user.id),
                "email": email,
                "plan": plan,
            }
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error in register_firm: {e}")
            return False, "Registration failed (email may already exist)", None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error registering firm: {e}", exc_info=True)
            return False, "Registration failed", None
    
    # ===================
    # Login / Logout
    # ===================
    
    async def login(
        self,
        email: str,
        password: str,
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Authenticate user and return JWT tokens
        
        Args:
            email: User email
            password: Password (plain text)
            
        Returns:
            Tuple of (success: bool, message: str, data: dict or None)
            On success: (True, "Login successful", {"access_token": ..., "refresh_token": ..., "user": ...})
            On error: (False, "Error message", None)
        """
        
        try:
            logger.info(f"Login attempt: {email}")
            
            # Find user
            user = await self._get_user_by_email(email)
            if not user:
                logger.warning(f"Login failed: user not found ({email})")
                return False, "Invalid email or password", None
            
            # Check user is active
            if not user.is_active:
                logger.warning(f"Login failed: user inactive ({email})")
                return False, "User account is inactive", None
            
            # Verify password
            if not verify_password(password, user.password_hash):
                logger.warning(f"Login failed: invalid password ({email})")
                return False, "Invalid email or password", None
            
            # Get firm
            firm = await self._get_firm_by_id(user.firm_id)
            if not firm:
                logger.error(f"Firm not found for user {user.id}")
                return False, "Firm not found", None
            
            # Check firm is active
            if not firm.is_active:
                logger.warning(f"Login failed: firm inactive ({email})")
                return False, "Firm account is inactive", None
            
            # Update last login time
            user.last_login_at = datetime.now(timezone.utc)
            await self.db.commit()
            
            # Create tokens
            access_token = create_access_token(
                user_id=str(user.id),
                firm_id=str(firm.id),
                vertical="law",
                role=user.role.value,
                plan=firm.plan,
                email=user.email,
            )
            
            refresh_token = create_refresh_token(
                user_id=str(user.id),
                firm_id=str(firm.id),
            )
            
            logger.info(f"Login successful: {email}")
            
            return True, "Login successful", {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "role": user.role.value,
                    "firm_id": str(firm.id),
                    "firm_name": firm.name,
                    "plan": firm.plan,
                },
            }
            
        except Exception as e:
            logger.error(f"Error during login: {e}", exc_info=True)
            return False, "Login failed", None
    
    async def logout(
        self,
        token: str,
    ) -> Tuple[bool, str]:
        """
        Logout user by blacklisting token
        
        Args:
            token: Access token to blacklist
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        
        try:
            logger.info("Logout requested")
            
            # Blacklist the token
            success = blacklist_token(token)
            
            if success:
                logger.info("User logged out successfully")
                return True, "Logged out successfully"
            else:
                logger.warning("Failed to blacklist token on logout")
                return False, "Logout failed"
                
        except Exception as e:
            logger.error(f"Error during logout: {e}", exc_info=True)
            return False, "Logout failed"
    
    # ===================
    # Token Refresh
    # ===================
    
    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Use refresh token to get new access token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Tuple of (success: bool, message: str, data: dict or None)
            On success: (True, "Token refreshed", {"access_token": ..., ...})
            On error: (False, "Error message", None)
        """
        
        try:
            logger.info("Token refresh requested")
            
            # Decode refresh token
            token_data = decode_token(refresh_token, expected_type="refresh")
            if not token_data:
                logger.warning("Invalid refresh token")
                return False, "Invalid or expired refresh token", None
            
            # Get user
            user = await self._get_user_by_id(token_data.user_id)
            if not user or not user.is_active:
                logger.warning(f"User not found or inactive: {token_data.user_id}")
                return False, "User not found", None
            
            # Get firm
            firm = await self._get_firm_by_id(token_data.firm_id)
            if not firm or not firm.is_active:
                logger.warning(f"Firm not found or inactive: {token_data.firm_id}")
                return False, "Firm not found", None
            
            # Create new access token
            access_token = create_access_token(
                user_id=str(user.id),
                firm_id=str(firm.id),
                vertical="law",
                role=user.role.value,
                plan=firm.plan,
                email=user.email,
            )
            
            logger.info(f"Token refreshed for user {user.id}")
            
            return True, "Token refreshed", {
                "access_token": access_token,
                "token_type": "bearer",
            }
            
        except Exception as e:
            logger.error(f"Error refreshing token: {e}", exc_info=True)
            return False, "Token refresh failed", None
    
    # ===================
    # Password Changes
    # ===================
    
    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> Tuple[bool, str]:
        """
        Change user password and revoke all existing tokens
        
        Args:
            user_id: User ID
            old_password: Current password (plain text)
            new_password: New password (plain text)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        
        try:
            logger.info(f"Password change requested for user {user_id}")
            
            # Get user
            user = await self._get_user_by_id(user_id)
            if not user:
                logger.warning(f"User not found: {user_id}")
                return False, "User not found"
            
            # Verify old password
            if not verify_password(old_password, user.password_hash):
                logger.warning(f"Invalid old password for user {user_id}")
                return False, "Invalid old password"
            
            # Hash new password
            user.password_hash = hash_password(new_password)
            await self.db.commit()
            
            # Revoke all existing tokens for this user
            blacklist_all_user_tokens(user_id)
            
            logger.info(f"Password changed for user {user_id}, all tokens revoked")
            
            return True, "Password changed successfully"
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error changing password: {e}", exc_info=True)
            return False, "Password change failed"
    
    # ===================
    # User Invitation
    # ===================
    
    async def invite_user(
        self,
        firm_id: str,
        email: str,
        role: str,
        invited_by_user_id: str,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Invite a new user to join firm
        
        Args:
            firm_id: Firm ID
            email: New user email
            role: Role (firm_admin, lawyer, staff)
            invited_by_user_id: ID of user sending invite
            
        Returns:
            Tuple of (success: bool, message: str, invite_token: str or None)
        """
        
        try:
            logger.info(f"Inviting user {email} to firm {firm_id} as {role}")
            
            # Check email doesn't already exist
            existing_user = await self._get_user_by_email(email)
            if existing_user:
                logger.warning(f"Email already exists: {email}")
                return False, "Email already registered", None
            
            # Validate role
            valid_roles = ["firm_admin", "lawyer", "staff"]
            if role not in valid_roles:
                return False, f"Invalid role: {role}", None
            
            # Create invite token (temporary, expires in 7 days)
            from datetime import timedelta
            invite_token = create_access_token(
                user_id="",  # No user ID yet
                firm_id=firm_id,
                vertical="law",
                role="invite",
                plan="invite",
                email=email,
                expires_delta=timedelta(days=7),
            )
            
            logger.info(f"Invitation sent to {email}")
            
            return True, "Invitation sent", invite_token
            
        except Exception as e:
            logger.error(f"Error inviting user: {e}", exc_info=True)
            return False, "Invitation failed", None
    
    async def accept_invite(
        self,
        invite_token: str,
        password: str,
        name: str,
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Accept invitation and create user account
        
        Args:
            invite_token: Invite token from email
            password: New password (plain text)
            name: User's full name
            
        Returns:
            Tuple of (success: bool, message: str, data: dict or None)
        """
        
        try:
            logger.info("User accepting invitation")
            
            # Decode invite token
            token_data = decode_token(invite_token, expected_type="access")
            if not token_data or token_data.role != "invite":
                logger.warning("Invalid or expired invite token")
                return False, "Invalid or expired invitation", None
            
            email = token_data.email
            firm_id = token_data.firm_id
            
            # Check email doesn't already exist
            existing_user = await self._get_user_by_email(email)
            if existing_user:
                logger.warning(f"Email already exists: {email}")
                return False, "Email already registered", None
            
            # Create user
            user = User(
                firm_id=firm_id,
                name=name,
                email=email,
                password_hash=hash_password(password),
                role=UserRole.LAWYER,  # Default role, can be changed by firm_admin
                is_active=True,
            )
            self.db.add(user)
            await self.db.commit()
            
            logger.info(f"User created from invitation: {email}")
            
            return True, "Account created successfully", {
                "user_id": str(user.id),
                "email": email,
                "name": name,
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error accepting invitation: {e}", exc_info=True)
            return False, "Failed to create account", None
    
    # ===================
    # User Deactivation
    # ===================
    
    async def deactivate_user(
        self,
        user_id: str,
        firm_id: str,
        requesting_user_id: str,
    ) -> Tuple[bool, str]:
        """
        Deactivate a user (soft delete)
        
        Args:
            user_id: User to deactivate
            firm_id: Firm ID (for authorization check)
            requesting_user_id: User making the request (must be firm_admin)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        
        try:
            logger.info(f"Deactivating user {user_id} from firm {firm_id}")
            
            # Verify requesting user is firm admin
            requesting_user = await self._get_user_by_id(requesting_user_id)
            if not requesting_user or requesting_user.role != UserRole.FIRM_ADMIN:
                logger.warning(f"Unauthorized deactivation attempt by {requesting_user_id}")
                return False, "Unauthorized"
            
            # Get user to deactivate
            user = await self._get_user_by_id(user_id)
            if not user or str(user.firm_id) != firm_id:
                logger.warning(f"User not found or wrong firm: {user_id}")
                return False, "User not found"
            
            # Deactivate user
            user.is_active = False
            user.deleted_at = datetime.now(timezone.utc)
            await self.db.commit()
            
            # Revoke all tokens
            blacklist_all_user_tokens(user_id)
            
            logger.info(f"User deactivated: {user_id}")
            
            return True, "User deactivated"
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deactivating user: {e}", exc_info=True)
            return False, "Deactivation failed"
    
    # ===================
    # Private Helpers
    # ===================
    
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        stmt = select(User).where(
            and_(User.email == email, User.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
    
    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            from uuid import UUID
            stmt = select(User).where(
                and_(User.id == UUID(str(user_id)), User.deleted_at.is_(None))
            )
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except (ValueError, TypeError):
            return None
    
    async def _get_firm_by_email(self, email: str) -> Optional[Firm]:
        """Get firm by email"""
        stmt = select(Firm).where(
            and_(Firm.email == email, Firm.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
    
    async def _get_firm_by_id(self, firm_id: str) -> Optional[Firm]:
        """Get firm by ID"""
        try:
            from uuid import UUID
            stmt = select(Firm).where(
                and_(Firm.id == UUID(str(firm_id)), Firm.deleted_at.is_(None))
            )
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except (ValueError, TypeError):
            return None


async def get_auth_service(session: AsyncSession) -> AuthService:
    """Factory function to get auth service"""
    return AuthService(session)
