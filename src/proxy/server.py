"""
LLM Proxy Server - Validates requests before forwarding to LLM providers.

This proxy sits between your application (OpenClaw, etc.) and LLM providers
(OpenAI, Claude, Gemini, etc.) to validate inputs AND outputs for security threats.

Supported endpoints (all intercepted transparently):
  - POST /v1/chat/completions              (OpenAI Chat Completions API)
  - POST /v1/completions                   (OpenAI Completions API)
  - POST /v1/responses                     (OpenAI Responses API — used by OpenClaw)
  - POST /v1/messages                      (Anthropic Messages API)
  - POST /v1beta/models/*:generateContent  (Google Gemini API)
  - POST /api/generate, /api/chat          (Ollama native API)
  - ANY  /v1/{path}                        (catch-all for /v1/* endpoints)
  - ANY  /{path}                           (universal catch-all for ANY provider)
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Response

from ..core.prompt_validator import PromptValidator

logger = logging.getLogger(__name__)


def _load_env_file() -> None:
    """Load environment variables from ~/.sentinellm.env if it exists."""
    env_path = Path.home() / ".sentinellm.env"
    if not env_path.exists():
        return

    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Only set if not already in environment
                    if key.strip() and key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()
        logger.info(f"Loaded environment from {env_path}")
    except Exception as e:
        logger.warning(f"Failed to load {env_path}: {e}")


def _extract_text_from_content(content) -> list[str]:
    """Extract text strings from various content formats.

    Handles:
      - Plain strings
      - Lists of content blocks (OpenAI vision format, Anthropic format)
      - Nested structures
    """
    texts = []
    if isinstance(content, str):
        texts.append(content)
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    texts.append(item["text"])
                elif "content" in item:
                    texts.extend(_extract_text_from_content(item["content"]))
    return texts


def _extract_messages_from_body(body: dict) -> list[str]:
    """Extract all text content from any LLM API request body.

    Supports:
      - OpenAI Chat Completions: body.messages[].content
      - OpenAI Completions: body.prompt
      - OpenAI Responses API: body.input (string or list of messages)
      - Anthropic Messages API: body.messages[].content + body.system
      - Google Gemini: body.contents[].parts[].text + body.systemInstruction
      - Ollama: body.prompt (generate) + body.messages[].content (chat)
      - Generic: deep-scan any "text", "content", "prompt" string fields
    """
    messages = []

    # OpenAI Chat Completions / Anthropic Messages: messages[].content
    if "messages" in body:
        for msg in body["messages"]:
            if isinstance(msg, dict) and "content" in msg:
                messages.extend(_extract_text_from_content(msg["content"]))

    # OpenAI Completions: prompt
    if "prompt" in body:
        if isinstance(body["prompt"], str):
            messages.append(body["prompt"])
        elif isinstance(body["prompt"], list):
            for p in body["prompt"]:
                if isinstance(p, str):
                    messages.append(p)

    # OpenAI Responses API: input (used by OpenClaw with openai-responses)
    if "input" in body:
        inp = body["input"]
        if isinstance(inp, str):
            messages.append(inp)
        elif isinstance(inp, list):
            for item in inp:
                if isinstance(item, str):
                    messages.append(item)
                elif isinstance(item, dict):
                    # input can be a list of message objects
                    if "content" in item:
                        messages.extend(_extract_text_from_content(item["content"]))
                    # or role-based with text
                    if "text" in item:
                        messages.append(item["text"])

    # Anthropic: system prompt
    if "system" in body:
        if isinstance(body["system"], str):
            messages.append(body["system"])
        elif isinstance(body["system"], list):
            for item in body["system"]:
                if isinstance(item, dict) and item.get("type") == "text":
                    messages.append(item["text"])

    # Instructions (Responses API)
    if "instructions" in body and isinstance(body["instructions"], str):
        messages.append(body["instructions"])

    # Google Gemini: contents[].parts[].text
    if "contents" in body:
        for content_item in body["contents"]:
            if isinstance(content_item, dict):
                for part in content_item.get("parts", []):
                    if isinstance(part, dict) and "text" in part:
                        messages.append(part["text"])

    # Google Gemini: systemInstruction.parts[].text
    if "systemInstruction" in body:
        si = body["systemInstruction"]
        if isinstance(si, dict):
            for part in si.get("parts", []):
                if isinstance(part, dict) and "text" in part:
                    messages.append(part["text"])

    # Ollama generate API: body.prompt (string)
    # (body.prompt as string already handled above)

    # Fallback: deep-scan for any top-level "text" field not yet captured
    if not messages and "text" in body and isinstance(body["text"], str):
        messages.append(body["text"])

    return messages


def _extract_text_from_response(response_body: bytes) -> list[str]:
    """Extract text content from LLM response body for output validation (DLP).

    Supports:
      - OpenAI Chat Completions: choices[].message.content
      - OpenAI Responses API: output[].content[].text
      - Anthropic Messages: content[].text
      - Google Gemini: candidates[].content.parts[].text
      - Ollama: response (generate) / message.content (chat)
    """
    texts = []
    try:
        data = json.loads(response_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return texts

    if not isinstance(data, dict):
        return texts

    # OpenAI Chat Completions
    for choice in data.get("choices", []):
        if isinstance(choice, dict):
            msg = choice.get("message", {})
            if isinstance(msg, dict) and "content" in msg:
                texts.extend(_extract_text_from_content(msg["content"]))

    # OpenAI Responses API
    for output_item in data.get("output", []):
        if isinstance(output_item, dict):
            for content_block in output_item.get("content", []):
                if isinstance(content_block, dict) and content_block.get("type") == "text":
                    texts.append(content_block["text"])

    # Anthropic Messages API
    for content_block in data.get("content", []):
        if isinstance(content_block, dict) and content_block.get("type") == "text":
            texts.append(content_block["text"])

    # Google Gemini: candidates[].content.parts[].text
    for candidate in data.get("candidates", []):
        if isinstance(candidate, dict):
            candidate_content = candidate.get("content", {})
            if isinstance(candidate_content, dict):
                for part in candidate_content.get("parts", []):
                    if isinstance(part, dict) and "text" in part:
                        texts.append(part["text"])

    # Ollama generate API: response field
    if "response" in data and isinstance(data["response"], str):
        texts.append(data["response"])

    # Ollama chat API: message.content
    msg = data.get("message")
    if isinstance(msg, dict) and "content" in msg:
        texts.extend(_extract_text_from_content(msg["content"]))

    # Simple text field (fallback)
    if not texts and "text" in data and isinstance(data["text"], str):
        texts.append(data["text"])

    return texts


def create_proxy_app(
    target_url: str | None = None,
    validate_output: bool = True,
) -> FastAPI:
    """Create proxy FastAPI application.

    Args:
        target_url: Target LLM URL to forward requests to.
                   Defaults to SENTINELLM_TARGET_URL env var or https://api.openai.com
        validate_output: Whether to also validate LLM responses for secret leakage (DLP).
                        Defaults to True.
    """
    # Load environment from ~/.sentinellm.env if exists
    _load_env_file()

    app = FastAPI(
        title="SentineLLM Proxy",
        description="Security proxy for LLM API requests (input & output validation)",
        version="0.3.0",
    )

    # Determine target URL
    if target_url is None:
        target_url = os.environ.get("SENTINELLM_TARGET_URL", "https://api.openai.com")

    # Read output validation setting from env
    _validate_output = validate_output
    if os.environ.get("SENTINELLM_VALIDATE_OUTPUT", "").lower() in ("0", "false", "no"):
        _validate_output = False

    # Minimum threat level required to actually block a request.
    # Requests below this level are logged but forwarded.
    # Options: LOW, MEDIUM, HIGH, CRITICAL (default: MEDIUM)
    _min_block_level = os.environ.get("SENTINELLM_MIN_BLOCK_LEVEL", "MEDIUM").upper()
    _block_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    _min_block_score = _block_levels.get(_min_block_level, 2)

    logger.info("Proxy will forward requests to: %s", target_url)
    logger.info("Output (DLP) validation: %s", "enabled" if _validate_output else "disabled")
    logger.info("Minimum block level: %s", _min_block_level)
    validator = PromptValidator()

    async def _validate_and_forward(request: Request) -> Response:
        """Core proxy logic: validate input → forward → validate output → return."""
        request_path = request.url.path
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            # Parse request body
            raw_body = await request.body()
            body = {}
            if raw_body:
                try:
                    body = json.loads(raw_body)
                except json.JSONDecodeError:
                    # Not JSON — forward as-is (e.g., multipart, health checks)
                    pass

            # === INPUT VALIDATION ===
            if isinstance(body, dict):
                messages_to_validate = _extract_messages_from_body(body)

                for content in messages_to_validate:
                    if not content or not content.strip():
                        continue

                    result = validator.validate(str(content))

                    if not result.safe:
                        threat_score = _block_levels.get(result.threat_level.upper(), 0)
                        if threat_score >= _min_block_score:
                            logger.warning(
                                "[%s] INPUT BLOCKED on %s: filter=%s threat=%s content_preview=%.80s",
                                timestamp,
                                request_path,
                                result.blocked_by,
                                result.threat_level,
                                content,
                            )
                            raise HTTPException(
                                status_code=403,
                                detail={
                                    "error": {
                                        "message": f"Request blocked by security filter: {result.blocked_by}",
                                        "type": "security_violation",
                                        "threat_level": result.threat_level,
                                        "blocked_by": result.blocked_by,
                                        "direction": "input",
                                    }
                                },
                            )
                        else:
                            logger.info(
                                "[%s] INPUT WARNING on %s: filter=%s threat=%s (below min_block_level=%s) content_preview=%.80s",
                                timestamp,
                                request_path,
                                result.blocked_by,
                                result.threat_level,
                                _min_block_level,
                                content,
                            )

                logger.info(
                    "[%s] INPUT OK on %s (%d messages validated)",
                    timestamp,
                    request_path,
                    len(messages_to_validate),
                )

            # === FORWARD TO LLM ===
            forward_url = request.headers.get("X-Target-URL", target_url)

            async with httpx.AsyncClient() as client:
                # Prepare headers (remove proxy-specific headers)
                forward_headers = dict(request.headers)
                forward_headers.pop("host", None)
                forward_headers.pop("x-target-url", None)
                # Remove content-length as httpx recalculates it
                forward_headers.pop("content-length", None)

                response = await client.request(
                    method=request.method,
                    url=f"{forward_url}{request_path}",
                    content=raw_body,
                    headers=forward_headers,
                    timeout=120.0,
                )

                # === OUTPUT VALIDATION (DLP) ===
                if _validate_output and response.status_code == 200:
                    output_texts = _extract_text_from_response(response.content)

                    for text in output_texts:
                        if not text or not text.strip():
                            continue

                        result = validator.validate(str(text))

                        if not result.safe:
                            threat_score = _block_levels.get(result.threat_level.upper(), 0)
                            if threat_score >= _min_block_score:
                                logger.warning(
                                    "[%s] OUTPUT BLOCKED on %s: filter=%s threat=%s content_preview=%.80s",
                                    timestamp,
                                    request_path,
                                    result.blocked_by,
                                    result.threat_level,
                                    text,
                                )
                                return Response(
                                    content=json.dumps(
                                        {
                                            "error": {
                                                "message": f"Response blocked by DLP filter: {result.blocked_by}",
                                                "type": "dlp_violation",
                                                "threat_level": result.threat_level,
                                                "blocked_by": result.blocked_by,
                                                "direction": "output",
                                            }
                                        }
                                    ),
                                    status_code=403,
                                    media_type="application/json",
                                )
                            else:
                                logger.info(
                                    "[%s] OUTPUT WARNING on %s: filter=%s threat=%s (below min_block_level=%s) content_preview=%.80s",
                                    timestamp,
                                    request_path,
                                    result.blocked_by,
                                    result.threat_level,
                                    _min_block_level,
                                    text,
                                )

                    if output_texts:
                        logger.info(
                            "[%s] OUTPUT OK on %s (%d text blocks validated)",
                            timestamp,
                            request_path,
                            len(output_texts),
                        )

                # Return original response
                # Filter out hop-by-hop headers
                response_headers = {}
                hop_by_hop = {"transfer-encoding", "connection", "keep-alive"}
                for k, v in response.headers.items():
                    if k.lower() not in hop_by_hop:
                        response_headers[k] = v

                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type"),
                )

        except HTTPException:
            raise
        except httpx.ConnectError as e:
            logger.error("Cannot connect to LLM provider: %s", e)
            raise HTTPException(
                status_code=502,
                detail={
                    "error": {
                        "message": f"Cannot reach LLM provider: {e}",
                        "type": "proxy_error",
                    }
                },
            ) from e
        except Exception as e:
            logger.error("Proxy error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e

    # ── Explicit routes (most common LLM API patterns) ──

    @app.post("/v1/chat/completions")
    async def proxy_chat_completions(request: Request):
        """OpenAI Chat Completions API."""
        return await _validate_and_forward(request)

    @app.post("/v1/completions")
    async def proxy_completions(request: Request):
        """OpenAI Completions API."""
        return await _validate_and_forward(request)

    @app.post("/v1/responses")
    async def proxy_responses(request: Request):
        """OpenAI Responses API (used by OpenClaw with openai-responses)."""
        return await _validate_and_forward(request)

    @app.post("/v1/messages")
    async def proxy_anthropic_messages(request: Request):
        """Anthropic Messages API."""
        return await _validate_and_forward(request)

    # ── Catch-all for any other /v1/* or root endpoints ──

    @app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_v1_catchall(request: Request, path: str):
        """Catch-all for /v1/* endpoints not explicitly handled."""
        if request.method == "POST":
            return await _validate_and_forward(request)
        # For GET requests (e.g., /v1/models), forward without validation
        forward_url = request.headers.get("X-Target-URL", target_url)
        async with httpx.AsyncClient() as client:
            forward_headers = dict(request.headers)
            forward_headers.pop("host", None)
            forward_headers.pop("x-target-url", None)
            forward_headers.pop("content-length", None)
            response = await client.request(
                method=request.method,
                url=f"{forward_url}/v1/{path}",
                headers=forward_headers,
                timeout=30.0,
            )
            response_headers = {
                k: v
                for k, v in response.headers.items()
                if k.lower() not in {"transfer-encoding", "connection", "keep-alive"}
            }
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
            )

    # ── Universal catch-all for ANY other path (Gemini, Ollama, etc.) ──

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_universal_catchall(request: Request, path: str):
        """Universal catch-all for non-/v1 paths.

        Handles:
          - Gemini: /v1beta/models/{model}:generateContent
          - Ollama: /api/generate, /api/chat
          - Any other LLM API endpoint
        """
        if path == "health":
            return {
                "status": "healthy",
                "service": "sentinellm-proxy",
                "version": "0.3.0",
                "target_url": target_url,
                "output_validation": _validate_output,
                "supported_providers": [
                    "openai",
                    "anthropic",
                    "google-gemini",
                    "ollama",
                    "any-openai-compatible",
                ],
            }
        if request.method == "POST":
            return await _validate_and_forward(request)
        # For GET/other methods, forward without validation
        forward_url = request.headers.get("X-Target-URL", target_url)
        async with httpx.AsyncClient() as client:
            forward_headers = dict(request.headers)
            forward_headers.pop("host", None)
            forward_headers.pop("x-target-url", None)
            forward_headers.pop("content-length", None)
            response = await client.request(
                method=request.method,
                url=f"{forward_url}/{path}",
                headers=forward_headers,
                timeout=30.0,
            )
            response_headers = {
                k: v
                for k, v in response.headers.items()
                if k.lower() not in {"transfer-encoding", "connection", "keep-alive"}
            }
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
            )

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "sentinellm-proxy",
            "version": "0.3.0",
            "target_url": target_url,
            "output_validation": _validate_output,
            "supported_providers": [
                "openai",
                "anthropic",
                "google-gemini",
                "ollama",
                "any-openai-compatible",
            ],
        }

    return app


def run_proxy(
    host: str = "127.0.0.1",
    port: int = 8080,
    target_url: str | None = None,
):
    """Run the proxy server.

    Args:
        host: Host to bind to. Default 127.0.0.1 (localhost only).
              Use 0.0.0.0 only if you need network access (security risk).
        port: Port to listen on. Default 8080 (different from OpenClaw Gateway 18789).
        target_url: Target LLM URL (e.g., https://generativelanguage.googleapis.com
                   for Gemini). Defaults to SENTINELLM_TARGET_URL env var or OpenAI.
    """
    import uvicorn

    app = create_proxy_app(target_url=target_url)

    print("🛡️  SentineLLM Proxy Server")
    print(f"   Listening on: http://{host}:{port}")
    print(
        f"   Forwarding to: {target_url or os.environ.get('SENTINELLM_TARGET_URL', 'https://api.openai.com')}"
    )
    print("   Press Ctrl+C to stop\n")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_proxy()
