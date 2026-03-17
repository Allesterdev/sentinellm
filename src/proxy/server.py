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

import copy
import hashlib
import json
import logging
import os
import posixpath
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from ..core.prompt_validator import PromptValidator
from ..utils.constants import SECRET_PATTERNS, SecretType

# Descriptive placeholders per secret type — meaningful for both humans and
# the LLM that will receive the sanitised message.  The text is intentionally
# verbose so the model understands *why* a value is missing and does not try
# to hallucinate or reconstruct the original secret.
_SECRET_PLACEHOLDERS: dict[SecretType, str] = {
    SecretType.AWS_ACCESS_KEY: "[AWS_ACCESS_KEY_REMOVED_BY_SECURITY]",
    SecretType.AWS_SECRET_KEY: "[AWS_SECRET_KEY_REMOVED_BY_SECURITY]",
    SecretType.GITHUB_TOKEN: "[GITHUB_TOKEN_REMOVED_BY_SECURITY]",
    SecretType.BEARER_TOKEN: "[BEARER_TOKEN_REMOVED_BY_SECURITY]",
    SecretType.JWT_TOKEN: "[JWT_TOKEN_REMOVED_BY_SECURITY]",
    SecretType.GOOGLE_API_KEY: "[GOOGLE_API_KEY_REMOVED_BY_SECURITY]",
    SecretType.OPENAI_API_KEY: "[OPENAI_API_KEY_REMOVED_BY_SECURITY]",
    SecretType.ANTHROPIC_API_KEY: "[ANTHROPIC_API_KEY_REMOVED_BY_SECURITY]",
    SecretType.HUGGINGFACE_TOKEN: "[HUGGINGFACE_TOKEN_REMOVED_BY_SECURITY]",
    SecretType.STRIPE_KEY: "[STRIPE_KEY_REMOVED_BY_SECURITY]",
    SecretType.SLACK_TOKEN: "[SLACK_TOKEN_REMOVED_BY_SECURITY]",
    SecretType.SENDGRID_KEY: "[SENDGRID_KEY_REMOVED_BY_SECURITY]",
    SecretType.GROQ_API_KEY: "[GROQ_API_KEY_REMOVED_BY_SECURITY]",
    SecretType.OPENROUTER_API_KEY: "[OPENROUTER_API_KEY_REMOVED_BY_SECURITY]",
    SecretType.GENERIC_API_KEY: "[API_KEY_REMOVED_BY_SECURITY]",
    SecretType.PRIVATE_KEY: "[PRIVATE_KEY_REMOVED_BY_SECURITY]",
    SecretType.CREDIT_CARD: "[CREDIT_CARD_REMOVED_BY_SECURITY]",
}

logger = logging.getLogger(__name__)

# SHA-256 hashes (truncated) of secrets already warned about in this proxy session.
# Ensures the WARNING is emitted only the first time a specific secret appears,
# silencing subsequent turns where the same value remains in the history.
_seen_secret_hashes: set[str] = set()


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


def _normalize_path(path: str) -> str:
    """Normalize a user-supplied URL path to prevent path traversal (partial SSRF).

    Uses ``posixpath.normpath`` to collapse ``..`` and ``.`` components so that
    a crafted path like ``/v1/../../admin`` cannot escape the intended API root
    on the target LLM server.  The result always starts with ``/``.
    """
    # Ensure a leading slash so normpath does not treat it as relative.
    normalized = posixpath.normpath("/" + path.lstrip("/"))
    # normpath may strip the trailing slash for root — keep it as "/".
    return normalized if normalized.startswith("/") else "/" + normalized


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


