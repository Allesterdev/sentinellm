"""Unit tests for the agent_config module."""

import json
import os
from unittest.mock import patch

from src.cli.agent_config import (
    KNOWN_AGENTS,
    PROVIDER_DEFAULT_MODELS,
    PROVIDER_PRESETS,
    _create_openclaw_default_config,
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


# ── Tests for _create_openclaw_default_config ───────────────────────────


class TestCreateOpenclawDefaultConfig:
    """Tests for _create_openclaw_default_config."""

    def test_creates_required_sections(self):
        """Default config has all required top-level sections."""
        config = _create_openclaw_default_config()
        assert "messages" in config
        assert "agents" in config
        assert "gateway" in config
        assert "wizard" in config
        assert "meta" in config

    def test_no_invalid_compaction_field(self):
        """Config must NOT contain invalid 'compaction' field."""
        config = _create_openclaw_default_config()
        # Verify 'compaction' is not in agents section
        assert "compaction" not in config.get("agents", {})

    def test_agents_structure(self):
        """Agents section has valid structure."""
        config = _create_openclaw_default_config()
        agents = config["agents"]
        assert "defaults" in agents
        assert "maxConcurrent" in agents["defaults"]
        assert "subagents" in agents["defaults"]
        assert isinstance(agents["defaults"]["maxConcurrent"], int)
        assert isinstance(agents["defaults"]["subagents"], dict)

    def test_gateway_structure(self):
        """Gateway section has valid structure."""
        config = _create_openclaw_default_config()
        gateway = config["gateway"]
        assert gateway["mode"] == "local"
        assert gateway["port"] == 18789
        assert gateway["bind"] == "loopback"
        assert "auth" in gateway
        assert gateway["auth"]["mode"] == "token"
        assert "token" in gateway["auth"]
        assert len(gateway["auth"]["token"]) == 64  # 32 bytes hex = 64 chars

    def test_wizard_populated(self):
        """Wizard section has timestamps and version."""
        config = _create_openclaw_default_config()
        wizard = config["wizard"]
        assert "lastRunAt" in wizard
        assert "lastRunVersion" in wizard
        assert wizard["lastRunVersion"] == "2026.2.6-3"

    def test_meta_populated(self):
        """Meta section has timestamps and version."""
        config = _create_openclaw_default_config()
        meta = config["meta"]
        assert "lastTouchedAt" in meta
        assert "lastTouchedVersion" in meta
        assert meta["lastTouchedVersion"] == "2026.2.6-3"


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
    """Tests for _patch_openclaw_config.

    New behavior: creates a *custom* sentinellm-{provider} provider so that
    OpenClaw actually routes traffic through the proxy (built-in providers
    ignore baseUrl overrides per OpenClaw docs).
    """

    PROXY = "http://127.0.0.1:8080"

    def test_patch_creates_custom_provider_name(self):
        """Patching creates 'sentinellm-openai', not 'openai'."""
        result = _patch_openclaw_config({}, "openai", "https://api.openai.com", self.PROXY)
        assert "sentinellm-openai" in result["models"]["providers"]
        assert "openai" not in result["models"]["providers"]

    def test_patch_sets_base_url_on_custom_provider(self):
        """Custom provider's baseUrl points to the SentineLLM proxy."""
        result = _patch_openclaw_config({}, "openai", "https://api.openai.com", self.PROXY)
        assert result["models"]["providers"]["sentinellm-openai"]["baseUrl"] == self.PROXY

    def test_patch_sets_models_mode_merge(self):
        """models.mode is always set to 'merge' to preserve other providers."""
        result = _patch_openclaw_config(
            {}, "gemini", "https://generativelanguage.googleapis.com", self.PROXY
        )
        assert result["models"]["mode"] == "merge"

    def test_patch_sets_api_type(self):
        """Custom provider gets the correct OpenClaw API type."""
        result = _patch_openclaw_config(
            {}, "gemini", "https://generativelanguage.googleapis.com", self.PROXY
        )
        provider = result["models"]["providers"]["sentinellm-gemini"]
        assert provider["api"] == "google-generative-ai"

    def test_patch_sets_api_key_env_ref(self):
        """Custom provider includes apiKey as env var reference."""
        result = _patch_openclaw_config({}, "openai", "https://api.openai.com", self.PROXY)
        provider = result["models"]["providers"]["sentinellm-openai"]
        assert provider["apiKey"] == "${OPENAI_API_KEY}"  # pragma: allowlist secret

    def test_patch_ollama_uses_dummy_key(self):
        """Ollama (no auth) gets a dummy apiKey value."""
        result = _patch_openclaw_config({}, "ollama", "http://localhost:11434", self.PROXY)
        provider = result["models"]["providers"]["sentinellm-ollama"]
        assert provider["apiKey"] == "ollama-local"

    def test_patch_includes_default_model_in_list(self):
        """Custom provider has at least one model in its models list."""
        result = _patch_openclaw_config(
            {}, "gemini", "https://generativelanguage.googleapis.com", self.PROXY
        )
        provider = result["models"]["providers"]["sentinellm-gemini"]
        assert isinstance(provider["models"], list)
        assert len(provider["models"]) >= 1
        assert provider["models"][0]["id"] == "gemini-2.0-flash"

    def test_patch_sets_primary_model(self):
        """agents.defaults.model.primary is set to the custom provider model ref."""
        result = _patch_openclaw_config(
            {}, "gemini", "https://generativelanguage.googleapis.com", self.PROXY
        )
        primary = result["agents"]["defaults"]["model"]["primary"]
        assert primary == "sentinellm-gemini/gemini-2.0-flash"

    def test_patch_adds_model_to_allowlist(self):
        """Model ref is added to agents.defaults.models allowlist with alias."""
        result = _patch_openclaw_config({}, "openai", "https://api.openai.com", self.PROXY)
        allowlist = result["agents"]["defaults"]["models"]
        assert "sentinellm-openai/gpt-4o" in allowlist
        assert "alias" in allowlist["sentinellm-openai/gpt-4o"]

    def test_patch_preserves_gateway_and_other_sections(self):
        """Patching preserves unrelated config sections."""
        config = {
            "gateway": {"port": 18789},
            "messages": {"ackReactionScope": "group-mentions"},
        }
        result = _patch_openclaw_config(
            config, "gemini", "https://generativelanguage.googleapis.com", self.PROXY
        )
        assert result["gateway"]["port"] == 18789
        assert result["messages"]["ackReactionScope"] == "group-mentions"

    def test_patch_preserves_existing_custom_models(self):
        """Re-patching preserves existing model entries in the provider's list."""
        config = {
            "models": {
                "providers": {
                    "sentinellm-gemini": {
                        "baseUrl": self.PROXY,
                        "api": "google-generative-ai",
                        "models": [
                            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
                        ],
                    }
                }
            }
        }
        result = _patch_openclaw_config(
            config, "gemini", "https://generativelanguage.googleapis.com", self.PROXY
        )
        models = result["models"]["providers"]["sentinellm-gemini"]["models"]
        model_ids = [m["id"] for m in models]
        # Both the existing custom model AND the default should be present
        assert "gemini-2.5-pro" in model_ids
        assert "gemini-2.0-flash" in model_ids

    def test_patch_idempotent_on_default_model(self):
        """Re-patching does not duplicate default model entry."""
        config = {}
        result1 = _patch_openclaw_config(
            config, "gemini", "https://generativelanguage.googleapis.com", self.PROXY
        )
        result2 = _patch_openclaw_config(
            result1, "gemini", "https://generativelanguage.googleapis.com", self.PROXY
        )
        models = result2["models"]["providers"]["sentinellm-gemini"]["models"]
        ids = [m["id"] for m in models]
        assert ids.count("gemini-2.0-flash") == 1  # no duplicate

    def test_patch_all_known_providers(self):
        """All providers in PROVIDER_DEFAULT_MODELS can be patched without error."""
        for provider_id, info in PROVIDER_DEFAULT_MODELS.items():
            config = {}
            result = _patch_openclaw_config(config, provider_id, "https://example.com", self.PROXY)
            custom = f"sentinellm-{provider_id}"
            assert custom in result["models"]["providers"]
            assert result["models"]["providers"][custom]["baseUrl"] == self.PROXY
            model_ref = f"{custom}/{info['id']}"
            assert result["agents"]["defaults"]["model"]["primary"] == model_ref

    def test_patch_unknown_provider_uses_default_api(self):
        """Unknown provider falls back to openai-completions api type."""
        result = _patch_openclaw_config({}, "my-llm", "https://custom.example.com", self.PROXY)
        provider = result["models"]["providers"]["sentinellm-my-llm"]
        assert provider["api"] == "openai-completions"
        assert provider["baseUrl"] == self.PROXY


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
        """Successfully patches OpenClaw config with custom provider name."""
        config_file = tmp_path / "config.json5"
        config_file.write_text(json.dumps({}))

        with patch("src.cli.agent_config._find_agent_config", return_value=config_file):
            result = quick_configure_openclaw("openai")
            assert result is True

            # Custom provider: sentinellm-openai, not the built-in 'openai'
            patched = json.loads(config_file.read_text())
            provider = patched["models"]["providers"]["sentinellm-openai"]
            assert provider["baseUrl"] == "http://127.0.0.1:8080"
            assert provider["api"] == "openai-responses"
            assert patched["agents"]["defaults"]["model"]["primary"] == "sentinellm-openai/gpt-4o"

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
            provider = patched["models"]["providers"]["sentinellm-anthropic"]
            assert provider["baseUrl"] == "http://127.0.0.1:8080"
            assert provider["api"] == "anthropic"
            assert (
                patched["agents"]["defaults"]["model"]["primary"]
                == "sentinellm-anthropic/claude-sonnet-4-5"
            )

    def test_multi_provider_list(self, tmp_path):
        """Configure multiple providers at once."""
        config_file = tmp_path / "config.json5"
        config_file.write_text("{}")

        with patch("src.cli.agent_config._find_agent_config", return_value=config_file):
            result = quick_configure_openclaw(["openai", "anthropic", "gemini"])
            assert result is True

            patched = json.loads(config_file.read_text())
            providers = patched["models"]["providers"]
            assert providers["sentinellm-openai"]["baseUrl"] == "http://127.0.0.1:8080"
            assert providers["sentinellm-openai"]["api"] == "openai-responses"
            assert providers["sentinellm-anthropic"]["baseUrl"] == "http://127.0.0.1:8080"
            assert providers["sentinellm-anthropic"]["api"] == "anthropic"
            assert providers["sentinellm-gemini"]["baseUrl"] == "http://127.0.0.1:8080"
            assert providers["sentinellm-gemini"]["api"] == "google-generative-ai"

    def test_multi_provider_skips_unknown(self, tmp_path, capsys):
        """Multi-provider skips unknown providers with warning."""
        config_file = tmp_path / "config.json5"
        config_file.write_text("{}")

        with patch("src.cli.agent_config._find_agent_config", return_value=config_file):
            result = quick_configure_openclaw(["openai", "unknown_llm"])
            assert result is True

            patched = json.loads(config_file.read_text())
            assert "sentinellm-openai" in patched["models"]["providers"]
            assert "sentinellm-unknown_llm" not in patched["models"]["providers"]
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
        """Detects sentinellm-prefixed providers and strips the prefix."""
        config = {
            "models": {
                "providers": {
                    "sentinellm-google": {"baseUrl": "http://127.0.0.1:8080"},
                    "sentinellm-openai": {"baseUrl": "http://127.0.0.1:8080"},
                }
            }
        }
        result = _detect_existing_providers(config)
        assert result == {"google", "openai"}

    def test_detects_plain_provider_names(self):
        """Also detects plain provider names (manually configured entries)."""
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
