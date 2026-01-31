"""Tests for config_wizard module."""

from unittest.mock import MagicMock, patch

from src.cli.config_wizard import (
    check_ollama_installed,
    check_ollama_running,
    get_ollama_models,
)


class TestConfigWizard:
    """Test configuration wizard functionality."""

    def test_check_ollama_installed(self):
        """Test check if Ollama is installed."""
        result = check_ollama_installed()
        assert isinstance(result, bool)

    @patch("src.cli.config_wizard.subprocess")
    def test_check_ollama_running(self, mock_subprocess):
        """Test check if Ollama is running."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.run.return_value = mock_result

        result = check_ollama_running()
        assert result is True

        mock_result.returncode = 1
        result = check_ollama_running()
        assert result is False

    @patch("src.cli.config_wizard.subprocess")
    def test_get_ollama_models(self, mock_subprocess):
        """Test getting Ollama models list."""
        mock_result = MagicMock()
        mock_result.stdout = "llama2\nllama3\n"
        mock_result.returncode = 0
        mock_subprocess.run.return_value = mock_result

        result = get_ollama_models()
        assert isinstance(result, list)
        assert len(result) >= 0