def _extract_user_messages_from_body(body: dict) -> list[str]:
    """Extract only the **current** user turn from any LLM API request body.

    Used exclusively for prompt injection detection.  Returns at most the
    most-recent user message so that conversation history — which may contain
    a previously blocked injection — does not cause every subsequent request
    in the same multi-turn session to be blocked as well.

    Intentionally skips:
      - System prompts (``system``, ``systemInstruction``, ``instructions``) —
        trusted content written by the operator, not the end user.
      - Assistant / model turns (``role=assistant``, ``role=model``) — LLM
        responses cannot be an injection from the user.
      - **Historical** user turns — already inspected when they were sent;
        re-scanning them would permanently block any conversation that ever
        contained an injection attempt.

    Only the **last** ``role=user`` message (or equivalent plain prompt) is
    returned, matching exactly what the user typed in this request.

    Supports:
      - OpenAI Chat Completions / Anthropic: last ``messages[role=user]``
      - OpenAI Completions / Ollama generate: ``prompt``
      - OpenAI Responses API: last user-role item in ``input``
      - Google Gemini: last ``contents[role=user]``
    """
    messages: list[str] = []

    # OpenAI Chat / Anthropic / Ollama chat — only the LAST role=user turn.
    if "messages" in body:
        for msg in reversed(body["messages"]):
            if isinstance(msg, dict) and msg.get("role") == "user" and "content" in msg:
                messages.extend(_extract_text_from_content(msg["content"]))
                break  # stop after the most-recent user message

    # OpenAI Completions / Ollama generate: plain prompt — always the current turn.
    if "prompt" in body:
        if isinstance(body["prompt"], str):
            messages.append(body["prompt"])
        elif isinstance(body["prompt"], list):
            for p in body["prompt"]:
                if isinstance(p, str):
                    messages.append(p)

    # OpenAI Responses API: input — only the last user-role item.
    if "input" in body:
        inp = body["input"]
        if isinstance(inp, str):
            messages.append(inp)
        elif isinstance(inp, list):
            for item in reversed(inp):
                if isinstance(item, str):
                    messages.append(item)
                    break
                if isinstance(item, dict) and item.get("role") in ("user", None):
                    if "content" in item:
                        messages.extend(_extract_text_from_content(item["content"]))
                    if "text" in item:
                        messages.append(item["text"])
                    break  # stop after the most-recent user item

    # Google Gemini: contents — only the LAST role=user item.
    if "contents" in body:
        for content_item in reversed(body["contents"]):
            if isinstance(content_item, dict) and content_item.get("role") == "user":
                for part in content_item.get("parts", []):
                    if isinstance(part, dict) and "text" in part:
                        messages.append(part["text"])
                break  # stop after the most-recent user turn

    # Fallback: top-level "text" (no role info available — scan it).
    if not messages and "text" in body and isinstance(body["text"], str):
        messages.append(body["text"])

    return messages


def _redact_secrets_in_text(text: str) -> tuple[str, int]:
    """Replace detected secrets in *text* with descriptive placeholders.

    Each secret type gets a specific placeholder that is meaningful to both
    humans reading the logs and the LLM that receives the sanitised message.
    The placeholder text tells the model that a sensitive value was removed
    by SentineLLM so it does not try to hallucinate or reconstruct the
    original secret.

    Example::

        "My key is AIzaSyB-abc123"  →  "My key is [API_KEY_REMOVED_BY_SECURITY]"

    Args:
        text: Any plain-text string extracted from an LLM API request.

    Returns:
        A tuple ``(sanitized_text, count)`` where *count* is the number of
        distinct secrets that were redacted.
    """
    count = 0
    sanitized = text
    for secret_type, pattern in SECRET_PATTERNS.items():
        placeholder = _SECRET_PLACEHOLDERS.get(secret_type, "[SENSITIVE_DATA_REMOVED_BY_SECURITY]")
        replaced, n = pattern.subn(placeholder, sanitized)
        count += n
        sanitized = replaced
    return sanitized, count


def _sanitize_content_block(content) -> tuple[any, int]:
    """Recursively sanitize a content value (str, list, or dict).

    Returns the sanitized value and the total number of secrets redacted.
    """
    total = 0
    if isinstance(content, str):
        sanitized, n = _redact_secrets_in_text(content)
        return sanitized, n
    elif isinstance(content, list):
        result = []
        for item in content:
            sanitized_item, n = _sanitize_content_block(item)
            result.append(sanitized_item)
            total += n
        return result, total
    elif isinstance(content, dict):
        result = {}
        for key, value in content.items():
            if key in ("text", "content", "prompt", "input", "system", "instructions"):
                sanitized_value, n = _sanitize_content_block(value)
                result[key] = sanitized_value
                total += n
            else:
                result[key] = value
        return result, total
    return content, 0


