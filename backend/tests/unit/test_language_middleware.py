"""Tests for Language middleware and parse_accept_language helper."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.language import LanguageMiddleware, parse_accept_language

# ---------------------------------------------------------------------------
# parse_accept_language pure-function tests
# ---------------------------------------------------------------------------


class TestParseAcceptLanguage:
    def test_en(self):
        assert parse_accept_language("en") == "en"

    def test_fr(self):
        assert parse_accept_language("fr") == "fr"

    def test_fr_with_quality(self):
        result = parse_accept_language("fr-FR,fr;q=0.9,en-US;q=0.8")
        assert result == "fr"

    def test_empty_string_defaults_to_en(self):
        assert parse_accept_language("") == "en"

    def test_unsupported_language_defaults_to_en(self):
        assert parse_accept_language("ja") == "en"

    def test_picks_highest_quality(self):
        result = parse_accept_language("en;q=0.5,fr;q=0.9")
        assert result == "fr"

    def test_default_quality_is_1(self):
        # "fr" has implicit q=1.0, "en" has q=0.8
        result = parse_accept_language("fr,en;q=0.8")
        assert result == "fr"

    def test_unsupported_primary_falls_to_supported(self):
        # "es" is not supported, "fr" is supported with q=0.5
        result = parse_accept_language("es,fr;q=0.5")
        assert result == "fr"

    def test_all_unsupported_defaults_to_en(self):
        result = parse_accept_language("ja,zh,ko")
        assert result == "en"

    def test_complex_header(self):
        result = parse_accept_language("de;q=0.9,fr;q=0.8,en;q=0.7")
        # de is unsupported, so fr (0.8) > en (0.7)
        assert result == "fr"


# ---------------------------------------------------------------------------
# Middleware dispatch tests
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(LanguageMiddleware)

    @app.get("/test")
    async def _get():
        return {"ok": True}

    return app


class TestLanguageMiddleware:
    async def test_default_content_language_header(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
            assert resp.status_code == 200
            assert resp.headers["Content-Language"] == "en"

    async def test_accept_language_fr(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test", headers={"Accept-Language": "fr"})
            assert resp.headers["Content-Language"] == "fr"

    async def test_accept_language_en(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test", headers={"Accept-Language": "en"})
            assert resp.headers["Content-Language"] == "en"

    async def test_unsupported_language_falls_to_en(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test", headers={"Accept-Language": "ja"})
            assert resp.headers["Content-Language"] == "en"
