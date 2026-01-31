"""CLI tools for SentineLLM configuration and management."""

from .config_wizard import run_config_wizard
from .setup import check_ollama_installation, run_setup

__all__ = ["run_config_wizard", "run_setup", "check_ollama_installation"]
