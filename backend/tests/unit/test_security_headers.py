"""Tests for Security Headers middleware."""

from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.security_headers import SecurityHeadersMiddleware


def _make_app(debug: bool = False) -> FastAPI:
    app = FastAPI()

    with patch("app.middleware.security_headers.settings") as mock_settings:
        mock_settings.debug = debug
        app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    async def _get():
        return {"ok": True}

    @app.get("/api/v1/auth/login")
    async def _auth():
        return {"ok": True}

    @app.get("/api/v1/users/me")
    async def _users():
        return {"ok": True}

    @app.get("/api/v1/games")
    async def _games():
        return {"ok": True}

    return app


class TestSecurityHeaders:
    async def test_x_content_type_options(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
            assert resp.headers["X-Content-Type-Options"] == "nosniff"

    async def test_x_frame_options(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
            assert resp.headers["X-Frame-Options"] == "DENY"

    async def test_x_xss_protection(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
            assert resp.headers["X-XSS-Protection"] == "1; mode=block"

    async def test_referrer_policy(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
            assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    async def test_permissions_policy(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
            assert "camera=()" in resp.headers["Permissions-Policy"]
            assert "microphone=()" in resp.headers["Permissions-Policy"]

    async def test_content_security_policy_present(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
            assert "Content-Security-Policy" in resp.headers

    async def test_sensitive_path_auth_gets_cache_control(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/auth/login")
            assert "no-store" in resp.headers["Cache-Control"]
            assert resp.headers["Pragma"] == "no-cache"

    async def test_sensitive_path_users_gets_cache_control(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/users/me")
            assert "no-store" in resp.headers["Cache-Control"]

    async def test_non_sensitive_path_no_cache_control(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/games")
            assert "Cache-Control" not in resp.headers
