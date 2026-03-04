"""
Main FastAPI application
Configures the API server with middleware, routers, and error handlers
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.config import settings
from app.db.base import close_db, engine
from app.middleware.csrf import CSRFProtectionMiddleware
from app.middleware.error_logger import ErrorLoggerMiddleware
from app.middleware.https import HTTPSEnforcementMiddleware
from app.middleware.language import LanguageMiddleware
from app.middleware.observability import ObservabilityMiddleware
from app.middleware.performance import PerformanceMiddleware
from app.middleware.query_monitor import query_monitor
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.observability.logger import get_logger
from app.observability.tracing import (
    init_metrics_export,
    init_tracing,
    instrument_app,
    instrument_sqlalchemy,
)
from app.routers import health, metrics, models
from app.services.dm_supervisor import get_dm_supervisor
from app.services.image_detection_service import get_image_detection_service
from app.services.provider_init import initialize_providers
from app.services.redis_service import session_service

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    logger.info("Environment: %s", settings.environment)
    logger.info("Debug mode: %s", settings.debug)

    # Initialize OpenTelemetry tracing
    if settings.tracing_enabled:
        logger.info("Initializing OpenTelemetry tracing...")
        init_tracing(
            service_name=settings.service_name,
            otlp_endpoint=settings.otlp_endpoint,
            enabled=True,
            grafana_otlp_endpoint=settings.grafana_otlp_endpoint,
            grafana_instance_id=settings.grafana_cloud_instance_id,
            grafana_api_key=settings.grafana_cloud_api_key,
        )
        # Instrument database queries
        instrument_sqlalchemy(engine)
        backend = "Grafana Cloud" if settings.grafana_cloud_enabled else settings.otlp_endpoint
        logger.info("Tracing enabled: exporting to %s", backend)

        # Initialize OTLP metrics export (Grafana Cloud only)
        if settings.grafana_cloud_enabled:
            init_metrics_export(
                service_name=settings.service_name,
                grafana_otlp_endpoint=settings.grafana_otlp_endpoint,
                grafana_instance_id=settings.grafana_cloud_instance_id,
                grafana_api_key=settings.grafana_cloud_api_key,
            )
            # Initialize OTel metric instruments alongside prometheus_client
            from app.observability.metrics import metrics

            metrics.init_otel_instruments()

    # Initialize database
    try:
        logger.info("Initializing database connection...")
        # Note: Tables are created by Alembic migrations
        # await init_db()  # Only use in development without Alembic
        logger.info("Database connection established")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise

    # Initialize Redis connection
    try:
        logger.info("Initializing Redis connection...")
        await session_service.connect()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Failed to initialize Redis: %s", e)
        raise

    # Setup query performance monitoring
    logger.info("Setting up query performance monitoring...")
    query_monitor.setup_query_logging()

    # Initialize AI providers
    try:
        logger.info("Initializing AI providers...")
        provider_count = await initialize_providers()
        if provider_count == 0:
            logger.warning("⚠️  No AI providers initialized - check API keys in .env")
        else:
            logger.info(f"✓ {provider_count} AI provider(s) ready")
    except Exception as e:
        logger.error(f"Failed to initialize AI providers: {e}")
        # Continue anyway - some endpoints might still work

    # Preload image detection service (471MB ML model - better to load at startup than first request)
    try:
        logger.info("Preloading image detection service...")
        get_image_detection_service()  # Singleton - loads model now
        logger.info("✓ Image detection service ready")
    except Exception as e:
        logger.warning(f"Failed to preload image detection service: {e}")
        # Not critical - will lazy load on first use

    # Pre-warm DM supervisor (RL-140): loads sentence-transformers model + embeds D&D rule chunks
    # Prevents 2-5s cold-start latency on first combat/validation request
    try:
        logger.info("Pre-warming DM supervisor (RL-140)...")
        get_dm_supervisor()  # Singleton - loads model and embeddings now
        logger.info("✓ DM supervisor ready")
    except Exception as e:
        logger.warning(f"Failed to pre-warm DM supervisor: {e}")
        # Not critical - will lazy load on first validation request

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


# CORS Middleware — restrict to only the methods and headers the frontend uses
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Accept-Language",
        "X-CSRF-Token",
        "X-Request-ID",
    ],
    expose_headers=[
        "X-CSRF-Token",
        "X-Request-ID",
        "X-RateLimit-Limit-Minute",
        "X-RateLimit-Remaining-Minute",
        "X-RateLimit-Limit-Hour",
        "X-RateLimit-Remaining-Hour",
        "Retry-After",
    ],
    max_age=600,  # Cache preflight for 10 minutes
)

# Security headers (OWASP best practices)
app.add_middleware(SecurityHeadersMiddleware)

# HTTPS enforcement (redirects HTTP to HTTPS in production)
app.add_middleware(HTTPSEnforcementMiddleware, hsts_max_age=31536000)  # 1 year

# CSRF protection middleware (must be after CORS, before rate limiting)
app.add_middleware(CSRFProtectionMiddleware)

# Error logging middleware (captures errors to file - must be early in chain)
app.add_middleware(ErrorLoggerMiddleware)

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
    logger.error("Validation error: %s", errors)

    # Clean up error details to make them JSON serializable
    cleaned_errors = []
    for error in errors:
        cleaned_error = {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
        # Convert ValueError or other objects to string
        if "ctx" in error and "error" in error["ctx"]:
            cleaned_error["detail"] = str(error["ctx"]["error"])
        if "input" in error:
            inp = error["input"]
            cleaned_error["input"] = (
                inp.decode("utf-8", errors="replace") if isinstance(inp, bytes) else inp
            )
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
    logger.error("Unexpected error: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.debug else None,
        },
    )


# Include routers
# Root-level routers (health checks, metrics)
app.include_router(health.router)
app.include_router(metrics.router)

# Models and providers management
app.include_router(models.router)

# API v1 routers
app.include_router(api_router, prefix="/api/v1")

# Mount static files for generated images
MEDIA_DIR = Path(__file__).parent.parent / "media"
if MEDIA_DIR.exists():
    app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
else:
    # Create media directory if it doesn't exist
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "images" / "generated").mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


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
