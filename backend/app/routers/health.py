"""
Health check router
Provides endpoints for service health monitoring
"""

from datetime import datetime

from fastapi import APIRouter

from app.config import settings
from app.models.schemas import HealthCheckResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthCheckResponse)
@router.get("/", response_model=HealthCheckResponse, include_in_schema=False)
async def health_check():
    """
    Health check endpoint

    Returns service status and basic information
    """
    return HealthCheckResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(),
    )


@router.get("/ready", response_model=HealthCheckResponse)
async def readiness_check():
    """
    Readiness check endpoint

    Checks if service is ready to accept requests
    Could include checks for Redis, database, etc.
    """
    # TODO: Add actual readiness checks (Redis connection, DB, etc.)
    return HealthCheckResponse(
        status="ready",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(),
    )
