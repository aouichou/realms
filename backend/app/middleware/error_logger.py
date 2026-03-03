"""
Error logging middleware - captures and writes all errors to file
Logs full exception details including stack traces for debugging
"""

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.logger import get_logger

logger = get_logger(__name__)

# Error log directory - use /app/logs/errors inside container, fallback for non-container envs
ERROR_LOG_DIR = Path("/app/logs/errors")
try:
    ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    ERROR_LOG_DIR = Path("logs/errors")
    ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)


class ErrorLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures all errors and writes them to a detailed log file
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and capture any errors"""
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Capture full error details
            error_details = self._build_error_details(request, exc)

            # Write to file
            self._write_error_to_file(error_details)

            # Log to console as well
            logger.error(
                f"Error captured by ErrorLoggerMiddleware: {exc}",
                exc_info=True,
                extra={
                    "extra_data": {
                        "method": request.method,
                        "path": request.url.path,
                        "error_type": type(exc).__name__,
                    }
                },
            )

            # Re-raise to let other handlers process it
            raise

    def _build_error_details(self, request: Request, exc: Exception) -> dict:
        """Build comprehensive error details"""
        error_dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "module": type(exc).__module__,
                "traceback": traceback.format_exc(),
                "chain": self._get_exception_chain(exc),
            },
            "request": {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "path_params": request.path_params,
                "client": {
                    "host": request.client.host if request.client else None,
                    "port": request.client.port if request.client else None,
                },
                "headers": {
                    key: value
                    for key, value in request.headers.items()
                    if key.lower() not in ["authorization", "cookie", "x-api-key"]
                },
            },
            "state": {
                "request_id": getattr(request.state, "request_id", None),
                "user_id": getattr(request.state, "user_id", None),
                "character_id": getattr(request.state, "character_id", None),
                "session_id": getattr(request.state, "session_id", None),
                "companion_ids": getattr(request.state, "active_companion_ids", []),
                "combat_session_id": getattr(request.state, "combat_session_id", None),
                "in_combat": getattr(request.state, "in_combat", False),
            },
        }
        return error_dict

    def _get_exception_chain(self, exc: Exception) -> list:
        """Get the full chain of exceptions (cause and context)"""
        chain = []
        current = exc

        while current is not None:
            chain.append(
                {
                    "type": type(current).__name__,
                    "message": str(current),
                    "module": type(current).__module__,
                }
            )

            # Check for __cause__ (explicit exception chaining with 'from')
            if current.__cause__:
                current = current.__cause__
            # Check for __context__ (implicit exception chaining)
            elif current.__context__:
                current = current.__context__
            else:
                break

        return chain

    def _write_error_to_file(self, error_details: dict):
        """Write error details to a timestamped log file"""
        try:
            # Create filename with timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            filename = f"error_{timestamp}.json"
            filepath = ERROR_LOG_DIR / filename

            # Write JSON with pretty formatting
            with open(filepath, "w") as f:
                json.dump(error_details, f, indent=2, default=str)

            logger.info(f"Error details written to: {filepath}")

            # Also write a human-readable version
            txt_filename = f"error_{timestamp}.txt"
            txt_filepath = ERROR_LOG_DIR / txt_filename

            with open(txt_filepath, "w") as f:
                f.write("=" * 80 + "\n")
                f.write(f"ERROR REPORT - {error_details['timestamp']}\n")
                f.write("=" * 80 + "\n\n")

                f.write(f"Error Type: {error_details['error']['type']}\n")
                f.write(f"Error Message: {error_details['error']['message']}\n\n")

                f.write(
                    f"Request: {error_details['request']['method']} {error_details['request']['url']}\n"
                )
                f.write(f"Client: {error_details['request']['client']['host']}\n\n")

                if error_details["error"]["chain"]:
                    f.write("Exception Chain:\n")
                    f.write("-" * 80 + "\n")
                    for i, exc in enumerate(error_details["error"]["chain"], 1):
                        f.write(f"{i}. {exc['type']}: {exc['message']}\n")
                    f.write("\n")

                f.write("Full Traceback:\n")
                f.write("-" * 80 + "\n")
                f.write(error_details["error"]["traceback"])
                f.write("\n")

                f.write("=" * 80 + "\n")

            logger.info(f"Human-readable error log written to: {txt_filepath}")

        except Exception as write_error:
            logger.error(f"Failed to write error to file: {write_error}", exc_info=True)
