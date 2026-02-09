"""
LLM Proxy Server - Validates requests before forwarding to LLM providers.

This proxy sits between your application (OpenClaw, etc.) and LLM providers
(OpenAI, Claude, etc.) to validate inputs for security threats.
"""

import logging

import httpx
from fastapi import FastAPI, HTTPException, Request, Response

from ..core.prompt_validator import PromptValidator

logger = logging.getLogger(__name__)


def create_proxy_app() -> FastAPI:
    """Create proxy FastAPI application."""
    app = FastAPI(
        title="SentineLLM Proxy",
        description="Security proxy for LLM API requests",
        version="0.1.0",
    )

    validator = PromptValidator()

    @app.post("/v1/chat/completions")
    @app.post("/v1/completions")
    async def proxy_openai(request: Request):
        """Proxy OpenAI-compatible API calls with security validation."""
        try:
            # Parse request body
            body = await request.json()

            # Extract messages to validate
            messages_to_validate = []

            if "messages" in body:  # Chat completions
                for msg in body["messages"]:
                    if isinstance(msg, dict) and "content" in msg:
                        messages_to_validate.append(msg["content"])
            elif "prompt" in body:  # Completions
                messages_to_validate.append(body["prompt"])

            # Validate all messages
            for content in messages_to_validate:
                if not content:
                    continue

                result = validator.validate(str(content))

                if not result.safe:
                    logger.warning(
                        "Blocked request: %s (threat: %s)",
                        result.blocked_by,
                        result.threat_level,
                    )
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": {
                                "message": f"Request blocked by security filter: {result.blocked_by}",
                                "type": "security_violation",
                                "threat_level": result.threat_level,
                                "blocked_by": result.blocked_by,
                            }
                        },
                    )

            # Get target LLM URL from headers or environment
            target_url = request.headers.get("X-Target-URL", "https://api.openai.com")

            # Forward to actual LLM
            async with httpx.AsyncClient() as client:
                # Prepare headers (remove proxy-specific headers)
                forward_headers = dict(request.headers)
                forward_headers.pop("host", None)
                forward_headers.pop("x-target-url", None)

                # Forward request
                response = await client.post(
                    f"{target_url}{request.url.path}",
                    json=body,
                    headers=forward_headers,
                    timeout=120.0,
                )

                # Return response
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.headers.get("content-type"),
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Proxy error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "service": "sentinellm-proxy"}

    return app


def run_proxy(host: str = "127.0.0.1", port: int = 8080):
    """Run the proxy server.

    Args:
        host: Host to bind to. Default 127.0.0.1 (localhost only).
              Use 0.0.0.0 only if you need network access (security risk).
        port: Port to listen on.
    """
    import uvicorn

    app = create_proxy_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_proxy()
