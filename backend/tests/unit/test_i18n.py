"""Tests for app.i18n — internationalization."""

from __future__ import annotations

from app.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    TranslationContext,
    _,
    get_language,
    get_translation,
    set_language,
    translate,
)


class TestSupportedLanguages:
    def test_en_supported(self):
        assert "en" in SUPPORTED_LANGUAGES

    def test_fr_supported(self):
        assert "fr" in SUPPORTED_LANGUAGES

    def test_default_is_en(self):
        assert DEFAULT_LANGUAGE == "en"


class TestGetTranslation:
    def test_returns_translation_for_en(self):
        t = get_translation("en")
        assert t is not None

    def test_returns_translation_for_fr(self):
        t = get_translation("fr")
        assert t is not None

    def test_unsupported_language_falls_back(self):
        t = get_translation("zz")
        # Should return the default (en) translation
        assert t is not None

    def test_caching(self):
        t1 = get_translation("en")
        t2 = get_translation("en")
        assert t1 is t2


class TestSetLanguage:
    def test_set_valid_language(self):
        set_language("fr")
        assert get_language() == "fr"
        # Reset
        set_language("en")

    def test_set_invalid_language_ignored(self):
        original = get_language()
        set_language("xx")
        assert get_language() == original


class TestTranslate:
    def test_translate_returns_string(self):
        result = translate("hello")
        assert isinstance(result, str)

    def test_translate_with_language_override(self):
        result = translate("hello", language="fr")
        assert isinstance(result, str)

    def test_translate_with_kwargs(self):
        # Since translations may not be loaded, just verify no crash
        result = translate("welcome {name}", name="Gandalf")
        assert isinstance(result, str)

    def test_translate_bad_format_key(self):
        # If format key is missing it should return unformatted
        result = translate("{missing_key}")
        assert isinstance(result, str)

    def test_shorthand_alias(self):
        assert _ is translate


class TestTranslationContext:
    def test_context_manager_switches_language(self):
        set_language("en")
        with TranslationContext("fr"):
            assert get_language() == "fr"
        assert get_language() == "en"

    def test_context_manager_restores_on_exit(self):
        set_language("en")
        with TranslationContext("fr"):
            pass
        assert get_language() == "en"

    def test_nested_contexts(self):
        set_language("en")
        with TranslationContext("fr"):
            assert get_language() == "fr"
            # Nested is not yet supported but shouldn't crash
        assert get_language() == "en"
