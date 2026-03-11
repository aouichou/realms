"""Core security utilities for password hashing and JWT tokens"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import HTTPException, Response, status
from jwt.exceptions import InvalidTokenError

# Configuration from environment
_jwt_secret = os.getenv("JWT_SECRET")
if not _jwt_secret:
    raise ValueError(
        "JWT_SECRET environment variable is required. "
        'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
    )
SECRET_KEY = _jwt_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Cookie settings
COOKIE_ACCESS_TOKEN_NAME = "access_token"
COOKIE_REFRESH_TOKEN_NAME = "refresh_token"
COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

COOKIE_GUEST_TOKEN_NAME = "guest_token"

# Check if running in production (HTTPS required for secure cookies)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access", "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def set_auth_cookies(response: Response, access_token: str, refresh_token: Optional[str] = None):
    """Set httpOnly cookies for authentication tokens

    Args:
        response: FastAPI Response object
        access_token: JWT access token
        refresh_token: Optional JWT refresh token

    Security:
        - httponly=True: Prevents JavaScript access (XSS protection)
        - secure=True: HTTPS only in production
        - samesite="lax": CSRF protection while allowing external links
        - domain=None: Restricts to current domain only
    """
    # Set access token cookie
    response.set_cookie(
        key=COOKIE_ACCESS_TOKEN_NAME,
        value=access_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,  # XSS protection
        secure=IS_PRODUCTION,  # HTTPS only in production
        samesite="lax",  # CSRF protection
    )

    # Set refresh token cookie if provided
    if refresh_token:
        response.set_cookie(
            key=COOKIE_REFRESH_TOKEN_NAME,
            value=refresh_token,
            max_age=REFRESH_COOKIE_MAX_AGE,
            httponly=True,  # XSS protection
            secure=IS_PRODUCTION,  # HTTPS only in production
            samesite="lax",  # CSRF protection
        )


def clear_auth_cookies(response: Response):
    """Clear authentication cookies (logout)

    Args:
        response: FastAPI Response object
    """
    response.delete_cookie(key=COOKIE_ACCESS_TOKEN_NAME, httponly=True, samesite="lax")
    response.delete_cookie(key=COOKIE_REFRESH_TOKEN_NAME, httponly=True, samesite="lax")
    response.delete_cookie(key=COOKIE_GUEST_TOKEN_NAME, httponly=True, samesite="lax")


async def check_token_revoked(payload: dict) -> bool:
    """Check if a token has been revoked (async — for use in endpoints)."""
    from app.services.redis_service import session_service

    jti = payload.get("jti")
    if not jti:
        return False
    return await session_service.is_token_revoked(jti)
