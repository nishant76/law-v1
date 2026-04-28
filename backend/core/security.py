"""
Security module — JWT token creation, validation, and blacklist management
Implements HS256 (symmetric) JWT tokens with Redis-backed blacklist
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import redis
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis client for token blacklist
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


class UserContext(BaseModel):
    """User context extracted from JWT token"""
    user_id: str
    firm_id: str
    vertical: str = "law"  # Currently only "law" in Phase 1
    role: str
    plan: str
    email: str


class TokenData(BaseModel):
    """JWT token payload structure"""
    user_id: str
    firm_id: str
    vertical: str
    role: str
    plan: str
    email: str
    exp: datetime
    iat: datetime


def _truncate_password(password: str) -> str:
    """Truncate to 72 bytes — bcrypt hard limit. Consistent across hash and verify."""
    return password.encode("utf-8")[:72].decode("utf-8", errors="ignore")


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(_truncate_password(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from DB

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(_truncate_password(plain_password), hashed_password)


def create_access_token(
    user_id: str,
    firm_id: str,
    vertical: str,
    role: str,
    plan: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed access token (JWT)
    
    Args:
        user_id: User ID (UUID)
        firm_id: Firm ID (UUID)
        vertical: Vertical code ("law")
        role: User role (super_admin, firm_admin, lawyer, staff, trial)
        plan: Firm plan (trial, solo, small, mid, large)
        email: User email
        expires_delta: Override token expiry (default: 60 minutes)
        
    Returns:
        Signed JWT token string
        
    Security:
    - Algorithm: HS256
    - Expiry: 60 minutes default
    - Token does NOT contain sensitive data (no password, no secrets)
    """
    
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    payload = {
        "sub": user_id,
        "firm_id": firm_id,
        "vertical": vertical,
        "role": role,
        "plan": plan,
        "email": email,
        "iat": now.timestamp(),
        "exp": expire.timestamp(),
        "type": "access",
    }
    
    try:
        encoded_jwt = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        logger.debug(f"Access token created for user {user_id} (expires in {expires_delta})")
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise


