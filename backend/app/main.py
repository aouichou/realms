"""
Main FastAPI application
Configures the API server with middleware, routers, and error handlers
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    adventures,
    auth,
    characters,
    combat,
    companion,
    conditions,
    conversations,
    dice,
    effects,
    game,
    images,
    inventory,
    loot,
    memories,
    npcs,
    progression,
    quests,
    random_status,
    rest,
    sessions,
    spells,
)
from app.api.routes import rules
from app.config import settings
from app.db.base import close_db
from app.middleware.language import LanguageMiddleware
from app.middleware.observability import ObservabilityMiddleware
from app.middleware.performance import PerformanceMiddleware
from app.middleware.query_monitor import query_monitor
from app.middleware.rate_limit import RateLimitMiddleware
from app.observability.logger import get_logger
from app.observability.tracing import init_tracing, instrument_app
from app.routers import health, metrics, narrate
from app.services.redis_service import session_service

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize OpenTelemetry tracing
    if settings.tracing_enabled:
        logger.info("Initializing OpenTelemetry tracing...")
        init_tracing(
            service_name=settings.service_name,
            otlp_endpoint=settings.otlp_endpoint,
            enabled=True,
        )
        logger.info(f"Tracing enabled: exporting to {settings.otlp_endpoint}")

    # Initialize database
    try:
        logger.info("Initializing database connection...")
        # Note: Tables are created by Alembic migrations
        # await init_db()  # Only use in development without Alembic
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Initialize Redis connection
    try:
        logger.info("Initializing Redis connection...")
        await session_service.connect()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise

    # Setup query performance monitoring
    logger.info("Setting up query performance monitoring...")
    query_monitor.setup_query_logging()

    yield

    # Shutdown
    logger.info("Shutting down application")
    await close_db()
    await session_service.disconnect()


# Create FastAPI application
app = FastAPI(
    title="Mistral Realms API",
    description="AI-Powered D&D Adventure Generator using Mistral AI",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Language detection middleware (sets language context)
app.add_middleware(LanguageMiddleware)

# Observability middleware (correlation IDs, metrics, logging)
app.add_middleware(ObservabilityMiddleware)

# Rate limiting middleware (before performance to track blocked requests)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
    requests_per_hour=settings.rate_limit_per_hour,
    burst_threshold=settings.rate_limit_burst_threshold,
    block_duration=settings.rate_limit_block_duration,
)

# Performance monitoring middleware
app.add_middleware(PerformanceMiddleware)

# Instrument FastAPI with OpenTelemetry
if settings.tracing_enabled:
    instrument_app(app)


# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with custom response"""
    errors = exc.errors()
    logger.error(f"Validation error: {errors}")

    # Clean up error details to make them JSON serializable
    cleaned_errors = []
    for error in errors:
        cleaned_error = {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
        # Convert ValueError or other objects to string
        if "ctx" in error and "error" in error["ctx"]:
            cleaned_error["detail"] = str(error["ctx"]["error"])
        if "input" in error:
            cleaned_error["input"] = error["input"]
        cleaned_errors.append(cleaned_error)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "detail": cleaned_errors,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.debug else None,
        },
    )


# Include routers
app.include_router(health.router)
app.include_router(metrics.router)  # Prometheus metrics
app.include_router(auth.router)  # Authentication endpoints
app.include_router(companion.router)  # AI Companion
app.include_router(images.router)  # Scene Image Generation
app.include_router(game.router)  # Save/Load System
app.include_router(narrate.router)
app.include_router(characters.router)
app.include_router(sessions.router)
app.include_router(conversations.router)
app.include_router(dice.router)
app.include_router(random_status.router)
app.include_router(inventory.router)
app.include_router(spells.router)
app.include_router(combat.router)
app.include_router(loot.router)
app.include_router(progression.router)
app.include_router(rest.router)
app.include_router(conditions.router)
app.include_router(effects.router)  # Active effects system
app.include_router(npcs.router)
app.include_router(quests.router)
app.include_router(adventures.router)  # Preset adventures
app.include_router(memories.router)  # Vector memory system
app.include_router(rules.router)  # D&D 5e rules helpers


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "disabled",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
