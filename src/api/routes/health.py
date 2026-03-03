"""
Health check endpoints.
"""

import logging

from fastapi import APIRouter

from src.utils.config_loader import get_config

from ..models import HealthResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status and Ollama availability.
    """
    try:
        config = get_config()
        ollama_enabled = config.prompt_injection.layers and config.prompt_injection.layers.get(
            "llm", {}
        ).get("enabled", False)

        if ollama_enabled:
            # Check Ollama health
            from src.filters.llm_detector import OllamaDetector

            try:
                detector = OllamaDetector(config.ollama)
                ollama_health = detector.health_check()
                detector.close()

                return HealthResponse(
                    status="healthy",
                    version="0.1.0",
                    ollama_available=True,
                    ollama_status="connected" if ollama_health else "unavailable",
                )
            except (ConnectionError, TimeoutError) as e:
                logger.warning("Ollama connection failed: %s", e)
                return HealthResponse(
                    status="healthy",
                    version="0.1.0",
                    ollama_available=False,
                    ollama_status="unavailable",
                )
        else:
            return HealthResponse(
                status="healthy",
                version="0.1.0",
                ollama_available=False,
                ollama_status="disabled",
            )

    except ValueError as e:
        logger.error("Configuration error: %s", e)
        return HealthResponse(
            status="healthy",
            version="0.1.0",
            ollama_available=False,
            ollama_status="config_error",
        )


@router.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "SentineLLM API",
        "version": "0.1.0",
        "description": "AI Security Gateway",
        "health": "/api/v1/health",
    }
