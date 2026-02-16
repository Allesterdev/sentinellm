"""Tests for config_loader module."""

import os
from unittest.mock import patch

from src.utils.config_loader import (
    _detect_ollama_model,
    _resolve_ollama_model,
    get_config,
    reload_config,
    set_config,
)


class TestConfigLoader:
    """Test configuration loader functionality."""

    def test_get_default_config(self):
        """Test getting default configuration."""
        config = get_config()

        assert config is not None
        assert hasattr(config, "prompt_injection")
        assert hasattr(config, "secret_detection")

    def test_security_config_structure(self):
        """Test SecurityConfig dataclass structure."""
        config = get_config()

        assert hasattr(config, "prompt_injection")
        assert hasattr(config, "secret_detection")
        assert hasattr(config, "ollama")

    def test_prompt_injection_config(self):
        """Test prompt injection configuration exists."""
        config = get_config()
        assert hasattr(config.prompt_injection, "enabled")
        assert hasattr(config.prompt_injection, "layers")

    def test_secret_detection_config(self):
        """Test secret detection configuration exists."""
        config = get_config()
        assert hasattr(config.secret_detection, "enabled")
        assert hasattr(config.secret_detection, "patterns")

    def test_ollama_config(self):
        """Test Ollama configuration exists."""
        config = get_config()
        assert hasattr(config.ollama, "mode")
        assert hasattr(config.ollama, "local")

    def test_reload_config(self):
        """Test reloading configuration."""
        config1 = get_config()
        config2 = reload_config()

        assert config1 is not None
        assert config2 is not None

    def test_set_config(self):
        """Test setting custom config."""
        custom_config = get_config()
        set_config(custom_config)

        config = get_config()
        assert config == custom_config

    def test_config_singleton_pattern(self):
        """Test that get_config returns same instance."""
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_ollama_local_config(self):
        """Test Ollama local configuration."""
        config = get_config()
        assert hasattr(config.ollama.local, "host")
        assert hasattr(config.ollama.local, "port")
        assert hasattr(config.ollama.local, "timeout")

    def test_ollama_local_endpoint_has_scheme(self):
        """Endpoint always includes http:// even if host has no scheme."""
        from src.utils.config_loader import OllamaLocalConfig

        # Without scheme (as typically written in YAML)
        local = OllamaLocalConfig(host="localhost", port=11434)
        assert local.endpoint == "http://localhost:11434"

        # With scheme already present
        local2 = OllamaLocalConfig(host="http://localhost", port=11434)
        assert local2.endpoint == "http://localhost:11434"

        # Custom host without scheme
        local3 = OllamaLocalConfig(host="192.168.1.100", port=11434)
        assert local3.endpoint == "http://192.168.1.100:11434"

    def test_ollama_vpc_config(self):
        """Test Ollama VPC configuration."""
        config = get_config()
        assert hasattr(config.ollama.vpc, "endpoint")
        assert hasattr(config.ollama.vpc, "load_balancing")

    def test_ollama_external_config(self):
        """Test Ollama external configuration."""
        config = get_config()
        assert hasattr(config.ollama.external, "endpoint")
        assert hasattr(config.ollama.external, "timeout")

    def test_ollama_model_config(self):
        """Test Ollama model configuration."""
        config = get_config()
        assert hasattr(config.ollama.model, "name")

    def test_ollama_circuit_breaker_config(self):
        """Test Ollama circuit breaker configuration."""
        config = get_config()
        assert hasattr(config.ollama.circuit_breaker, "failure_threshold")
        assert hasattr(config.ollama.circuit_breaker, "recovery_timeout")

    def test_config_layers_structure(self):
        """Test configuration layers structure."""
        config = get_config()
        assert isinstance(config.prompt_injection.layers, dict)


# ── Tests for Ollama model auto-detection ───────────────────────────────


class TestOllamaModelDetection:
    """Tests for _detect_ollama_model and _resolve_ollama_model."""

    def test_detect_ollama_model_with_models(self):
        """Detects first model from ollama list output."""
        fake_output = "NAME            ID           SIZE    MODIFIED\nllama3.2:3b     abc123       2.0 GB  2 days ago\nmistral:7b      def456       4.1 GB  5 days ago\n"
        with patch("src.utils.config_loader.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = fake_output
            result = _detect_ollama_model()
            assert result == "llama3.2:3b"

    def test_detect_ollama_model_no_models(self):
        """Returns None when no models installed."""
        fake_output = "NAME            ID           SIZE    MODIFIED\n"
        with patch("src.utils.config_loader.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = fake_output
            result = _detect_ollama_model()
            assert result is None

    def test_detect_ollama_not_installed(self):
        """Returns None when ollama is not installed."""
        with patch("src.utils.config_loader.subprocess.run", side_effect=FileNotFoundError):
            result = _detect_ollama_model()
            assert result is None

    def test_detect_ollama_timeout(self):
        """Returns None on timeout."""
        import subprocess

        with patch(
            "src.utils.config_loader.subprocess.run",
            side_effect=subprocess.TimeoutExpired("ollama", 3),
        ):
            result = _detect_ollama_model()
            assert result is None

    def test_resolve_env_var_wins(self):
        """SENTINELLM_OLLAMA_MODEL env var takes highest priority."""
        with patch.dict(os.environ, {"SENTINELLM_OLLAMA_MODEL": "phi3:mini"}):
            result = _resolve_ollama_model("mistral:7b")
            assert result == "phi3:mini"

    def test_resolve_explicit_config(self):
        """Explicit config value (not 'auto') is used."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove env var if present
            os.environ.pop("SENTINELLM_OLLAMA_MODEL", None)
            result = _resolve_ollama_model("mistral:7b")
            assert result == "mistral:7b"

    def test_resolve_auto_detects(self):
        """'auto' triggers detection."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SENTINELLM_OLLAMA_MODEL", None)
            with patch(
                "src.utils.config_loader._detect_ollama_model",
                return_value="llama3.2:3b",
            ):
                result = _resolve_ollama_model("auto")
                assert result == "llama3.2:3b"

    def test_resolve_auto_fallback(self):
        """'auto' falls back to llama3.2:3b when detection fails."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SENTINELLM_OLLAMA_MODEL", None)
            with patch(
                "src.utils.config_loader._detect_ollama_model",
                return_value=None,
            ):
                result = _resolve_ollama_model("auto")
                assert result == "llama3.2:3b"
