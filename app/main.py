"""
Smart Study Planner - FastAPI Application

Main application entry point.
Initializes FastAPI with all middleware, exception handlers, and routes.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config.settings import get_settings
from app.core.database.mongo import close_mongodb_connection, connect_to_mongodb
from app.core.exceptions.handlers import register_exception_handlers
from app.core.logging.logger import setup_logging
from app.shared.constants import APP_DESCRIPTION, APP_NAME, APP_VERSION

# Initialize settings
settings = get_settings()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# FastAPI Application
# -----------------------------------------------------------------------------

def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    
    app = FastAPI(
        title=settings.APP_NAME,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        docs_url=settings.DOCS_URL if not settings.is_production else None,
        redoc_url=settings.REDOC_URL if not settings.is_production else None,
        openapi_url=settings.OPENAPI_URL if not settings.is_production else None,
    )
    
    return app


app = create_application()


# -----------------------------------------------------------------------------
# Middleware Registration
# -----------------------------------------------------------------------------

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# -----------------------------------------------------------------------------
# Exception Handlers
# -----------------------------------------------------------------------------

register_exception_handlers(app)


# -----------------------------------------------------------------------------
# Lifecycle Events
# -----------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    
    Initializes database connections and other resources.
    """
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT.value}")
    
    try:
        # Connect to MongoDB
        await connect_to_mongodb()
        logger.info("Database connection established")
        
        # Future: Initialize Redis, cache, etc.
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.
    
    Closes database connections and cleans up resources.
    """
    logger.info("Shutting down application")
    
    try:
        # Close MongoDB connection
        await close_mongodb_connection()
        logger.info("Database connection closed")
        
        # Future: Close Redis, cleanup cache, etc.
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# -----------------------------------------------------------------------------
# API Routes
# -----------------------------------------------------------------------------

# Include v1 API routes
app.include_router(
    v1_router,
    prefix=settings.API_V1_PREFIX,
)


# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="API Root",
    description="Get API information",
)
async def root():
    """
    Root endpoint - API information.
    
    Returns basic API information and health status.
    """
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "environment": settings.ENVIRONMENT.value,
        "status": "running",
        "docs_url": settings.DOCS_URL,
    }


# -----------------------------------------------------------------------------
# Application Entry Point (for direct execution)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD and settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
