"""
Structured logging with correlation IDs
Uses Python's logging with JSON formatting for production
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[int]] = ContextVar("user_id", default=None)
session_id_var: ContextVar[Optional[int]] = ContextVar("session_id", default=None)
character_id_var: ContextVar[Optional[int]] = ContextVar("character_id", default=None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context variables
        if request_id := request_id_var.get():
            log_data["request_id"] = request_id
        if user_id := user_id_var.get():
            log_data["user_id"] = user_id
        if session_id := session_id_var.get():
            log_data["session_id"] = session_id
        if character_id := character_id_var.get():
            log_data["character_id"] = character_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Format as JSON-like string (simple format for readability)
        return " ".join(f"{k}={v}" for k, v in log_data.items())


def get_logger(name: str) -> logging.Logger:
    """
    Get a structured logger with correlation ID support

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger


class log_context:
    """
    Context manager for setting log context variables

    Usage:
        with log_context(request_id="abc123", user_id=42):
            logger.info("User action")
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None,
        session_id: Optional[int] = None,
        character_id: Optional[int] = None,
    ):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.character_id = character_id
        self.tokens: list = []

    def __enter__(self):
        """Set context variables"""
        self.tokens.append(request_id_var.set(self.request_id))
        if self.user_id is not None:
            self.tokens.append(user_id_var.set(self.user_id))
        if self.session_id is not None:
            self.tokens.append(session_id_var.set(self.session_id))
        if self.character_id is not None:
            self.tokens.append(character_id_var.set(self.character_id))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Reset context variables"""
        for token in self.tokens:
            token.var.reset(token)


# Default logger for the application
logger = get_logger("mistral_realms")
