"""Unit tests for the PromptValidator orchestrator."""

from unittest.mock import MagicMock, patch

from src.core.prompt_validator import PromptValidator, ValidationResult


class TestValidationResult:
    """Tests for ValidationResult defaults."""

    def test_defaults(self):
        """Default result is safe with no threats."""
        r = ValidationResult()
        assert r.safe is True
        assert r.threat_level == "NONE"
        assert r.blocked_by is None
        assert r.secret_result is None
        assert r.injection_result is None
        assert r.llm_result is None
        assert r.entropy_result is None


class TestPromptValidatorInit:
    """Tests for PromptValidator initialization."""

    def test_init_without_llm(self):
        """Initializes without LLM detector when not configured."""
        validator = PromptValidator()
        assert validator.secret_detector is not None
        assert validator.injection_detector is not None

    def test_init_llm_connection_error(self):
        """LLM detector init failure is handled gracefully."""
        mock_config = MagicMock()
        mock_config.prompt_injection.enabled = True
        mock_config.prompt_injection.layers = {"llm": {"enabled": True}}
        mock_config.secret_detection.enabled = True

        with (
            patch("src.core.prompt_validator.get_config", return_value=mock_config),
            patch(
                "src.core.prompt_validator.OllamaDetector",
                side_effect=ConnectionError("fail"),
            ),
        ):
            validator = PromptValidator()
            assert validator.llm_detector is None


class TestPromptValidatorValidate:
    """Tests for PromptValidator.validate method."""

    def test_empty_text_returns_safe(self):
        """Empty or whitespace-only text returns safe immediately."""
        validator = PromptValidator()
        result = validator.validate("")
        assert result.safe is True
        assert result.threat_level == "NONE"

    def test_whitespace_only_returns_safe(self):
        """Whitespace-only text returns safe immediately."""
        validator = PromptValidator()
        result = validator.validate("   \n\t  ")
        assert result.safe is True

    def test_safe_text(self):
        """Normal text passes all checks."""
        validator = PromptValidator()
        result = validator.validate("What is the weather today?")
        assert result.safe is True
        assert result.entropy_result is not None

    def test_llm_scan_found(self):
        """LLM detector finding a threat blocks the input."""
        mock_llm_result = MagicMock()
        mock_llm_result.found = True
        mock_llm_result.threat_level.name = "HIGH"

        mock_detector = MagicMock()
        mock_detector.scan.return_value = mock_llm_result

        validator = PromptValidator()
        validator.llm_detector = mock_detector

        result = validator.validate("What is the weather?")
        assert result.safe is False
        assert result.blocked_by == "llm_detection"
        assert result.threat_level == "HIGH"

    def test_llm_scan_connection_error(self):
        """LLM detector connection failure is handled gracefully."""
        mock_detector = MagicMock()
        mock_detector.scan.side_effect = ConnectionError("timeout")

        validator = PromptValidator()
        validator.llm_detector = mock_detector

        result = validator.validate("What is the weather?")
        assert result.safe is True

    def test_llm_scan_timeout_error(self):
        """LLM detector timeout failure is handled gracefully."""
        mock_detector = MagicMock()
        mock_detector.scan.side_effect = TimeoutError("timeout")

        validator = PromptValidator()
        validator.llm_detector = mock_detector

        result = validator.validate("What is the weather?")
        assert result.safe is True
