"""
Performance Monitoring Middleware
Tracks API endpoint performance and slow queries
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.logger import get_logger

logger = get_logger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request duration and log slow endpoints.

    Features:
    - Request duration tracking
    - Slow query detection (>1s warning, >3s error)
    - Endpoint performance metrics
    - Memory usage tracking (optional)
    """

    SLOW_REQUEST_THRESHOLD = 1.0  # Warn if request takes > 1s
    VERY_SLOW_REQUEST_THRESHOLD = 3.0  # Error if request takes > 3s

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track performance"""
        # Start timing
        start_time = time.time()

        # Get request info
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "unknown"

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error with duration
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {method} {path} - {str(e)}",
                extra={
                    "method": method,
                    "path": path,
                    "client": client,
                    "duration": f"{duration:.3f}s",
                    "error": str(e),
                },
            )
            raise

        # Calculate duration
        duration = time.time() - start_time

        # Add performance header
        response.headers["X-Process-Time"] = f"{duration:.3f}"

        # Log performance based on threshold
        log_extra = {
            "method": method,
            "path": path,
            "status": response.status_code,
            "duration": f"{duration:.3f}s",
            "client": client,
        }

        if duration > self.VERY_SLOW_REQUEST_THRESHOLD:
            logger.error(
                f"VERY SLOW REQUEST: {method} {path} took {duration:.3f}s", extra=log_extra
            )
        elif duration > self.SLOW_REQUEST_THRESHOLD:
            logger.warning(f"Slow request: {method} {path} took {duration:.3f}s", extra=log_extra)
        else:
            logger.info(
                f"{method} {path} - {response.status_code} ({duration:.3f}s)", extra=log_extra
            )

        return response
