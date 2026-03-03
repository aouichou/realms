"""Tests for RateLimitMiddleware dispatch paths — rate_limit.py

Complements test_rate_limit.py (which covers in-memory helpers)
by testing the full dispatch method with a minimal FastAPI app.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, PropertyMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.rate_limit import RateLimitMiddleware

# ---------------------------------------------------------------------------
# Test app factory
# ---------------------------------------------------------------------------


def _make_app(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    burst_threshold: int = 20,
    block_duration: int = 300,
) -> FastAPI:
    """Create a minimal FastAPI app with the rate-limit middleware."""
    app = FastAPI()

    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        burst_threshold=burst_threshold,
        block_duration=block_duration,
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"message": "ok"}

    @app.post("/api/v1/auth/login")
    async def login():
        return {"token": "fake"}

    return app


async def _get_client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Whitelisted paths skip rate limiting
# ---------------------------------------------------------------------------


class TestWhitelistedPaths:
    async def test_health_skips_rate_limit(self):
        app = _make_app()
        async with await _get_client(app) as client:
            # Patch Redis as unavailable so we go in-memory
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=None)
                resp = await client.get("/health")
                assert resp.status_code == 200
                # No rate limit headers on whitelisted paths
                assert "X-RateLimit-Limit-Minute" not in resp.headers

    async def test_docs_skips_rate_limit(self):
        app = _make_app()
        async with await _get_client(app) as client:
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=None)
                resp = await client.get("/docs")
                # /docs redirects or returns HTML, but should not be rate-limited
                assert resp.status_code in (200, 307, 404)


# ---------------------------------------------------------------------------
# In-memory dispatch path
# ---------------------------------------------------------------------------


class TestInMemoryDispatch:
    async def test_normal_request_succeeds(self):
        app = _make_app()
        async with await _get_client(app) as client:
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=None)
                resp = await client.get("/api/v1/test")
                assert resp.status_code == 200
                assert "X-RateLimit-Limit-Minute" in resp.headers
                assert "X-RateLimit-Remaining-Minute" in resp.headers

    async def test_rate_limit_headers_present(self):
        app = _make_app(requests_per_minute=100)
        async with await _get_client(app) as client:
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=None)
                resp = await client.get("/api/v1/test")
                assert resp.headers["X-RateLimit-Limit-Minute"] == "100"

    async def test_per_minute_limit_enforced(self):
        app = _make_app(requests_per_minute=3, requests_per_hour=1000, burst_threshold=100)
        async with await _get_client(app) as client:
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=None)
                for _ in range(3):
                    resp = await client.get("/api/v1/test")
                    assert resp.status_code == 200

                # 4th request should be blocked
                resp = await client.get("/api/v1/test")
                assert resp.status_code == 429
                body = resp.json()
                assert body["error"] == "TooManyRequests"
                assert "Retry-After" in resp.headers

    async def test_blocked_client_gets_429(self):
        app = _make_app(burst_threshold=2)
        async with await _get_client(app) as client:
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=None)
                # Send enough to trigger burst block
                for _ in range(3):
                    await client.get("/api/v1/test")

                # should now be blocked
                resp = await client.get("/api/v1/test")
                assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Redis dispatch path
# ---------------------------------------------------------------------------


class TestRedisDispatch:
    async def test_normal_request_with_redis(self):
        app = _make_app()
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0  # not blocked
        mock_redis.zcount.return_value = 0  # no requests
        mock_redis.zadd = AsyncMock()
        mock_redis.expire = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock()

        async with await _get_client(app) as client:
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=mock_redis)
                resp = await client.get("/api/v1/test")
                assert resp.status_code == 200
                assert "X-RateLimit-Limit-Minute" in resp.headers

    async def test_blocked_in_redis(self):
        app = _make_app()
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1  # blocked

        async with await _get_client(app) as client:
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=mock_redis)
                resp = await client.get("/api/v1/test")
                assert resp.status_code == 429

    async def test_redis_rate_limit_exceeded(self):
        app = _make_app(requests_per_minute=5)
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0  # not blocked

        call_count = [0]

        async def fake_zcount(key, min_val, max_val):
            call_count[0] += 1
            # First call is burst check → 0
            # Second call is global per-minute → over limit
            if call_count[0] <= 1:
                return 0
            return 100  # over any limit

        mock_redis.zcount = fake_zcount
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zrangebyscore = AsyncMock(return_value=[str(time.time() - 30)])

        async with await _get_client(app) as client:
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=mock_redis)
                resp = await client.get("/api/v1/test")
                assert resp.status_code == 429

    async def test_redis_connection_error_falls_back(self):
        app = _make_app()
        mock_redis = AsyncMock()
        mock_redis.exists.side_effect = ConnectionError("Redis down")

        async with await _get_client(app) as client:
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=mock_redis)
                # Should fall back to in-memory and succeed
                resp = await client.get("/api/v1/test")
                assert resp.status_code == 200

    async def test_redis_burst_protection(self):
        app = _make_app(burst_threshold=5)
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0

        call_count = [0]

        async def fake_zcount(key, min_val, max_val):
            call_count[0] += 1
            if call_count[0] == 1:
                # First zcount is burst check → over threshold
                return 100
            return 0

        mock_redis.zcount = fake_zcount
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.set = AsyncMock()

        async with await _get_client(app) as client:
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=mock_redis)
                resp = await client.get("/api/v1/test")
                assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Endpoint-specific rate limits (in-memory path)
# ---------------------------------------------------------------------------


class TestEndpointSpecificLimits:
    async def test_login_rate_limit(self):
        app = _make_app(requests_per_minute=1000, burst_threshold=1000)
        async with await _get_client(app) as client:
            with patch("app.middleware.rate_limit.session_service") as mock_ss:
                type(mock_ss).redis = PropertyMock(return_value=None)
                # Login limit is 5/min
                for _ in range(5):
                    resp = await client.post("/api/v1/auth/login")
                    assert resp.status_code in (200, 307, 422)

                # 6th should be blocked
                resp = await client.post("/api/v1/auth/login")
                assert resp.status_code == 429
