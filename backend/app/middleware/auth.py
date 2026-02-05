"""Authentication middleware and dependencies"""

from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import COOKIE_ACCESS_TOKEN_NAME, decode_token
from app.db.base import get_db
from app.db.models import User
from app.services.auth_service import get_user_by_id

# Bearer token scheme (backward compatibility)
security = HTTPBearer(auto_error=False)


def get_token_from_request(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token_cookie: Optional[str] = Cookie(None, alias=COOKIE_ACCESS_TOKEN_NAME),
) -> Optional[str]:
    """Extract token from either cookie or Authorization header
    
    Priority:
        1. httpOnly cookie (preferred for security)
        2. Authorization header (backward compatibility)
    
    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials from Authorization header
        access_token_cookie: Access token from httpOnly cookie
    
    Returns:
        JWT token string or None
    """
    # Priority 1: Check cookie (preferred)
    if access_token_cookie:
        return access_token_cookie
    
    # Priority 2: Check Authorization header (backward compatibility)
    if credentials:
        return credentials.credentials
    
    return None


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(get_token_from_request),
) -> User:
    """Get current authenticated user from JWT token"""

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode token
    payload = decode_token(token)

    user_id = payload.get("sub")
    if user_id is None or not isinstance(user_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user (can be guest or registered)"""
    return current_user


async def get_current_registered_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user (must be registered, not guest)"""
    if current_user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a registered account",
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None or not isinstance(user_id, str):
            return None
        return await get_user_by_id(db, user_id)
    except HTTPException:
        return None
