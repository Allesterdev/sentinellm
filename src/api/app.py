"""
FastAPI application factory.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import health, validation


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="SentineLLM API",
        description="AI Security Gateway - Protect LLMs from prompt injections and secret leakage",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """API root endpoint with basic information."""
        return {
            "name": "SentineLLM API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    # Register routes
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(validation.router, prefix="/api/v1", tags=["Validation"])

    return app
