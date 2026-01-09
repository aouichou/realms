"""
Internationalization middleware
Detects and sets language based on Accept-Language header or user preferences
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.i18n import SUPPORTED_LANGUAGES, set_language


def parse_accept_language(accept_language: str) -> str:
    """
    Parse Accept-Language header and return best matching language

    Args:
        accept_language: Accept-Language header value (e.g., "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7")

    Returns:
        Language code (en or fr)
    """
    if not accept_language:
        return "en"

    # Parse language preferences with quality values
    languages = []
    for lang_range in accept_language.split(","):
        parts = lang_range.strip().split(";")
        lang = parts[0].split("-")[0].lower()  # Get primary language code

        # Get quality value (default 1.0)
        quality = 1.0
        if len(parts) > 1 and parts[1].startswith("q="):
            try:
                quality = float(parts[1][2:])
            except ValueError:
                quality = 1.0

        if lang in SUPPORTED_LANGUAGES:
            languages.append((lang, quality))

    # Sort by quality and return best match
    if languages:
        languages.sort(key=lambda x: x[1], reverse=True)
        return languages[0][0]

    return "en"


class LanguageMiddleware(BaseHTTPMiddleware):
    """
    Middleware that detects and sets the language for each request
    Priority: User preference > Accept-Language header > Default (en)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Set language context for the request"""
        language = "en"

        # Check if user has preferred language (from auth)
        if hasattr(request.state, "user") and request.state.user:
            user_lang = getattr(request.state.user, "preferred_language", None)
            if user_lang and user_lang in SUPPORTED_LANGUAGES:
                language = user_lang

        # Fallback to Accept-Language header
        if language == "en":
            accept_language = request.headers.get("Accept-Language", "")
            language = parse_accept_language(accept_language)

        # Set language context
        set_language(language)

        # Add language to response headers
        response = await call_next(request)
        response.headers["Content-Language"] = language

        return response
