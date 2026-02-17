"""Unit tests for the agent_config module."""

import json
import os
from unittest.mock import patch

from src.cli.agent_config import (
    KNOWN_AGENTS,
    OPENCLAW_API_MAP,
    PROVIDER_PRESETS,
    _detect_existing_providers,
    _find_agent_config,
    _get_proxy_url,
    _patch_openclaw_config,
    _print_agent_summary,
    _print_manual_instructions,
    _print_multi_provider_summary,
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
        """Patching an empty config creates the models.providers structure."""
        config = {}
        result = _patch_openclaw_config(
            config, "openai", "https://api.openai.com", "http://127.0.0.1:8080"
        )
        assert result["models"]["providers"]["openai"]["baseUrl"] == "http://127.0.0.1:8080"
        assert result["models"]["providers"]["openai"]["api"] == "openai-responses"

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

    def test_patch_overwrites_base_url(self):
        """Patching overwrites existing baseUrl with proxy URL."""
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
        assert result["models"]["providers"]["openai"]["baseUrl"] == "http://127.0.0.1:8080"

    def test_patch_already_proxied(self):
        """Patching already-proxied config updates baseUrl idempotently."""
        config = {
            "models": {
                "providers": {
                    "openai": {
                        "baseUrl": "http://127.0.0.1:8080",
                        "api": "openai-responses",
                    },
                }
            }
        }
        result = _patch_openclaw_config(
            config, "openai", "https://api.openai.com", "http://127.0.0.1:8080"
        )
        assert result["models"]["providers"]["openai"]["baseUrl"] == "http://127.0.0.1:8080"

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

    def test_patch_sets_api_type_for_known_providers(self):
        """Patching sets the correct OpenClaw API type for known providers."""
        for provider_name, expected_api in OPENCLAW_API_MAP.items():
            config = {}
            result = _patch_openclaw_config(
                config, provider_name, "https://example.com", "http://127.0.0.1:8080"
            )
            assert result["models"]["providers"][provider_name]["api"] == expected_api

    def test_patch_preserves_existing_api(self):
        """Patching does not overwrite an existing api field."""
        config = {
            "models": {
                "providers": {
                    # user explicitly set this
                    "openai": {"api": "openai-chat"},
                }
            }
        }
        result = _patch_openclaw_config(
            config, "openai", "https://api.openai.com", "http://127.0.0.1:8080"
        )
        # Should keep user's explicit choice, not overwrite with default
        assert result["models"]["providers"]["openai"]["api"] == "openai-chat"

    def test_patch_unknown_provider_no_api(self):
        """Patching with unknown provider does not set api field."""
        config = {}
        result = _patch_openclaw_config(
            config, "custom_llm", "https://custom.example.com", "http://127.0.0.1:8080"
        )
        assert "api" not in result["models"]["providers"]["custom_llm"]
        assert result["models"]["providers"]["custom_llm"]["baseUrl"] == "http://127.0.0.1:8080"

    def test_patch_google_provider(self):
        """Patching with 'google' provider adds /v1beta path and sets API type."""
        config = {}
        result = _patch_openclaw_config(
            config,
            "google",
            "https://generativelanguage.googleapis.com",
            "http://127.0.0.1:8080",
        )
        provider = result["models"]["providers"]["google"]
        assert provider["baseUrl"] == "http://127.0.0.1:8080/v1beta"
        assert provider["api"] == "google-generative-ai"

    def test_patch_preserves_other_config(self):
        """Patching preserves unrelated config sections."""
        config = {
            "agents": {"defaults": {"model": {"primary": "google/gemini-2.5-flash"}}},
            "gateway": {"port": 18789},
        }
        result = _patch_openclaw_config(
            config,
            "google",
            "https://generativelanguage.googleapis.com",
            "http://127.0.0.1:8080",
        )
        assert result["agents"]["defaults"]["model"]["primary"] == "google/gemini-2.5-flash"
        assert result["gateway"]["port"] == 18789
        assert result["models"]["providers"]["google"]["baseUrl"] == "http://127.0.0.1:8080/v1beta"

    def test_patch_preserves_provider_models(self):
        """Patching preserves existing models array in provider."""
        config = {
            "models": {
                "providers": {
                    "google": {
                        "baseUrl": "https://generativelanguage.googleapis.com",
                        "api": "google-generative-ai",
                        "models": [
                            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
                        ],
                    }
                }
            }
        }
        result = _patch_openclaw_config(
            config,
            "google",
            "https://generativelanguage.googleapis.com",
            "http://127.0.0.1:8080",
        )
        provider = result["models"]["providers"]["google"]
        assert provider["baseUrl"] == "http://127.0.0.1:8080/v1beta"
        assert provider["api"] == "google-generative-ai"
        assert len(provider["models"]) == 1
        assert provider["models"][0]["id"] == "gemini-2.5-flash"

    def test_patch_v1beta_path_for_google_gemini_only(self):
        """Only google/gemini providers get /v1beta path, others don't."""
        # Google should get /v1beta
        config1 = {}
        result1 = _patch_openclaw_config(
            config1, "google", "https://generativelanguage.googleapis.com", "http://localhost:8080"
        )
        assert result1["models"]["providers"]["google"]["baseUrl"] == "http://localhost:8080/v1beta"

        # Gemini should get /v1beta
        config2 = {}
        result2 = _patch_openclaw_config(
            config2, "gemini", "https://generativelanguage.googleapis.com", "http://localhost:8080"
        )
        assert result2["models"]["providers"]["gemini"]["baseUrl"] == "http://localhost:8080/v1beta"

        # OpenAI should NOT get /v1beta
        config3 = {}
        result3 = _patch_openclaw_config(
            config3, "openai", "https://api.openai.com", "http://localhost:8080"
        )
        assert result3["models"]["providers"]["openai"]["baseUrl"] == "http://localhost:8080"

        # Anthropic should NOT get /v1beta
        config4 = {}
        result4 = _patch_openclaw_config(
            config4, "anthropic", "https://api.anthropic.com", "http://localhost:8080"
        )
        assert result4["models"]["providers"]["anthropic"]["baseUrl"] == "http://localhost:8080"


# ── Tests for print functions ───────────────────────────────────────────


class TestPrintFunctions:
    """Tests for print helper functions."""

    def test_print_manual_instructions(self, capsys):
        """Print manual instructions without error."""
        preset = {"name": "OpenAI", "base_url": "https://api.openai.com", "header": "Authorization"}
        _print_manual_instructions("https://api.openai.com", "http://localhost:8080", preset)
        captured = capsys.readouterr()
        assert "http://localhost:8080" in captured.out
        assert "SENTINELLM_TARGET_URL" in captured.out

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
        """Skips unknown provider but still succeeds."""
        config_file = tmp_path / "config.json5"
        config_file.write_text("{}")
        with patch("src.cli.agent_config._find_agent_config", return_value=config_file):
            # Single unknown provider — nothing gets configured but call succeeds
            result = quick_configure_openclaw("nonexistent_provider")
            assert result is True

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
            assert patched["models"]["providers"]["openai"]["api"] == "openai-responses"

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
            assert patched["models"]["providers"]["anthropic"]["baseUrl"] == "http://127.0.0.1:8080"
            assert patched["models"]["providers"]["anthropic"]["api"] == "anthropic"

    def test_multi_provider_list(self, tmp_path):
        """Configure multiple providers at once."""
        config_file = tmp_path / "config.json5"
        config_file.write_text("{}")

        with patch("src.cli.agent_config._find_agent_config", return_value=config_file):
            result = quick_configure_openclaw(["openai", "anthropic", "gemini"])
            assert result is True

            patched = json.loads(config_file.read_text())
            providers = patched["models"]["providers"]
            assert providers["openai"]["baseUrl"] == "http://127.0.0.1:8080"
            assert providers["openai"]["api"] == "openai-responses"
            assert providers["anthropic"]["baseUrl"] == "http://127.0.0.1:8080"
            assert providers["anthropic"]["api"] == "anthropic"
            assert providers["gemini"]["baseUrl"] == "http://127.0.0.1:8080/v1beta"
            assert providers["gemini"]["api"] == "google-generative-ai"

    def test_multi_provider_skips_unknown(self, tmp_path, capsys):
        """Multi-provider skips unknown providers with warning."""
        config_file = tmp_path / "config.json5"
        config_file.write_text("{}")

        with patch("src.cli.agent_config._find_agent_config", return_value=config_file):
            result = quick_configure_openclaw(["openai", "unknown_llm"])
            assert result is True

            patched = json.loads(config_file.read_text())
            assert "openai" in patched["models"]["providers"]
            assert "unknown_llm" not in patched["models"]["providers"]

            captured = capsys.readouterr()
            assert "unknown_llm" in captured.out


# ── Tests for _detect_existing_providers ────────────────────────────────


class TestDetectExistingProviders:
    """Tests for _detect_existing_providers."""

    def test_empty_config(self):
        """Empty config returns empty set."""
        assert _detect_existing_providers({}) == set()

    def test_no_models(self):
        """Config without models returns empty set."""
        assert _detect_existing_providers({"agents": {}}) == set()

    def test_no_providers(self):
        """Config with models but no providers returns empty set."""
        assert _detect_existing_providers({"models": {}}) == set()

    def test_existing_providers(self):
        """Detects existing providers."""
        config = {
            "models": {
                "providers": {
                    "google": {"baseUrl": "https://generativelanguage.googleapis.com"},
                    "openai": {"baseUrl": "https://api.openai.com"},
                }
            }
        }
        result = _detect_existing_providers(config)
        assert result == {"google", "openai"}

    def test_invalid_structure(self):
        """Handles invalid structure gracefully."""
        assert _detect_existing_providers({"models": {"providers": None}}) == set()


# ── Tests for _print_multi_provider_summary ─────────────────────────────


class TestPrintMultiProviderSummary:
    """Tests for _print_multi_provider_summary."""

    def test_prints_all_providers(self, capsys):
        """Summary lists all configured providers."""
        _print_multi_provider_summary(
            agent_name="OpenClaw",
            providers=["openai", "anthropic"],
            proxy_url="http://127.0.0.1:8080",
        )
        captured = capsys.readouterr()
        assert "OpenClaw" in captured.out
        assert "OpenAI" in captured.out
        assert "Anthropic" in captured.out
        assert "http://127.0.0.1:8080" in captured.out
        assert "SENTINELLM_TARGET_URL" in captured.out


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
