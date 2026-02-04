"""
API configuration settings.
"""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API settings."""

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    # API Configuration
    API_HOST: str = "0.0.0.0"  # nosec B104 # noqa: S104 - Required for Docker
    API_PORT: int = 8000
    API_WORKERS: int = 4

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Security
    API_KEY_HEADER: str = "X-API-Key"
    REQUIRE_API_KEY: bool = False

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds


settings = Settings()
