"""Tests for CSRF protection middleware."""

from unittest.mock import MagicMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.csrf import (
    CSRF_HEADER_NAME,
    CSRF_TOKEN_LENGTH,
    CSRF_TOKEN_NAME,
    CSRFProtectionMiddleware,
    clear_csrf_cookie,
    generate_csrf_token,
    set_csrf_cookie,
)

# ---------------------------------------------------------------------------
# Helper: build a minimal FastAPI app with only the CSRF middleware
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CSRFProtectionMiddleware)

    @app.get("/test")
    async def _get():
        return {"ok": True}

    @app.post("/test")
    async def _post():
        return {"ok": True}

    @app.put("/test")
    async def _put():
        return {"ok": True}

    @app.delete("/test")
    async def _delete():
        return {"ok": True}

    # Exempt endpoints
    @app.post("/api/v1/auth/login")
    async def _login():
        return {"ok": True}

    @app.post("/api/v1/auth/register")
    async def _register():
        return {"ok": True}

    @app.post("/api/v1/auth/guest")
    async def _guest():
        return {"ok": True}

    @app.post("/api/v1/auth/claim-guest")
    async def _claim():
        return {"ok": True}

    @app.post("/api/v1/auth/refresh")
    async def _refresh():
        return {"ok": True}

    @app.post("/api/v1/auth/logout")
    async def _logout():
        return {"ok": True}

    @app.post("/test/")
    async def _post_trailing():
        return {"ok": True}

    return app


# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


class TestGenerateCsrfToken:
    def test_returns_string(self):
        token = generate_csrf_token()
        assert isinstance(token, str)

    def test_expected_length(self):
        # token_urlsafe(32) produces ~43 chars, just verify it's at least the byte length
        token = generate_csrf_token()
        assert len(token) >= CSRF_TOKEN_LENGTH

    def test_unique_tokens(self):
        tokens = {generate_csrf_token() for _ in range(10)}
        assert len(tokens) == 10, "Each generated token should be unique"


class TestSetCsrfCookie:
    def test_sets_cookie(self):
        response = MagicMock()
        set_csrf_cookie(response, "test-token-value")
        response.set_cookie.assert_called_once()
        kwargs = response.set_cookie.call_args
        assert kwargs[1]["key"] == CSRF_TOKEN_NAME
        assert kwargs[1]["value"] == "test-token-value"
        assert kwargs[1]["httponly"] is False
        assert kwargs[1]["samesite"] == "lax"


class TestClearCsrfCookie:
    def test_clears_cookie(self):
        response = MagicMock()
        clear_csrf_cookie(response)
        response.delete_cookie.assert_called_once_with(key=CSRF_TOKEN_NAME, samesite="lax")


# ---------------------------------------------------------------------------
# Middleware dispatch tests (via test app)
# ---------------------------------------------------------------------------


class TestCSRFMiddlewareDispatch:
    async def test_get_allowed_without_token(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/test")
            assert resp.status_code == 200

    async def test_post_blocked_without_tokens(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/test")
            assert resp.status_code == 403
            assert resp.json()["error"] == "CSRFValidationError"

    async def test_post_blocked_with_only_cookie(self):
        app = _make_app()
        token = generate_csrf_token()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/test", cookies={CSRF_TOKEN_NAME: token})
            assert resp.status_code == 403

    async def test_post_blocked_with_only_header(self):
        app = _make_app()
        token = generate_csrf_token()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/test", headers={CSRF_HEADER_NAME: token})
            assert resp.status_code == 403

    async def test_post_blocked_with_mismatched_tokens(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/test",
                cookies={CSRF_TOKEN_NAME: "token-a"},
                headers={CSRF_HEADER_NAME: "token-b"},
            )
            assert resp.status_code == 403
            assert resp.json()["error"] == "CSRFValidationError"

    async def test_post_allowed_with_matching_tokens(self):
        app = _make_app()
        token = generate_csrf_token()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/test",
                cookies={CSRF_TOKEN_NAME: token},
                headers={CSRF_HEADER_NAME: token},
            )
            assert resp.status_code == 200

    async def test_put_requires_csrf(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.put("/test")
            assert resp.status_code == 403

    async def test_delete_requires_csrf(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/test")
            assert resp.status_code == 403

    async def test_exempt_path_login(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/auth/login")
            assert resp.status_code == 200

    async def test_exempt_path_register(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/auth/register")
            assert resp.status_code == 200

    async def test_exempt_path_guest(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/auth/guest")
            assert resp.status_code == 200

    async def test_exempt_path_claim_guest(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/auth/claim-guest")
            assert resp.status_code == 200

    async def test_exempt_path_refresh(self):
        """Refresh uses httpOnly cookie auth, not CSRF-vulnerable."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/auth/refresh")
            assert resp.status_code == 200

    async def test_exempt_path_logout(self):
        """Logout uses httpOnly cookie; worst-case is forced logout."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/auth/logout")
            assert resp.status_code == 200

    async def test_trailing_slash_normalised(self):
        """POST /test/ should be treated same as /test (needs CSRF)."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/test/")
            assert resp.status_code == 403
