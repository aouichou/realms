"""
Internationalization (i18n) support
Provides translation services for English and French
"""

import gettext
from contextvars import ContextVar
from pathlib import Path
from typing import Optional

# Context variable for current language
current_language: ContextVar[str] = ContextVar("language", default="en")

# Available languages
SUPPORTED_LANGUAGES = {"en", "fr"}
DEFAULT_LANGUAGE = "en"

# Path to translation files
LOCALE_DIR = Path(__file__).parent / "locales"

# Translation instances cache
_translations = {}


def get_translation(language: str) -> gettext.GNUTranslations:
    """
    Get translation instance for a language

    Args:
        language: Language code (en, fr)

    Returns:
        gettext translation instance
    """
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE

    if language not in _translations:
        try:
            translation = gettext.translation(
                "messages", localedir=LOCALE_DIR, languages=[language], fallback=True
            )
            _translations[language] = translation
        except Exception:
            # Fallback to NullTranslations if files don't exist
            _translations[language] = gettext.NullTranslations()

    return _translations[language]


def set_language(language: str) -> None:
    """
    Set the current language for the context

    Args:
        language: Language code (en, fr)
    """
    if language in SUPPORTED_LANGUAGES:
        current_language.set(language)


def get_language() -> str:
    """Get the current language from context"""
    return current_language.get()


def translate(message: str, language: Optional[str] = None, **kwargs) -> str:
    """
    Translate a message to the current language

    Args:
        message: Message to translate (English key)
        language: Optional language override
        **kwargs: Variables to format into the message

    Returns:
        Translated and formatted message

    Usage:
        translate("character.created", name="Gandalf")
        translate("error.not_found", language="fr")
    """
    lang = language or get_language()
    translation = get_translation(lang)
    translated = translation.gettext(message)

    # Format with variables if provided
    if kwargs:
        try:
            translated = translated.format(**kwargs)
        except KeyError:
            # If formatting fails, return unformatted
            pass

    return translated


# Shorthand alias
_ = translate


class TranslationContext:
    """
    Context manager for temporarily setting language

    Usage:
        with TranslationContext("fr"):
            message = _("welcome.message")
    """

    def __init__(self, language: str):
        self.language = language
        self.previous_language = None
        self.token = None

    def __enter__(self):
        """Set language context"""
        self.previous_language = current_language.get()
        self.token = current_language.set(self.language)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore previous language"""
        if self.token:
            current_language.reset(self.token)