def create_refresh_token(
    user_id: str,
    firm_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a refresh token (JWT)
    
    Args:
        user_id: User ID (UUID)
        firm_id: Firm ID (UUID)
        expires_delta: Override token expiry (default: 30 days)
        
    Returns:
        Signed JWT refresh token
        
    Security:
    - Refresh tokens are longer-lived than access tokens
    - Only contains user_id and firm_id (minimal payload)
    - Used only for getting new access tokens
    """
    
    if expires_delta is None:
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    payload = {
        "sub": user_id,
        "firm_id": firm_id,
        "iat": now.timestamp(),
        "exp": expire.timestamp(),
        "type": "refresh",
    }
    
    try:
        encoded_jwt = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        logger.debug(f"Refresh token created for user {user_id} (expires in {expires_delta})")
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creating refresh token: {e}")
        raise


def decode_token(token: str, expected_type: str = "access") -> Optional[TokenData]:
    """
    Decode and validate a JWT token
    
    Args:
        token: JWT token string
        expected_type: Expected token type ("access" or "refresh")
        
    Returns:
        TokenData with extracted claims, or None if invalid
        
    Security:
    - Validates signature
    - Validates expiry
    - Validates token type
    - Returns None if token is blacklisted
    """
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        
        # Validate token type
        token_type = payload.get("type", "access")
        if token_type != expected_type:
            logger.warning(f"Token type mismatch: expected {expected_type}, got {token_type}")
            return None
        
        user_id = payload.get("sub")
        firm_id = payload.get("firm_id")
        
        # Check if token is blacklisted (on logout)
        if is_token_blacklisted(token):
            logger.info(f"Token is blacklisted for user {user_id}")
            return None
        
        # For access tokens, extract full context
        if expected_type == "access":
            return TokenData(
                user_id=user_id,
                firm_id=firm_id,
                vertical=payload.get("vertical", "law"),
                role=payload.get("role", "trial"),
                plan=payload.get("plan", "trial"),
                email=payload.get("email", ""),
                exp=datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc),
                iat=datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc),
            )
        else:
            # For refresh tokens, return minimal data
            return TokenData(
                user_id=user_id,
                firm_id=firm_id,
                vertical="law",
                role="refresh",
                plan="refresh",
                email="",
                exp=datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc),
                iat=datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc),
            )
        
    except JWTError as e:
        logger.warning(f"JWT validation error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        return None


def blacklist_token(token: str) -> bool:
    """
    Add a token to the blacklist (used on logout)
    Token is stored in Redis with TTL equal to remaining token expiry
    
    Args:
        token: JWT token to blacklist
        
    Returns:
        True if blacklisted successfully
        
    Usage:
    - Called on logout: tokens become invalid immediately
    - Called on password change: all existing tokens for user are invalidated
    
    Storage:
    - Redis key: blacklist:token_id (token_id = user_id + creation timestamp)
    - TTL: equal to token expiry time (automatic cleanup)
    """
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},  # Get expiry even if expired
        )
        
        user_id = payload.get("sub")
        exp_timestamp = payload.get("exp", 0)
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        
        # Calculate TTL (time until expiry)
        now = datetime.now(timezone.utc)
        ttl_seconds = int((exp_datetime - now).total_seconds())
        
        # Don't store already-expired tokens
        if ttl_seconds <= 0:
            logger.debug(f"Token already expired for user {user_id}")
            return False
        
        # Create blacklist entry with TTL
        # Use a hash of the token as the key (shorter than full token)
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        blacklist_key = f"blacklist:{user_id}:{token_hash}"
        
        redis_client.setex(
            blacklist_key,
            ttl_seconds,
            json.dumps({
                "user_id": user_id,
                "blacklisted_at": now.isoformat(),
                "expires_at": exp_datetime.isoformat(),
            })
        )
        
        logger.info(f"Token blacklisted for user {user_id} (TTL: {ttl_seconds}s)")
        return True
        
    except JWTError:
        logger.warning("Could not decode token for blacklisting")
        return False
    except Exception as e:
        logger.error(f"Error blacklisting token: {e}")
        return False


def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token has been blacklisted (e.g., after logout)
    
    Args:
        token: JWT token to check
        
    Returns:
        True if token is blacklisted, False if still valid
    """
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        
        user_id = payload.get("sub")
        
        # Check if blacklist entry exists
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        blacklist_key = f"blacklist:{user_id}:{token_hash}"
        
        blacklist_entry = redis_client.get(blacklist_key)
        return blacklist_entry is not None
        
    except JWTError:
        return False
    except Exception as e:
        logger.error(f"Error checking token blacklist: {e}")
        return False


def blacklist_all_user_tokens(user_id: str) -> bool:
    """
    Blacklist ALL tokens for a user (used on password change)
    
    Args:
        user_id: User ID
        
    Returns:
        True if successful
    """
    
    try:
        # Create a "revoke all" marker in Redis
        revoke_key = f"user_revoke_all:{user_id}"
        redis_client.setex(
            revoke_key,
            86400 * 30,  # 30 days
            json.dumps({
                "user_id": user_id,
                "revoked_at": datetime.now(timezone.utc).isoformat(),
            })
        )
        
        logger.info(f"All tokens revoked for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error revoking all user tokens: {e}")
        return False


def check_user_revocation(user_id: str, token_iat: float) -> bool:
    """
    Check if user has revoked all tokens (after password change)
    
    Args:
        user_id: User ID
        token_iat: Token issued-at timestamp (JWT 'iat' claim)
        
    Returns:
        True if user has revoked all tokens (token is invalid)
    """
    
    try:
        revoke_key = f"user_revoke_all:{user_id}"
        revoke_entry = redis_client.get(revoke_key)
        
        if not revoke_entry:
            return False  # No revocation, token is valid
        
        # Check if token was issued before revocation
        revoke_data = json.loads(revoke_entry)
        revoked_at = datetime.fromisoformat(revoke_data["revoked_at"])
        token_iat_dt = datetime.fromtimestamp(token_iat, tz=timezone.utc)
        
        return token_iat_dt < revoked_at  # Token was issued before revocation
        
    except Exception as e:
        logger.error(f"Error checking user revocation: {e}")
        return False
