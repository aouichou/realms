"""
Observability middleware for HTTP requests
Adds correlation IDs, metrics, and logging to all requests
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.logger import get_logger, log_context
from app.observability.metrics import metrics

logger = get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds observability to all HTTP requests
    - Generates correlation IDs
    - Logs requests and responses
    - Records Prometheus metrics
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with observability"""
        # Generate request ID
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Extract user context if available
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = getattr(request.state.user, "id", None)

        # Set up logging context
        with log_context(request_id=request_id, user_id=user_id):
            # Log request
            logger.info(
                "Request started",
                extra={
                    "extra_data": {
                        "method": request.method,
                        "path": request.url.path,
                        "client_ip": request.client.host if request.client else None,
                    }
                },
            )

            # Process request
            try:
                response = await call_next(request)
                duration = time.time() - start_time

                # Record metrics
                metrics.record_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status=response.status_code,
                    duration=duration,
                )

                # Log response
                logger.info(
                    "Request completed",
                    extra={
                        "extra_data": {
                            "method": request.method,
                            "path": request.url.path,
                            "status": response.status_code,
                            "duration": duration,
                        }
                    },
                )

                # Add request ID to response headers
                response.headers["X-Request-ID"] = request_id

                return response

            except Exception as e:
                duration = time.time() - start_time

                # Record error metrics
                metrics.record_error(
                    error_type=type(e).__name__,
                    endpoint=request.url.path,
                )

                # Log error
                logger.error(
                    "Request failed",
                    extra={
                        "extra_data": {
                            "method": request.method,
                            "path": request.url.path,
                            "error": str(e),
                            "duration": duration,
                        }
                    },
                    exc_info=True,
                )

                raise
