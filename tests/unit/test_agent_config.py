"""Unit tests for the agent_config module."""

import json
import os
from unittest.mock import patch

from src.cli.agent_config import (
    KNOWN_AGENTS,
    PROVIDER_PRESETS,
    _find_agent_config,
    _get_proxy_url,
    _patch_openclaw_config,
    _print_agent_summary,
    _print_manual_instructions,
    _read_json5_file,
    _write_json_file,
    quick_configure_openclaw,
)

# ── Tests for constants ─────────────────────────────────────────────────


class TestConstants:
    """Tests for agent and provider constants."""

    def test_known_agents_structure(self):
        """KNOWN_AGENTS has expected keys and structure."""
        assert "openclaw" in KNOWN_AGENTS
        assert "cline" in KNOWN_AGENTS
        assert "aider" in KNOWN_AGENTS

        for _agent_id, agent in KNOWN_AGENTS.items():
            assert "name" in agent
            assert "description" in agent
            assert "config_paths" in agent
            assert "url_field" in agent
            assert isinstance(agent["config_paths"], list)
            assert len(agent["config_paths"]) > 0

    def test_provider_presets_structure(self):
        """PROVIDER_PRESETS has expected keys."""
        assert "openai" in PROVIDER_PRESETS
        assert "anthropic" in PROVIDER_PRESETS
        assert "gemini" in PROVIDER_PRESETS
        assert "ollama" in PROVIDER_PRESETS
        assert "openrouter" in PROVIDER_PRESETS
        assert "azure" in PROVIDER_PRESETS
        assert "custom" in PROVIDER_PRESETS

        for _pid, preset in PROVIDER_PRESETS.items():
            assert "name" in preset
            assert "base_url" in preset

    def test_openclaw_agent_details(self):
        """OpenClaw agent has correct configuration."""
        agent = KNOWN_AGENTS["openclaw"]
        assert agent["name"] == "OpenClaw"
        assert agent["url_field"] == "baseUrl"
        assert agent["providers_path"] == ["models", "providers"]
        assert any("config.json5" in p for p in agent["config_paths"])


# ── Tests for _find_agent_config ────────────────────────────────────────


class TestFindAgentConfig:
    """Tests for _find_agent_config."""

    def test_unknown_agent(self):
        """Unknown agent returns None."""
        assert _find_agent_config("nonexistent") is None

    def test_env_var_path(self, tmp_path):
        """Config found via environment variable."""
        config_file = tmp_path / "config.json5"
        config_file.write_text("{}")

        with patch.dict(os.environ, {"OPENCLAW_CONFIG_PATH": str(config_file)}):
            result = _find_agent_config("openclaw")
            assert result == config_file

    def test_env_var_nonexistent(self):
        """Env var pointing to nonexistent file falls through to path search."""
        with patch.dict(os.environ, {"OPENCLAW_CONFIG_PATH": "/nonexistent/config.json"}):
            # Will fall through to path search, which also won't find anything
            _find_agent_config("openclaw")
            # Either None or found in default paths
            # Just check it doesn't crash

    def test_known_path(self, tmp_path):
        """Config found in known path."""
        # Mock the paths to use tmp_path
        config_file = tmp_path / "config.json5"
        config_file.write_text("{}")

        with patch.dict(
            KNOWN_AGENTS,
            {
                "test_agent": {
                    "name": "Test",
                    "description": "Test agent",
                    "config_paths": [str(config_file)],
                    "env_var": None,
                    "url_field": "baseUrl",
                    "providers_path": [],
                }
            },
        ):
            result = _find_agent_config("test_agent")
            assert result == config_file

    def test_no_config_found(self):
        """Returns None when no config found."""
        with patch.dict(
            KNOWN_AGENTS,
            {
                "test_agent": {
                    "name": "Test",
                    "description": "Test",
                    "config_paths": ["/nonexistent/path"],
                    "env_var": None,
                    "url_field": "baseUrl",
                    "providers_path": [],
                }
            },
        ):
            assert _find_agent_config("test_agent") is None


# ── Tests for _read_json5_file ──────────────────────────────────────────


