"""
Main FastAPI application
Configures the API server with middleware, routers, and error handlers
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from app.config import settings
from app.utils.logger import logger
from app.routers import health, narrate
from app.api import characters, sessions, conversations, dice, random_status, inventory, spells
from app.db.base import init_db, close_db
from app.services.redis_service import session_service


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
    lifespan=lifespan
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with custom response"""
    errors = exc.errors()
    logger.error(f"Validation error: {errors}")
    
    # Clean up error details to make them JSON serializable
    cleaned_errors = []
    for error in errors:
        cleaned_error = {
            'loc': error['loc'],
            'msg': error['msg'],
            'type': error['type']
        }
        # Convert ValueError or other objects to string
        if 'ctx' in error and 'error' in error['ctx']:
            cleaned_error['detail'] = str(error['ctx']['error'])
        if 'input' in error:
            cleaned_error['input'] = error['input']
        cleaned_errors.append(cleaned_error)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "detail": cleaned_errors
        }
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
            "detail": str(exc) if settings.debug else None
        }
    )


# Include routers
app.include_router(health.router)
app.include_router(narrate.router)
app.include_router(characters.router)
app.include_router(sessions.router)
app.include_router(conversations.router)
app.include_router(dice.router)
app.include_router(random_status.router)
app.include_router(inventory.router)
app.include_router(spells.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "disabled",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
