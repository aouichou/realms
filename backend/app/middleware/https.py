"""
HTTPS enforcement middleware
Redirects HTTP to HTTPS in production and adds HSTS headers
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, Response

from app.config import settings


class HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce HTTPS in production

    Features:
    - Redirects HTTP to HTTPS (301 permanent redirect)
    - Adds HSTS headers to prevent downgrade attacks
    - Only active in production (environment == "production")
    - Allows health checks on HTTP for load balancers
    """

    def __init__(self, app, hsts_max_age: int = 31536000):
        """
        Initialize HTTPS enforcement middleware

        Args:
            app: FastAPI application
            hsts_max_age: Max age for HSTS header in seconds (default: 1 year)
        """
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.is_production = settings.environment == "production"

    async def dispatch(self, request: Request, call_next):
        """
        Process request and enforce HTTPS if in production

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            Response (redirected if HTTP in production, or normal response)
        """
        # Skip HTTPS enforcement in development
        if not self.is_production:
            return await call_next(request)

        # Determine the real scheme — behind a reverse proxy / load balancer
        # the connection to the app is plain HTTP but the client-facing side
        # is HTTPS.  The proxy communicates this via X-Forwarded-Proto.
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()

        # Allow health checks on HTTP (for load balancers)
        if request.url.path in ["/health", "/health/ready", "/health/live"]:
            return await call_next(request)

        # Redirect HTTP to HTTPS in production
        if scheme == "http":
            # Build HTTPS URL
            https_url = request.url.replace(scheme="https")

            # 301 Permanent Redirect (tells browsers to always use HTTPS)
            return RedirectResponse(url=str(https_url), status_code=301)

        # For HTTPS requests, process normally and add HSTS header
        response: Response = await call_next(request)

        # Add HSTS header (Strict-Transport-Security)
        # Tells browsers to only use HTTPS for this domain for the specified time
        response.headers["Strict-Transport-Security"] = (
            f"max-age={self.hsts_max_age}; includeSubDomains; preload"
        )

        return response
