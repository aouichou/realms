"""Core security utilities for password hashing and JWT tokens"""

import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import HTTPException, Response, status
from jose import JWTError, jwt

# Configuration from environment
SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Cookie settings
COOKIE_ACCESS_TOKEN_NAME = "access_token"
COOKIE_REFRESH_TOKEN_NAME = "refresh_token"
COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
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
