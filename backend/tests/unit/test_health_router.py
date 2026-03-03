"""Tests for the health check router (/health)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# -- Strip problematic middleware ------------------------------------------


@pytest.fixture(autouse=True)
def _strip_middleware():
    from app.main import app
    from app.middleware.csrf import CSRFProtectionMiddleware
    from app.middleware.https import HTTPSEnforcementMiddleware
    from app.middleware.rate_limit import RateLimitMiddleware

    original = app.user_middleware[:]
    app.user_middleware = [
        m
        for m in app.user_middleware
        if m.cls not in (CSRFProtectionMiddleware, RateLimitMiddleware, HTTPSEnforcementMiddleware)
    ]
    app.middleware_stack = app.build_middleware_stack()
    yield
    app.user_middleware = original
    app.middleware_stack = app.build_middleware_stack()


# ===========================================================================
# GET /health
# ===========================================================================


async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "app_name" in data
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


async def test_health_check_trailing_slash(client):
    resp = await client.get("/health/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


# ===========================================================================
# GET /health/live
# ===========================================================================


async def test_liveness(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


# ===========================================================================
# GET /health/ready
# ===========================================================================


async def test_readiness_all_healthy(client):
    """When all checks succeed, status should be 'ready'."""
    with (
        patch(
            "app.routers.health.check_database", new_callable=AsyncMock, return_value=(True, "ok")
        ),
        patch("app.routers.health.check_redis", new_callable=AsyncMock, return_value=(True, "ok")),
        patch(
            "app.routers.health.check_mistral_api",
            new_callable=AsyncMock,
            return_value=(True, "ok"),
        ),
    ):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"]["status"] == "ok"
        assert data["checks"]["redis"]["status"] == "ok"


async def test_readiness_db_down(client):
    """Database failure should make status 'not_ready'."""
    with (
        patch(
            "app.routers.health.check_database",
            new_callable=AsyncMock,
            return_value=(False, "connection refused"),
        ),
        patch("app.routers.health.check_redis", new_callable=AsyncMock, return_value=(True, "ok")),
        patch(
            "app.routers.health.check_mistral_api",
            new_callable=AsyncMock,
            return_value=(True, "ok"),
        ),
    ):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"]["status"] == "error"


async def test_readiness_redis_down(client):
    """Redis failure should make status 'not_ready'."""
    with (
        patch(
            "app.routers.health.check_database", new_callable=AsyncMock, return_value=(True, "ok")
        ),
        patch(
            "app.routers.health.check_redis",
            new_callable=AsyncMock,
            return_value=(False, "timeout"),
        ),
        patch(
            "app.routers.health.check_mistral_api",
            new_callable=AsyncMock,
            return_value=(True, "ok"),
        ),
    ):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["redis"]["status"] == "error"


async def test_readiness_mistral_down_still_ready(client):
    """Mistral failure should NOT make service 'not_ready' (graceful degradation)."""
    with (
        patch(
            "app.routers.health.check_database", new_callable=AsyncMock, return_value=(True, "ok")
        ),
        patch("app.routers.health.check_redis", new_callable=AsyncMock, return_value=(True, "ok")),
        patch(
            "app.routers.health.check_mistral_api",
            new_callable=AsyncMock,
            return_value=(False, "key missing"),
        ),
    ):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        # Mistral is excluded from readiness decision
        assert data["status"] == "ready"
        assert data["checks"]["mistral_api"]["status"] == "error"
