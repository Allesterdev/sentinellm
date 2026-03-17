"""
Configuration loader for SentineLLM security settings
"""

import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class OllamaLocalConfig:
    """Local Ollama deployment configuration"""

    host: str = "http://localhost"
    port: int = 11434
    timeout: float = 3.0

    @property
    def endpoint(self) -> str:
        """Get full endpoint URL"""
        host = self.host
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"
        return f"{host}:{self.port}"


@dataclass
class OllamaVPCConfig:
    """VPC Ollama deployment configuration"""

    endpoint: str = "http://ollama-lb.internal.company.vpc:11434"
    instances: list[str] = field(default_factory=list)
    load_balancing: str = "round-robin"
    timeout: float = 5.0


@dataclass
class OllamaExternalConfig:
    """External Ollama deployment configuration"""

    endpoint: str = "https://api.ollama.external.com"
    api_key_env: str = "OLLAMA_API_KEY"
    timeout: float = 10.0

    @property
    def api_key(self) -> str | None:
        """Get API key from environment"""
        return os.getenv(self.api_key_env)


def _detect_ollama_model() -> str | None:
    """Auto-detect the first available Ollama model.

    Calls ``ollama list`` and returns the first model name,
    or *None* if Ollama is not installed / not running.
    """
    try:
        result = subprocess.run(
            ["ollama", "list"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")[1:]  # skip header
            for line in lines:
                parts = line.split()
                if parts:
                    return parts[0]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # Ollama is not installed or not reachable — return None to caller.
        pass
    return None


def _resolve_ollama_model(configured: str) -> str:
    """Resolve the Ollama model name.

    Priority:
      1. ``SENTINELLM_OLLAMA_MODEL`` env var
      2. Configured value (from YAML) — unless it is ``"auto"``
      3. Auto-detect from ``ollama list``
      4. Fallback to ``"llama3.2:3b"``
    """
    # 1. Env var always wins
    env_model = os.environ.get("SENTINELLM_OLLAMA_MODEL")
    if env_model:
        logger.info("Ollama model from env: %s", env_model)
        return env_model

    # 2. Explicit config (not "auto")
    if configured and configured != "auto":
        return configured

    # 3. Auto-detect
    detected = _detect_ollama_model()
    if detected:
        logger.info("Ollama model auto-detected: %s", detected)
        return detected

    # 4. Safe fallback
    return "llama3.2:3b"


@dataclass
class OllamaModelConfig:
    """Ollama model configuration"""

    name: str = "auto"
    prompt_template: str = ""


@dataclass
class OllamaHealthCheckConfig:
    """Health check configuration"""

    enabled: bool = True
    interval: int = 60
    timeout: float = 2.0
    retries: int = 3


@dataclass
class OllamaCircuitBreakerConfig:
    """Circuit breaker configuration"""

    enabled: bool = True
    failure_threshold: int = 3
    recovery_timeout: int = 60
    half_open_max_calls: int = 5


@dataclass
class OllamaFallbackConfig:
    """Fallback configuration"""

    mode: str = "regex_only"  # regex_only, block_all, allow_all
    log_failures: bool = True
    alert_on_failure: bool = True


@dataclass
class OllamaConfig:
    """Complete Ollama configuration"""

    mode: str = "local"  # local, vpc, external
    local: OllamaLocalConfig = field(default_factory=OllamaLocalConfig)
    vpc: OllamaVPCConfig = field(default_factory=OllamaVPCConfig)
    external: OllamaExternalConfig = field(default_factory=OllamaExternalConfig)
    model: OllamaModelConfig = field(default_factory=OllamaModelConfig)
    health_check: OllamaHealthCheckConfig = field(default_factory=OllamaHealthCheckConfig)
    circuit_breaker: OllamaCircuitBreakerConfig = field(default_factory=OllamaCircuitBreakerConfig)
    fallback: OllamaFallbackConfig = field(default_factory=OllamaFallbackConfig)

    def get_endpoint(self) -> str:
        """Get endpoint based on deployment mode"""
        if self.mode == "local":
            return self.local.endpoint
        elif self.mode == "vpc":
            return self.vpc.endpoint
        elif self.mode == "external":
            return self.external.endpoint
        else:
            raise ValueError(f"Invalid Ollama mode: {self.mode}")

    def get_timeout(self) -> float:
        """Get timeout based on deployment mode"""
        if self.mode == "local":
            return self.local.timeout
        elif self.mode == "vpc":
            return self.vpc.timeout
        elif self.mode == "external":
            return self.external.timeout
        else:
            return 3.0


@dataclass
class PromptInjectionConfig:
    """Prompt injection detection configuration"""

    enabled: bool = True
    layers: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecretDetectionConfig:
    """Secret detection configuration"""

    enabled: bool = True
    entropy_threshold: float = 4.5
    patterns: list[str] = field(default_factory=list)
    validation: dict[str, bool] = field(default_factory=dict)


@dataclass
class SecurityConfig:
    """Complete security configuration"""

    prompt_injection: PromptInjectionConfig = field(default_factory=PromptInjectionConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    secret_detection: SecretDetectionConfig = field(default_factory=SecretDetectionConfig)

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> "SecurityConfig":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to YAML config file

        Returns:
            SecurityConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "SecurityConfig":
        """Create config from dictionary"""
        # Prompt injection config
        pi_data = data.get("prompt_injection", {})
        prompt_injection = PromptInjectionConfig(
            enabled=pi_data.get("enabled", True), layers=pi_data.get("layers", [])
        )

        # Ollama config
        ollama_data = data.get("ollama", {})

        # Handle model - can be either a string or a dict
        model_data = ollama_data.get("model", {})
        if isinstance(model_data, str):
            model_config = OllamaModelConfig(name=model_data)
        else:
            model_config = OllamaModelConfig(**model_data)

        # Resolve "auto" / env var to a real model name
        model_config.name = _resolve_ollama_model(model_config.name)

        ollama = OllamaConfig(
            mode=ollama_data.get("mode", "local"),
            local=OllamaLocalConfig(**ollama_data.get("local", {})),
            vpc=OllamaVPCConfig(**ollama_data.get("vpc", {})),
            external=OllamaExternalConfig(**ollama_data.get("external", {})),
            model=model_config,
            health_check=OllamaHealthCheckConfig(**ollama_data.get("health_check", {})),
            circuit_breaker=OllamaCircuitBreakerConfig(**ollama_data.get("circuit_breaker", {})),
            fallback=OllamaFallbackConfig(**ollama_data.get("fallback", {})),
        )

        # Secret detection config
        sd_data = data.get("secret_detection", {})
        secret_detection = SecretDetectionConfig(
            enabled=sd_data.get("enabled", True),
            entropy_threshold=sd_data.get("entropy_threshold", 4.5),
            patterns=sd_data.get("patterns", []),
            validation=sd_data.get("validation", {}),
        )

        return cls(
            prompt_injection=prompt_injection,
            ollama=ollama,
            secret_detection=secret_detection,
        )

    @classmethod
    def get_default_config_path(cls) -> Path:
        """Get default config file path"""
        # Try to find config in standard locations
        candidates = [
            Path("config/security_config.yaml"),
            Path("../config/security_config.yaml"),
            Path("/etc/sentinellm/security_config.yaml"),
            Path.home() / ".sentinellm" / "security_config.yaml",
        ]

        for path in candidates:
            if path.exists():
                return path

        # Return first candidate as default
        return candidates[0]

    @classmethod
    def load_default(cls) -> "SecurityConfig":
        """
        Load configuration from default location.

        Returns:
            SecurityConfig instance

        Raises:
            FileNotFoundError: If no config file found
        """
        config_path = cls.get_default_config_path()
        return cls.from_yaml(config_path)


# Singleton instance
_config_instance: SecurityConfig | None = None


def get_config() -> SecurityConfig:
    """
    Get singleton configuration instance.

    Loads config on first call, returns cached instance on subsequent calls.

    Returns:
        SecurityConfig instance
    """
    global _config_instance

    if _config_instance is None:
        try:
            _config_instance = SecurityConfig.load_default()
        except FileNotFoundError:
            # Use default configuration if no file found
            _config_instance = SecurityConfig()

    return _config_instance


def reload_config() -> SecurityConfig:
    """
    Reload configuration from file.

    Returns:
        New SecurityConfig instance
    """
    global _config_instance
    _config_instance = None
    return get_config()


def set_config(config: SecurityConfig) -> None:
    """
    Set configuration instance (useful for testing).

    Args:
        config: SecurityConfig instance to use
    """
    global _config_instance
    _config_instance = config