class TestReadJson5File:
    """Tests for _read_json5_file."""

    def test_read_valid_json(self, tmp_path):
        """Read a valid JSON file."""
        f = tmp_path / "config.json"
        f.write_text('{"key": "value"}')
        result = _read_json5_file(f)
        assert result == {"key": "value"}

    def test_strip_single_line_comments(self, tmp_path):
        """Strip // comments from JSON5."""
        f = tmp_path / "config.json5"
        f.write_text('{\n  "key": "value" // this is a comment\n}')
        result = _read_json5_file(f)
        assert result == {"key": "value"}

    def test_strip_multi_line_comments(self, tmp_path):
        """Strip /* */ comments from JSON5."""
        f = tmp_path / "config.json5"
        f.write_text('{\n  /* comment */\n  "key": "value"\n}')
        result = _read_json5_file(f)
        assert result == {"key": "value"}

    def test_strip_trailing_commas(self, tmp_path):
        """Strip trailing commas before } or ]."""
        f = tmp_path / "config.json5"
        f.write_text('{\n  "a": 1,\n  "b": [1, 2,],\n}')
        result = _read_json5_file(f)
        assert result == {"a": 1, "b": [1, 2]}

    def test_invalid_json(self, tmp_path):
        """Invalid JSON returns empty dict."""
        f = tmp_path / "config.json"
        f.write_text("not valid json at all {{{")
        result = _read_json5_file(f)
        assert result == {}

    def test_complex_json5(self, tmp_path):
        """Complex JSON5 with comments and trailing commas."""
        f = tmp_path / "config.json5"
        f.write_text("""{
  // OpenClaw configuration
  "models": {
    "providers": {
      "openai": {
        "name": "gpt-4",  // primary model
      },
    },
  },
}""")
        result = _read_json5_file(f)
        assert result["models"]["providers"]["openai"]["name"] == "gpt-4"


# ── Tests for _write_json_file ──────────────────────────────────────────


class TestWriteJsonFile:
    """Tests for _write_json_file."""

    def test_write_and_read_back(self, tmp_path):
        """Write JSON and read it back."""
        f = tmp_path / "output.json"
        data = {"key": "value", "nested": {"a": 1}}
        _write_json_file(f, data)

        content = f.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed == data

    def test_file_ends_with_newline(self, tmp_path):
        """Written file ends with newline."""
        f = tmp_path / "output.json"
        _write_json_file(f, {"key": "value"})
        assert f.read_text().endswith("\n")

    def test_unicode_preserved(self, tmp_path):
        """Unicode characters are preserved."""
        f = tmp_path / "output.json"
        _write_json_file(f, {"name": "José"})
        content = f.read_text(encoding="utf-8")
        assert "José" in content


# ── Tests for _get_proxy_url ────────────────────────────────────────────


class TestGetProxyUrl:
    """Tests for _get_proxy_url."""

    def test_default(self):
        """Default proxy URL."""
        assert _get_proxy_url() == "http://127.0.0.1:8080"

    def test_custom_host_port(self):
        """Custom host and port."""
        assert _get_proxy_url("0.0.0.0", 9090) == "http://0.0.0.0:9090"  # noqa: S104


# ── Tests for _patch_openclaw_config ────────────────────────────────────


class TestPatchOpenclawConfig:
    """Tests for _patch_openclaw_config."""

    def test_patch_empty_config(self):
        """Patching an empty config creates the structure."""
        config = {}
        result = _patch_openclaw_config(
            config, "openai", "https://api.openai.com", "http://127.0.0.1:8080"
        )
        assert result["models"]["providers"]["openai"]["baseUrl"] == "http://127.0.0.1:8080"
        assert (
            result["models"]["providers"]["openai"]["headers"]["X-Target-URL"]
            == "https://api.openai.com"
        )

    def test_patch_existing_config(self):
        """Patching existing config preserves other providers."""
        config = {
            "models": {
                "providers": {
                    "anthropic": {"baseUrl": "https://api.anthropic.com"},
                }
            }
        }
        result = _patch_openclaw_config(
            config, "openai", "https://api.openai.com", "http://127.0.0.1:8080"
        )
        assert result["models"]["providers"]["openai"]["baseUrl"] == "http://127.0.0.1:8080"
        assert result["models"]["providers"]["anthropic"]["baseUrl"] == "https://api.anthropic.com"

    def test_patch_saves_original_url(self):
        """Original baseUrl is saved as _original_baseUrl."""
        config = {
            "models": {
                "providers": {
                    "openai": {"baseUrl": "https://api.openai.com"},
                }
            }
        }
        result = _patch_openclaw_config(
            config, "openai", "https://api.openai.com", "http://127.0.0.1:8080"
        )
        assert (
            result["models"]["providers"]["openai"]["_original_baseUrl"] == "https://api.openai.com"
        )

    def test_patch_already_proxied(self):
        """Patching already-proxied config doesn't re-save _original_baseUrl."""
        config = {
            "models": {
                "providers": {
                    "openai": {
                        "baseUrl": "http://127.0.0.1:8080",
                        "_original_baseUrl": "https://api.openai.com",
                    },
                }
            }
        }
        result = _patch_openclaw_config(
            config, "openai", "https://api.openai.com", "http://127.0.0.1:8080"
        )
        # baseUrl equals proxy_url, so _original_baseUrl should NOT be overwritten
        assert result["models"]["providers"]["openai"]["baseUrl"] == "http://127.0.0.1:8080"

    def test_patch_adds_headers(self):
        """Patching adds headers dict if not present."""
        config = {"models": {"providers": {"openai": {"baseUrl": "https://api.openai.com"}}}}
        result = _patch_openclaw_config(
            config, "openai", "https://api.openai.com", "http://localhost:8080"
        )
        assert "headers" in result["models"]["providers"]["openai"]
        assert "X-Target-URL" in result["models"]["providers"]["openai"]["headers"]

    def test_patch_creates_models_key(self):
        """Patching creates 'models' key if missing."""
        config = {"some_other_key": "value"}
        result = _patch_openclaw_config(
            config, "openai", "https://api.openai.com", "http://localhost:8080"
        )
        assert "models" in result
        assert "providers" in result["models"]

    def test_patch_creates_providers_key(self):
        """Patching creates 'providers' key if missing."""
        config = {"models": {"settings": "value"}}
        result = _patch_openclaw_config(
            config, "openai", "https://api.openai.com", "http://localhost:8080"
        )
        assert "providers" in result["models"]


