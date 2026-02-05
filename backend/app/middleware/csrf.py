"""
CSRF Protection Middleware
Implements Double Submit Cookie pattern for CSRF protection
"""

import secrets
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.logger import get_logger

logger = get_logger(__name__)

# CSRF configuration
CSRF_TOKEN_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_TOKEN_LENGTH = 32

# Methods that require CSRF protection
PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths that don't need CSRF protection
EXEMPT_PATHS = {
    "/health",
    "/health/ready",
    "/health/live",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",  # Login generates new CSRF token
    "/api/v1/auth/register",  # Register generates new CSRF token
    "/api/v1/auth/guest",  # Guest login generates new CSRF token
}


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token"""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def set_csrf_cookie(response: Response, token: str):
    """Set CSRF token as a readable cookie (not httpOnly)

    Args:
        response: FastAPI Response object
        token: CSRF token to set

    Note:
        Cookie is NOT httpOnly because JavaScript needs to read it
        to include in request headers. This is safe because:
        1. CSRF tokens don't grant access alone (need valid auth)
        2. XSS attacks would bypass CSRF anyway
        3. The token must match both cookie AND header (double submit)
    """
    from app.core.security import IS_PRODUCTION

    response.set_cookie(
        key=CSRF_TOKEN_NAME,
        value=token,
        max_age=7 * 24 * 60 * 60,  # 7 days (same as refresh token)
        httponly=False,  # Must be readable by JavaScript
        secure=IS_PRODUCTION,  # HTTPS only in production
        samesite="strict",  # Strict for CSRF protection
        path="/",
    )


def clear_csrf_cookie(response: Response):
    """Clear CSRF token cookie"""
    response.delete_cookie(key=CSRF_TOKEN_NAME, samesite="strict")


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection using Double Submit Cookie pattern.

    How it works:
    1. Server generates random CSRF token on login
    2. Token sent to client in cookie (readable) and header (for display)
    3. Client must send token in X-CSRF-Token header for state-changing requests
    4. Server validates token from cookie matches token from header

    Security:
    - Attacker cannot read cookie from different origin (SameSite + CORS)
    - Attacker cannot guess token (cryptographically random)
    - Token must match in both cookie AND header (double submit)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate CSRF token for protected requests"""

        # Skip CSRF protection for exempt paths
        if request.url.path in EXEMPT_PATHS or request.url.path.startswith(
            ("/docs", "/redoc", "/static")
        ):
            return await call_next(request)

        # Only check state-changing methods
        if request.method in PROTECTED_METHODS:
            # Get CSRF token from cookie
            cookie_token = request.cookies.get(CSRF_TOKEN_NAME)

            # Get CSRF token from header
            header_token = request.headers.get(CSRF_HEADER_NAME)

            # Both must be present
            if not cookie_token or not header_token:
                logger.warning(
                    "CSRF validation failed: Missing token",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "has_cookie": bool(cookie_token),
                        "has_header": bool(header_token),
                    },
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "CSRFValidationError",
                        "message": "CSRF token missing. Please refresh the page and try again.",
                    },
                )

            # Tokens must match (constant-time comparison)
            if not secrets.compare_digest(cookie_token, header_token):
                logger.warning(
                    "CSRF validation failed: Token mismatch",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "client_ip": request.client.host if request.client else "unknown",
                    },
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "CSRFValidationError",
                        "message": "CSRF token invalid. Please refresh the page and try again.",
                    },
                )

            # Token validated successfully
            logger.debug(f"CSRF token validated for {request.method} {request.url.path}")

        # Process request
        response = await call_next(request)

        return response
