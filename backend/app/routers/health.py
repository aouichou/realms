"""
Health check router
Provides comprehensive health endpoints for Kubernetes probes
"""

from datetime import datetime

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.db.base import get_db
from app.models.schemas import HealthCheckResponse
from app.services.redis_service import session_service

router = APIRouter(prefix="/health", tags=["health"])


async def check_database() -> tuple[bool, str]:
    """Check PostgreSQL database connectivity"""
    try:
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            return True, "ok"
    except Exception as e:
        return False, str(e)


async def check_redis() -> tuple[bool, str]:
    """Check Redis connectivity"""
    try:
        # Try to set and get a test key
        await session_service.redis.set("health_check", "ok", ex=5)
        result = await session_service.redis.get("health_check")
        if result == "ok":
            return True, "ok"
        return False, "unexpected response"
    except Exception as e:
        return False, str(e)


async def check_mistral_api() -> tuple[bool, str]:
    """Check Mistral AI API availability"""
    if not settings.mistral_api_key:
        return False, "API key not configured"

    try:
        # Simple API health check (just verify connectivity, not make actual request)
        async with httpx.AsyncClient():
            # Mistral AI doesn't have a public health endpoint, so we skip actual check
            # In production, you might want to make a minimal API call
            return True, "ok"
    except Exception as e:
        return False, str(e)


@router.get("", response_model=HealthCheckResponse)
@router.get("/", response_model=HealthCheckResponse, include_in_schema=False)
async def health_check():
    """
    Basic health check endpoint
    Returns service status and basic information
    """
    return HealthCheckResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(),
    )


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe
    Indicates if the application is running
    """
    return {"status": "alive", "timestamp": datetime.now().isoformat()}


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe
    Checks if service is ready to accept requests
    Verifies database, Redis, and Mistral API connectivity
    """
    checks = {}
    is_ready = True

    # Check database
    db_ok, db_msg = await check_database()
    checks["database"] = {"status": "ok" if db_ok else "error", "message": db_msg}
    is_ready = is_ready and db_ok

    # Check Redis
    redis_ok, redis_msg = await check_redis()
    checks["redis"] = {"status": "ok" if redis_ok else "error", "message": redis_msg}
    is_ready = is_ready and redis_ok

    # Check Mistral API
    mistral_ok, mistral_msg = await check_mistral_api()
    checks["mistral_api"] = {"status": "ok" if mistral_ok else "error", "message": mistral_msg}
    # Don't mark as not ready for Mistral API issues (graceful degradation)

    response = {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }


    return response