# ── Tests for print functions ───────────────────────────────────────────


class TestPrintFunctions:
    """Tests for print helper functions."""

    def test_print_manual_instructions(self, capsys):
        """Print manual instructions without error."""
        preset = {"name": "OpenAI", "base_url": "https://api.openai.com", "header": "Authorization"}
        _print_manual_instructions("https://api.openai.com", "http://localhost:8080", preset)
        captured = capsys.readouterr()
        assert "http://localhost:8080" in captured.out
        assert "https://api.openai.com" in captured.out

    def test_print_agent_summary(self, capsys):
        """Print agent summary without error."""
        _print_agent_summary(
            agent_name="OpenClaw",
            provider_name="openai",
            target_url="https://api.openai.com",
            proxy_url="http://localhost:8080",
        )
        captured = capsys.readouterr()
        assert "OpenClaw" in captured.out
        assert "openai" in captured.out
        assert "http://localhost:8080" in captured.out


# ── Tests for quick_configure_openclaw ──────────────────────────────────


class TestQuickConfigureOpenclaw:
    """Tests for quick_configure_openclaw."""

    def test_config_not_found(self):
        """Returns False when OpenClaw config not found."""
        with patch("src.cli.agent_config._find_agent_config", return_value=None):
            assert quick_configure_openclaw() is False

    def test_unknown_provider(self, tmp_path):
        """Returns False for unknown provider."""
        config_file = tmp_path / "config.json5"
        config_file.write_text("{}")
        with patch("src.cli.agent_config._find_agent_config", return_value=config_file):
            assert quick_configure_openclaw("nonexistent_provider") is False

    def test_successful_configuration(self, tmp_path):
        """Successfully patches OpenClaw config."""
        config_file = tmp_path / "config.json5"
        config_file.write_text(
            json.dumps({"models": {"providers": {"openai": {"baseUrl": "https://api.openai.com"}}}})
        )

        with patch("src.cli.agent_config._find_agent_config", return_value=config_file):
            result = quick_configure_openclaw("openai")
            assert result is True

            # Verify the config was patched
            patched = json.loads(config_file.read_text())
            assert patched["models"]["providers"]["openai"]["baseUrl"] == "http://127.0.0.1:8080"
            assert (
                patched["models"]["providers"]["openai"]["headers"]["X-Target-URL"]
                == "https://api.openai.com"
            )

    def test_backup_created(self, tmp_path):
        """Backup file is created."""
        config_file = tmp_path / "config.json5"
        config_file.write_text("{}")

        with patch("src.cli.agent_config._find_agent_config", return_value=config_file):
            quick_configure_openclaw("openai")
            backup = tmp_path / "config.json5.bak"
            assert backup.exists()

    def test_anthropic_provider(self, tmp_path):
        """Configure with Anthropic provider."""
        config_file = tmp_path / "config.json5"
        config_file.write_text("{}")

        with patch("src.cli.agent_config._find_agent_config", return_value=config_file):
            result = quick_configure_openclaw("anthropic")
            assert result is True

            patched = json.loads(config_file.read_text())
            assert (
                patched["models"]["providers"]["anthropic"]["headers"]["X-Target-URL"]
                == "https://api.anthropic.com"
            )


# ── Tests for _detect_installed_agents ──────────────────────────────────


class TestDetectInstalledAgents:
    """Tests for _detect_installed_agents."""

    def test_none_detected(self):
        """No agents found when no configs exist."""
        from src.cli.agent_config import _detect_installed_agents

        with patch("src.cli.agent_config._find_agent_config", return_value=None):
            result = _detect_installed_agents()
            assert result == {}

    def test_one_detected(self, tmp_path):
        """Detects one agent."""
        from src.cli.agent_config import _detect_installed_agents

        fake_path = tmp_path / "config.json"

        def mock_find(agent_id):
            return fake_path if agent_id == "openclaw" else None

        with patch("src.cli.agent_config._find_agent_config", side_effect=mock_find):
            result = _detect_installed_agents()
            assert "openclaw" in result
            assert result["openclaw"] == fake_path


# ── Tests for configure_agent_interactive ───────────────────────────────


class TestConfigureAgentInteractive:
    """Tests for configure_agent_interactive."""

    def test_no_questionary(self, capsys):
        """Prints error when questionary not available."""
        from src.cli.agent_config import configure_agent_interactive

        with patch("src.cli.agent_config.questionary", None):
            result = configure_agent_interactive()
            assert result is None
