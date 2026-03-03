"""
API authentication dependency.
"""

import logging

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency that enforces API key authentication when enabled.

    Set ``REQUIRE_API_KEY=true`` and ``API_KEY=<secret>`` in the environment
    (or ``.env`` file) to activate protection.  When ``REQUIRE_API_KEY`` is
    ``False`` the dependency is a no-op so development stays frictionless.

    Raises:
        HTTPException 401: Header missing (when auth is required).
        HTTPException 403: Key present but wrong value.
        HTTPException 500: Auth required but no key configured on the server.
    """
    if not settings.REQUIRE_API_KEY:
        return

    if not settings.API_KEY:
        # Server misconfiguration — fail closed, never open
        logger.error(
            "REQUIRE_API_KEY is True but API_KEY is not configured. "
            "Set the API_KEY environment variable."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication is not configured",
        )

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Constant-time comparison to prevent timing attacks
    import hmac

    if not hmac.compare_digest(api_key.encode(), settings.API_KEY.encode()):
        logger.warning("Invalid API key received")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
