"""
API request/response models.
"""

from pydantic import BaseModel, Field


class ValidationRequest(BaseModel):
    """Request model for text validation."""

    text: str = Field(
        ...,
        description="Text to validate for security threats",
        min_length=1,
        max_length=100000,
        examples=["What is the capital of France?"],
    )

    include_details: bool = Field(
        default=False,
        description="Include detailed information about detection layers",
    )


class LayerResult(BaseModel):
    """Result from a single validation layer."""

    name: str = Field(..., description="Layer name")
    passed: bool = Field(..., description="Whether the layer passed")
    threat_level: str = Field(..., description="Threat level: NONE, LOW, MEDIUM, HIGH, CRITICAL")
    confidence: float = Field(..., description="Confidence score (0.0 - 1.0)", ge=0.0, le=1.0)
    details: dict = Field(default_factory=dict, description="Additional details")


class ValidationResponse(BaseModel):
    """Response model for validation results."""

    safe: bool = Field(..., description="Whether the text is safe")
    blocked: bool = Field(..., description="Whether the text was blocked")
    threat_level: str = Field(..., description="Overall threat level")
    reason: str | None = Field(None, description="Reason for blocking if blocked")
    layers: list[LayerResult] | None = Field(
        None, description="Detailed results from each layer (if include_details=true)"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status", examples=["healthy"])
    version: str = Field(..., description="API version", examples=["0.1.0"])
    ollama_available: bool = Field(..., description="Whether Ollama is available")
    ollama_status: str | None = Field(None, description="Ollama status details")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Detailed error information")
    code: str | None = Field(None, description="Error code")
