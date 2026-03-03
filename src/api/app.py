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
        # Disabled in production (enable only in dev via env)
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # CORS middleware
    # Security: allow_credentials=True requires explicit origins (never "*").
    # Restricting methods and headers reduces the attack surface.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """API root endpoint with basic information."""
        return {
            "name": "SentineLLM API",
            "version": "0.1.0",
            "health": "/api/v1/health",
        }

    # Register routes
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(validation.router, prefix="/api/v1", tags=["Validation"])

    return app


# Create app instance for uvicorn
app = create_app()
