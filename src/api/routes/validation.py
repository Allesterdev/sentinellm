"""
Validation endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.prompt_validator import PromptValidator

from ..auth import require_api_key
from ..models import ErrorResponse, LayerResult, ValidationRequest, ValidationResponse

router = APIRouter()
logger = logging.getLogger(__name__)


# Maximum text length accepted per validation request (protects against DoS)
_MAX_TEXT_BYTES = 50_000  # 50 KB


def _get_validator() -> PromptValidator:
    """Get configured validator instance."""
    try:
        return PromptValidator()
    except (ValueError, ImportError) as e:
        logger.error("Failed to initialize validator: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validator initialization failed",
        ) from e


@router.post(
    "/validate",
    response_model=ValidationResponse,
    dependencies=[Depends(require_api_key)],
    responses={
        200: {"description": "Validation successful"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "API key missing"},
        403: {"model": ErrorResponse, "description": "Content blocked by security filters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def validate_text(request: ValidationRequest):
    """
    Validate text for security threats.

    This endpoint checks the input text through multiple security layers:
    - **Secret scanning**: Finds leaked credentials and sensitive data
    - **Prompt injection detection**: Identifies manipulation attempts
    - **LLM semantic analysis** (if enabled): Deep content understanding
    - **Entropy analysis**: Detects anomalous patterns

    Args:
        request: Validation request with text to analyze

    Returns:
        ValidationResponse with safety status and threat details

    Raises:
        HTTPException: If validation fails or content is blocked
    """
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text field is required and cannot be empty",
        )

    if len(request.text.encode()) > _MAX_TEXT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Text exceeds maximum allowed size of {_MAX_TEXT_BYTES // 1000} KB",
        )

    validator = _get_validator()

    try:
        # Perform validation
        result = validator.validate(request.text)

        # Prepare response
        response_data = {
            "safe": result.safe,
            "blocked": not result.safe,
            "threat_level": result.threat_level,
            "reason": result.blocked_by if result.blocked_by else None,
        }

        # Include detailed layer results if requested
        if request.include_details:
            layers = []

            # Secret detection layer
            if result.secret_result:
                layers.append(
                    LayerResult(
                        name="secret_detection",
                        passed=not result.secret_result.found,
                        threat_level=result.secret_result.threat_level.name,
                        confidence=result.secret_result.confidence,
                        details={
                            "found": result.secret_result.found,
                            "secret_type": result.secret_result.secret_type.name
                            if result.secret_result.secret_type
                            else None,
                            "entropy": result.secret_result.entropy,
                        },
                    )
                )

            # Prompt injection layer
            if result.injection_result:
                layers.append(
                    LayerResult(
                        name="prompt_injection",
                        passed=not result.injection_result.found,
                        threat_level=result.injection_result.threat_level.name,
                        confidence=result.injection_result.confidence,
                        details={
                            "matched_patterns": result.injection_result.matched_patterns,
                            "match_count": len(result.injection_result.matches),
                        },
                    )
                )

            # LLM layer (if available)
            if result.llm_result:
                layers.append(
                    LayerResult(
                        name="llm_semantic",
                        passed=not result.llm_result.found,
                        threat_level=result.llm_result.threat_level.name,
                        confidence=result.llm_result.confidence,
                        details={
                            "attack_type": result.llm_result.attack_type,
                            "explanation": result.llm_result.explanation,
                            "model_used": result.llm_result.model_used,
                            "latency_ms": result.llm_result.latency_ms,
                        },
                    )
                )

            # Entropy layer (informational only)
            if result.entropy_result:
                layers.append(
                    LayerResult(
                        name="entropy",
                        passed=not result.entropy_result.anomaly_detected,
                        threat_level="NONE",
                        confidence=0.0,
                        details={
                            "entropy": result.entropy_result.entropy,
                            "anomaly_detected": result.entropy_result.anomaly_detected,
                        },
                    )
                )

            response_data["layers"] = layers

        # Return 403 if blocked
        if not result.safe:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Content blocked by security filters",
                    "reason": result.blocked_by,
                    "threat_level": result.threat_level,
                },
            )

        return ValidationResponse(**response_data)

    except (ValueError, RuntimeError) as e:
        logger.error("Validation error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation error",
        ) from e


@router.post(
    "/validate/batch",
    response_model=list[ValidationResponse],
    dependencies=[Depends(require_api_key)],
)
async def validate_batch(requests: list[ValidationRequest]):
    """
    Validate multiple texts in batch.

    Args:
        requests: List of validation requests (max 100)

    Returns:
        List of validation responses

    Raises:
        HTTPException: If batch size exceeds limit
    """
    if len(requests) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size exceeds maximum limit of 100",
        )

    oversized = [
        i for i, r in enumerate(requests) if r.text and len(r.text.encode()) > _MAX_TEXT_BYTES
    ]
    if oversized:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Items at positions {oversized[:5]} exceed the {_MAX_TEXT_BYTES // 1000} KB per-item limit",
        )

    validator = _get_validator()
    results = []

    for req in requests:
        try:
            result = validator.validate(req.text)
            results.append(
                ValidationResponse(
                    safe=result.safe,
                    blocked=not result.safe,
                    threat_level=result.threat_level,
                    reason=result.blocked_by if result.blocked_by else None,
                )
            )
        except (ValueError, RuntimeError) as e:
            logger.warning("Batch validation error for item: %s", e)
            results.append(
                ValidationResponse(
                    safe=False,
                    blocked=True,
                    threat_level="UNKNOWN",
                    reason="Validation error",
                )
            )

    return results
