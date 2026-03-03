"""Tests for HTTPS enforcement middleware."""

from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.https import HTTPSEnforcementMiddleware


def _make_app() -> FastAPI:
    """Build a bare FastAPI app with routes (middleware added per-test with patch)."""
    app = FastAPI()

    @app.get("/test")
    async def _get():
        return {"ok": True}

    @app.get("/health")
    async def _health():
        return {"status": "ok"}

    @app.get("/health/ready")
    async def _ready():
        return {"status": "ok"}

    return app


class TestHTTPSEnforcement:
    async def test_non_production_no_redirect(self):
        """In development mode, no HTTPS redirect should happen."""
        with patch("app.middleware.https.settings") as ms:
            ms.environment = "development"
            app = _make_app()
            app.add_middleware(HTTPSEnforcementMiddleware)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/test")
                assert resp.status_code == 200

    async def test_production_http_health_allowed(self):
        """Health check endpoints should be allowed on HTTP even in production."""
        with patch("app.middleware.https.settings") as ms:
            ms.environment = "production"
            app = _make_app()
            app.add_middleware(HTTPSEnforcementMiddleware)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/health")
                assert resp.status_code == 200

    async def test_production_http_health_ready_allowed(self):
        with patch("app.middleware.https.settings") as ms:
            ms.environment = "production"
            app = _make_app()
            app.add_middleware(HTTPSEnforcementMiddleware)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/health/ready")
                assert resp.status_code == 200

    async def test_production_http_redirects_to_https(self):
        """Non-health HTTP requests in production should get 301 redirect."""
        with patch("app.middleware.https.settings") as ms:
            ms.environment = "production"
            app = _make_app()
            app.add_middleware(HTTPSEnforcementMiddleware)
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                follow_redirects=False,
            ) as c:
                resp = await c.get("/test")
                assert resp.status_code == 301
                assert resp.headers["location"].startswith("https://")

    async def test_production_https_adds_hsts(self):
        """HTTPS requests in production should get HSTS header."""
        with patch("app.middleware.https.settings") as ms:
            ms.environment = "production"
            app = _make_app()
            app.add_middleware(HTTPSEnforcementMiddleware)
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                follow_redirects=False,
            ) as c:
                resp = await c.get("/test", headers={"x-forwarded-proto": "https"})
                assert resp.status_code == 200
                assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]
                assert "includeSubDomains" in resp.headers["Strict-Transport-Security"]

    async def test_production_x_forwarded_proto_https(self):
        """x-forwarded-proto: https should be treated as HTTPS connection."""
        with patch("app.middleware.https.settings") as ms:
            ms.environment = "production"
            app = _make_app()
            app.add_middleware(HTTPSEnforcementMiddleware)
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                follow_redirects=False,
            ) as c:
                resp = await c.get("/test", headers={"x-forwarded-proto": "https"})
                assert resp.status_code == 200
                assert "Strict-Transport-Security" in resp.headers
