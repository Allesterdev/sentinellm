"""Unit tests for the setup module."""

import subprocess
import sys
from unittest.mock import MagicMock, patch

from src.cli.setup import check_ollama_installation, install_ollama_guide

# ── Tests for check_ollama_installation ─────────────────────────────────


class TestCheckOllamaInstallation:
    """Tests for check_ollama_installation."""

    def test_ollama_not_installed(self):
        """When Ollama is not installed."""
        with patch("shutil.which", return_value=None):
            result = check_ollama_installation()
            assert result["installed"] is False
            assert result["running"] is False
            assert result["models"] == []

    def test_ollama_installed_but_not_running(self):
        """When Ollama is installed but not running."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with (
            patch("shutil.which", return_value="/usr/bin/ollama"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = check_ollama_installation()
            assert result["installed"] is True
            assert result["running"] is False
            assert result["models"] == []

    def test_ollama_running_with_models(self):
        """When Ollama is running with models."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "NAME\tSIZE\tmistral:7b\t4.1 GB\nllama2:13b\t7.3 GB\n"

        with (
            patch("shutil.which", return_value="/usr/bin/ollama"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = check_ollama_installation()
            assert result["installed"] is True
            assert result["running"] is True
            assert len(result["models"]) >= 1

    def test_ollama_running_no_models(self):
        """When Ollama is running but no models installed."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "NAME\tSIZE\n"

        with (
            patch("shutil.which", return_value="/usr/bin/ollama"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = check_ollama_installation()
            assert result["installed"] is True
            assert result["running"] is True
            assert result["models"] == []

    def test_ollama_timeout(self):
        """When Ollama command times out."""
        with (
            patch("shutil.which", return_value="/usr/bin/ollama"),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ollama", 3)),
        ):
            result = check_ollama_installation()
            assert result["installed"] is True
            assert result["running"] is False

    def test_ollama_file_not_found(self):
        """When Ollama binary not found during run."""
        with (
            patch("shutil.which", return_value="/usr/bin/ollama"),
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            result = check_ollama_installation()
            assert result["installed"] is True
            assert result["running"] is False


# ── Tests for install_ollama_guide ──────────────────────────────────────


class TestInstallOllamaGuide:
    """Tests for install_ollama_guide."""

    def test_linux_guide(self, capsys):
        """Print Linux installation guide."""
        with patch.object(sys, "platform", "linux"):
            install_ollama_guide()
            captured = capsys.readouterr()
            assert "curl" in captured.out
            assert "ollama" in captured.out.lower()

    def test_darwin_guide(self, capsys):
        """Print macOS installation guide."""
        with patch.object(sys, "platform", "darwin"):
            install_ollama_guide()
            captured = capsys.readouterr()
            assert "curl" in captured.out or "download" in captured.out.lower()

    def test_windows_guide(self, capsys):
        """Print Windows installation guide."""
        with patch.object(sys, "platform", "win32"):
            install_ollama_guide()
            captured = capsys.readouterr()
            assert "download" in captured.out.lower() or "installer" in captured.out.lower()

    def test_shows_recommended_models(self, capsys):
        """Guide shows recommended models."""
        with patch.object(sys, "platform", "linux"):
            install_ollama_guide()
            captured = capsys.readouterr()
            assert "mistral" in captured.out.lower() or "llama" in captured.out.lower()


# ── Tests for run_setup ─────────────────────────────────────────────────


class TestRunSetup:
    """Tests for run_setup."""

    def test_no_questionary(self, capsys):
        """Prints error when questionary not available."""
        from src.cli.setup import run_setup

        with patch("src.cli.setup.questionary", None):
            run_setup()
            captured = capsys.readouterr()
            assert "❌" in captured.out