def _sanitize_body_secrets(body: dict) -> tuple[dict, int]:
    """Sanitize all text content inside an LLM API request body.

    Walks the entire request body structure and replaces detected secrets
    with ``[REDACTED:<TYPE>]`` placeholders.  The original body is **not**
    mutated — a new dict is returned together with the total count of
    redacted secrets.

    Supports the same fields as :func:`_extract_messages_from_body`:
    ``messages``, ``prompt``, ``input``, ``system``, ``instructions``,
    ``contents`` (Gemini), ``systemInstruction`` (Gemini), and ``text``.

    Args:
        body: Parsed JSON request body.

    Returns:
        ``(sanitized_body, total_redacted)``
    """
    sanitized = copy.deepcopy(body)
    total = 0

    # OpenAI Chat / Anthropic: messages[].content
    if "messages" in sanitized and isinstance(sanitized["messages"], list):
        for msg in sanitized["messages"]:
            if isinstance(msg, dict) and "content" in msg:
                msg["content"], n = _sanitize_content_block(msg["content"])
                total += n

    # OpenAI Completions: prompt
    if "prompt" in sanitized:
        sanitized["prompt"], n = _sanitize_content_block(sanitized["prompt"])
        total += n

    # OpenAI Responses / input
    if "input" in sanitized:
        sanitized["input"], n = _sanitize_content_block(sanitized["input"])
        total += n

    # Anthropic system
    if "system" in sanitized:
        sanitized["system"], n = _sanitize_content_block(sanitized["system"])
        total += n

    # Responses API instructions
    if "instructions" in sanitized and isinstance(sanitized["instructions"], str):
        sanitized["instructions"], n = _redact_secrets_in_text(sanitized["instructions"])
        total += n

    # Google Gemini: contents[].parts[].text
    if "contents" in sanitized and isinstance(sanitized["contents"], list):
        for content_item in sanitized["contents"]:
            if isinstance(content_item, dict):
                for part in content_item.get("parts", []):
                    if isinstance(part, dict) and "text" in part:
                        part["text"], n = _redact_secrets_in_text(part["text"])
                        total += n

    # Google Gemini: systemInstruction.parts[].text
    if "systemInstruction" in sanitized and isinstance(sanitized["systemInstruction"], dict):
        for part in sanitized["systemInstruction"].get("parts", []):
            if isinstance(part, dict) and "text" in part:
                part["text"], n = _redact_secrets_in_text(part["text"])
                total += n

    # Fallback top-level "text"
    if "text" in sanitized and isinstance(sanitized["text"], str):
        sanitized["text"], n = _redact_secrets_in_text(sanitized["text"])
        total += n

    return sanitized, total


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

    # Disable all API documentation endpoints — the proxy is an internal
    # security component and should not expose a browsable interface.
    app = FastAPI(
        title="SentineLLM Proxy",
        description="Security proxy for LLM API requests (input & output validation)",
        version="0.3.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # Determine target URL
    if target_url is None:
        target_url = os.environ.get("SENTINELLM_TARGET_URL", "https://api.openai.com")

    # Read output validation setting from env
    _validate_output = validate_output
    if os.environ.get("SENTINELLM_VALIDATE_OUTPUT", "").lower() in ("0", "false", "no"):
        _validate_output = False

    # Minimum threat level required to block a prompt-injection request.
    # Applies ONLY to prompt-injection findings — secrets are always redacted.
    # Options: LOW, MEDIUM, HIGH, CRITICAL (default: MEDIUM)
    _min_block_level = os.environ.get("SENTINELLM_MIN_BLOCK_LEVEL", "MEDIUM").upper()
    _block_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    _min_block_score = _block_levels.get(_min_block_level, 2)

    logger.info("Proxy will forward requests to: %s", target_url)
    logger.info("Output (DLP) validation: %s", "enabled" if _validate_output else "disabled")
    logger.info("Minimum block level (injection): %s", _min_block_level)
    logger.info("Secret handling: always redact with descriptive placeholder")
    validator = PromptValidator()

    async def _validate_and_forward(request: Request) -> Response:
        """Core proxy logic: validate input → forward → validate output → return."""
        # Normalize path to prevent path-traversal / partial-SSRF (CWE-918).
        # Strip control characters (CR, LF, tab…) to prevent log injection
        # (CWE-117 / CodeQL py/log-injection) — done once here so every
        # subsequent logger call that references request_path is safe.
        request_path = _normalize_path(request.url.path).translate(
            str.maketrans("", "", "\r\n\t\x00\x08\x0b\x0c\x1b")
        )
        query_params = str(request.url.query)
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            # === BODY SIZE GUARD (DoS prevention) ===
            # Reject bodies larger than 10 MB to prevent memory exhaustion.
            # Large legitimate LLM requests (vision, long contexts) rarely exceed this.
            _max_body_bytes = 10 * 1024 * 1024  # 10 MB
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > _max_body_bytes:
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": {
                            "message": "Request body too large (max 10 MB)",
                            "type": "payload_too_large",
                        }
                    },
                )

            # Parse request body
            raw_body = await request.body()
            if len(raw_body) > _max_body_bytes:
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": {
                            "message": "Request body too large (max 10 MB)",
                            "type": "payload_too_large",
                        }
                    },
                )
            body = {}
            if raw_body:
                try:
                    body = json.loads(raw_body)
                except json.JSONDecodeError:
                    # Not JSON — forward as-is (e.g., multipart, health checks)
                    pass

            # === INPUT VALIDATION ===
            # Secrets   → always redacted with a descriptive placeholder.
            #             The sanitised request is forwarded so the conversation
            #             continues and the LLM understands why the value is missing.
            # Injection → blocked when threat score >= _min_block_score.
            #             Only user-role messages are scanned — system prompts and
            #             assistant turns are trusted content and must not be flagged.
            if isinstance(body, dict):
                # Secrets: scan entire body (redact leaked keys even in history)
                # Injection: scan only role=user turns to avoid false positives
                #            from system prompts like "act as a helpful assistant"
                all_messages = _extract_messages_from_body(body)
                user_messages = _extract_user_messages_from_body(body)

                # --- Pass 1: Secrets — scan ALL content (history + system prompt) ---
                _body_needs_redaction = False
                for content in all_messages:
                    if not content or not content.strip():
                        continue
                    result = validator.validate(str(content))
                    if not result.safe and result.blocked_by == "secret_detection":
                        _body_needs_redaction = True
                        # Emit WARNING only once per unique secret value.
                        # We hash each matched value (never logged) to track
                        # what has already been reported this session.
                        new_hashes = []
                        for stype, pattern in SECRET_PATTERNS.items():
                            for m in pattern.finditer(content):
                                h = hashlib.sha256(m.group(0).encode()).hexdigest()[:16]
                                if h not in _seen_secret_hashes:
                                    _seen_secret_hashes.add(h)
                                    new_hashes.append((stype.name, len(m.group(0))))
                        if new_hashes:
                            for token_type, matched_len in new_hashes:
                                logger.warning(
                                    "[%s] SENSITIVE DATA DETECTED on %s: type=%s length=%d — redacting and forwarding (will not warn again for this value)",
                                    timestamp,
                                    request_path,
                                    token_type,
                                    matched_len,
                                )

                # --- Pass 2: Injection — scan ONLY role=user content ---
                # System prompts and assistant/model turns are trusted operator
                # content; scanning them causes false positives when the system
                # prompt legitimately contains phrases like "act as a helpful
                # assistant" that the keyword layer would score as suspicious.
                for content in user_messages:
                    if not content or not content.strip():
                        continue
                    result = validator.validate(str(content))
                    if not result.safe and result.blocked_by != "secret_detection":
                        threat_score = _block_levels.get(result.threat_level.upper(), 0)
                        if threat_score >= _min_block_score:
                            # --- Prompt injection: block ---
                            logger.warning(
                                "[%s] INPUT BLOCKED on %s: filter=%s threat=%s",
                                timestamp,
                                request_path,
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
                                        "direction": "input",
                                    }
                                },
                            )
                        else:
                            logger.info(
                                "[%s] INPUT WARNING on %s: filter=%s threat=%s (below min_block_level=%s)",
                                timestamp,
                                request_path,
                                result.blocked_by,
                                result.threat_level,
                                _min_block_level,
                            )

                # Sanitise the full body in a single pass if any secret was found
                if _body_needs_redaction:
                    sanitized_body, redaction_count = _sanitize_body_secrets(body)
                    raw_body = json.dumps(sanitized_body, ensure_ascii=False).encode("utf-8")
                    body = sanitized_body
                    logger.info(
                        "[%s] BODY SANITISED on %s: %d value(s) replaced with descriptive placeholder — request forwarded to LLM",
                        timestamp,
                        request_path,
                        redaction_count,
                    )

                logger.info(
                    "[%s] INPUT OK on %s (%d messages validated)",
                    timestamp,
                    request_path,
                    len(user_messages),
                )

            # === FORWARD TO LLM ===
            # X-Target-URL is disabled for security (SSRF / exfiltration risk).
            # The proxy always forwards to the configured target_url.
            if request.headers.get("X-Target-URL"):
                logger.warning(
                    "[%s] X-Target-URL header ignored (disabled for security): %s",
                    timestamp,
                    request.headers.get("X-Target-URL"),
                )
            forward_url = target_url

            # Fix Google Gemini API paths: add /v1beta prefix if missing
            # Google Gemini expects /v1beta/models/... but some clients send /models/...
            if "generativelanguage.googleapis.com" in forward_url:
                if request_path.startswith("/models/") or request_path.startswith("/v1/models/"):
                    if not request_path.startswith("/v1beta/"):
                        # Remove /v1/ prefix if present, then add /v1beta/
                        clean_path = request_path.replace("/v1/models/", "/models/")
                        request_path = f"/v1beta{clean_path}"
                        logger.debug(f"Rewrote Google Gemini path to: {request_path}")

            # Detect streaming requests (SSE / Server-Sent Events)
            # Use proper query param parsing to avoid substring false positives
            # (e.g. "upstream=true" incorrectly matching "stream=true")
            parsed_qs = parse_qs(query_params)
            is_streaming = (
                parsed_qs.get("alt", [None])[0] == "sse"
                or parsed_qs.get("stream", [None])[0] == "true"
                or request.headers.get("accept") == "text/event-stream"
                # OpenAI/Ollama/Anthropic: "stream": true in JSON body
                or (isinstance(body, dict) and body.get("stream") is True)
            )

            # Build full path with query parameters preserved
            full_path = f"{request_path}?{query_params}" if query_params else request_path

            # Prepare headers (remove proxy-specific headers)
            forward_headers = dict(request.headers)
            forward_headers.pop("host", None)
            forward_headers.pop("x-target-url", None)
            # Remove content-length as httpx recalculates it
            forward_headers.pop("content-length", None)

            # === STREAMING: Pass-through without output validation ===
            if is_streaming:
                logger.info(
                    "[%s] STREAMING request on %s (output validation skipped)",
                    timestamp,
                    request_path,
                )

                # For streaming, we must NOT use `async with` for the client
                # because the context manager would close the client before
                # FastAPI consumes the StreamingResponse generator.
                # Instead, we close client+response inside the generator's finally.
                client = httpx.AsyncClient()

                try:
                    # Create streaming request
                    req = client.build_request(
                        method=request.method,
                        url=f"{forward_url}{full_path}",
                        content=raw_body,
                        headers=forward_headers,
                        timeout=120.0,
                    )

                    # Send request and get streaming response
                    resp = await client.send(req, stream=True)
                except Exception:
                    # If send() fails, close the client to avoid resource leak
                    # (stream_chunks() generator never runs, so its finally won't fire)
                    await client.aclose()
                    raise

                # Prepare response headers (exclude hop-by-hop headers)
                response_headers = {}
                hop_by_hop = {"transfer-encoding", "connection", "keep-alive"}
                for k, v in resp.headers.items():
                    if k.lower() not in hop_by_hop:
                        response_headers[k] = v

                # Stream chunks directly to client
                async def stream_chunks():
                    try:
                        async for chunk in resp.aiter_raw():
                            yield chunk
                    except (
                        httpx.ReadError,
                        httpx.StreamError,
                        httpx.TimeoutException,
                        httpx.ProtocolError,
                    ):
                        # Client (e.g. OpenClaw) closed connection before
                        # upstream finished streaming — this is normal for
                        # SSE streams where the client gets the final event
                        # and disconnects. Also handle timeouts and protocol
                        # errors that can occur mid-stream.
                        logger.debug("Upstream stream closed (client likely disconnected)")
                    finally:
                        # Ensure response AND client are closed after streaming
                        await resp.aclose()
                        await client.aclose()

                return StreamingResponse(
                    stream_chunks(),
                    status_code=resp.status_code,
                    headers=response_headers,
                    media_type=resp.headers.get("content-type", "text/event-stream"),
                )

            # === NON-STREAMING: Regular request with output validation ===
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=request.method,
                    url=f"{forward_url}{full_path}",
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
                                    "[%s] OUTPUT BLOCKED on %s: filter=%s threat=%s",
                                    timestamp,
                                    request_path,
                                    result.blocked_by,
                                    result.threat_level,
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
                                    "[%s] OUTPUT WARNING on %s: filter=%s threat=%s (below min_block_level=%s)",
                                    timestamp,
                                    request_path,
                                    result.blocked_by,
                                    result.threat_level,
                                    _min_block_level,
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
            # Do NOT expose internal exception details to the client (information leakage).
            raise HTTPException(
                status_code=500,
                detail={"error": {"message": "Internal proxy error", "type": "internal_error"}},
            ) from e

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
        # X-Target-URL is disabled for security (SSRF / exfiltration risk).
        forward_url = target_url
        query_params = str(request.url.query)
        # Normalize to prevent path-traversal / partial-SSRF (CWE-918).
        forward_path = _normalize_path(f"/v1/{path}")
        if query_params:
            forward_path = f"{forward_path}?{query_params}"
        async with httpx.AsyncClient() as client:
            forward_headers = dict(request.headers)
            forward_headers.pop("host", None)
            # strip even though ignored
            forward_headers.pop("x-target-url", None)
            forward_headers.pop("content-length", None)
            response = await client.request(
                method=request.method,
                url=f"{forward_url}{forward_path}",
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
            # Do not expose target_url or internal config — information leakage.
            return {
                "status": "healthy",
                "service": "sentinellm-proxy",
                "version": "0.3.0",
            }
        if request.method == "POST":
            return await _validate_and_forward(request)
        # For GET/other methods, forward without validation
        # X-Target-URL is disabled for security (SSRF / exfiltration risk).
        forward_url = target_url
        query_params = str(request.url.query)
        # Normalize to prevent path-traversal / partial-SSRF (CWE-918).
        forward_path = _normalize_path(f"/{path}")
        if query_params:
            forward_path = f"{forward_path}?{query_params}"
        async with httpx.AsyncClient() as client:
            forward_headers = dict(request.headers)
            forward_headers.pop("host", None)
            # strip even though ignored
            forward_headers.pop("x-target-url", None)
            forward_headers.pop("content-length", None)
            response = await client.request(
                method=request.method,
                url=f"{forward_url}{forward_path}",
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
        # Do not expose target_url or internal config — information leakage.
        return {
            "status": "healthy",
            "service": "sentinellm-proxy",
            "version": "0.3.0",
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
