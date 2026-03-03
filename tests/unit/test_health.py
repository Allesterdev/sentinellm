"""Unit tests for health endpoint with Ollama enabled paths."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.api.app import create_app


def _make_client():
    app = create_app()
    return TestClient(app)


class TestHealthOllamaEnabled:
    """Test health endpoint when Ollama is configured as enabled."""

    def test_ollama_healthy(self):
        """Health check returns healthy when Ollama is reachable."""
        mock_config = MagicMock()
        mock_config.prompt_injection.layers = {"llm": {"enabled": True}}

        mock_detector = MagicMock()
        mock_detector.health_check.return_value = True

        with (
            patch("src.api.routes.health.get_config", return_value=mock_config),
            patch(
                "src.filters.llm_detector.OllamaDetector",
                return_value=mock_detector,
            ),
        ):
            client = _make_client()
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ollama_available"] is True
            assert data["ollama_status"] == "connected"

    def test_ollama_unavailable(self):
        """Health check returns unavailable when Ollama is not reachable."""
        mock_config = MagicMock()
        mock_config.prompt_injection.layers = {"llm": {"enabled": True}}

        mock_detector = MagicMock()
        mock_detector.health_check.return_value = False

        with (
            patch("src.api.routes.health.get_config", return_value=mock_config),
            patch(
                "src.filters.llm_detector.OllamaDetector",
                return_value=mock_detector,
            ),
        ):
            client = _make_client()
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ollama_status"] == "unavailable"

    def test_ollama_connection_error(self):
        """Health check handles Ollama connection error."""
        mock_config = MagicMock()
        mock_config.prompt_injection.layers = {"llm": {"enabled": True}}

        with (
            patch("src.api.routes.health.get_config", return_value=mock_config),
            patch(
                "src.filters.llm_detector.OllamaDetector",
                side_effect=ConnectionError("refused"),
            ),
        ):
            client = _make_client()
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ollama_available"] is False
            assert data["ollama_status"] == "unavailable"

    def test_config_error(self):
        """Health check handles config ValueError."""
        with patch(
            "src.api.routes.health.get_config",
            side_effect=ValueError("bad config"),
        ):
            client = _make_client()
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ollama_status"] == "config_error"

    def test_ollama_disabled(self):
        """Health check returns disabled status when Ollama is not configured."""
        mock_config = MagicMock()
        mock_config.prompt_injection.layers = {"llm": {"enabled": False}}

        with patch("src.api.routes.health.get_config", return_value=mock_config):
            client = _make_client()
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ollama_available"] is False
            assert data["ollama_status"] == "disabled"

    def test_ollama_no_layers(self):
        """Health check returns disabled when no layers configured."""
        mock_config = MagicMock()
        mock_config.prompt_injection.layers = None

        with patch("src.api.routes.health.get_config", return_value=mock_config):
            client = _make_client()
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ollama_status"] == "disabled"
