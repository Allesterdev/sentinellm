"""Tests for config_wizard module."""

import subprocess
from unittest.mock import MagicMock, patch

from src.cli.config_wizard import (
    check_ollama_installed,
    check_ollama_running,
    get_ollama_models,
    print_ollama_info,
    print_welcome,
    run_config_wizard,
)


class TestCheckOllamaInstalled:
    """Tests for check_ollama_installed."""

    def test_ollama_installed(self):
        """Returns True when Ollama binary found."""
        with patch("shutil.which", return_value="/usr/bin/ollama"):
            assert check_ollama_installed() is True

    def test_ollama_not_installed(self):
        """Returns False when Ollama binary not found."""
        with patch("shutil.which", return_value=None):
            assert check_ollama_installed() is False


class TestCheckOllamaRunning:
    """Tests for check_ollama_running."""

    def test_ollama_running(self):
        """Returns True when Ollama is running."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            assert check_ollama_running() is True

    def test_ollama_not_running(self):
        """Returns False when Ollama is not running."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result):
            assert check_ollama_running() is False

    def test_ollama_timeout(self):
        """Returns False when Ollama times out."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ollama", 3)):
            assert check_ollama_running() is False

    def test_ollama_file_not_found(self):
        """Returns False when Ollama binary not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert check_ollama_running() is False


class TestGetOllamaModels:
    """Tests for get_ollama_models."""

    def test_models_available(self):
        """Returns list of models."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "NAME\tSIZE\nmistral:7b\t4.1 GB\nllama2:13b\t7.3 GB\n"
        with patch("subprocess.run", return_value=mock_result):
            result = get_ollama_models()
            assert len(result) == 2
            assert "mistral:7b" in result

    def test_no_models(self):
        """Returns empty list when no models."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "NAME\tSIZE\n"
        with patch("subprocess.run", return_value=mock_result):
            result = get_ollama_models()
            assert result == []

    def test_ollama_not_running(self):
        """Returns empty list when Ollama not running."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result):
            assert get_ollama_models() == []

    def test_ollama_timeout(self):
        """Returns empty list on timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ollama", 3)):
            assert get_ollama_models() == []

    def test_ollama_file_not_found(self):
        """Returns empty list when binary not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert get_ollama_models() == []


class TestPrintFunctions:
    """Tests for print helper functions."""

    def test_print_welcome(self, capsys):
        """print_welcome runs without error."""
        print_welcome()
        captured = capsys.readouterr()
        assert "SentineLLM" in captured.out or "=" in captured.out

    def test_print_ollama_info(self, capsys):
        """print_ollama_info runs without error."""
        print_ollama_info()
        captured = capsys.readouterr()
        assert "Ollama" in captured.out or "ollama" in captured.out


class TestRunConfigWizard:
    """Tests for run_config_wizard."""

    def test_no_questionary(self, capsys):
        """Prints error when questionary not available."""
        with patch("src.cli.config_wizard.questionary", None):
            result = run_config_wizard()
            assert result == {}
            captured = capsys.readouterr()
            assert "❌" in captured.out
