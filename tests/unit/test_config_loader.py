"""Tests for config_loader module."""

from src.utils.config_loader import (
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
