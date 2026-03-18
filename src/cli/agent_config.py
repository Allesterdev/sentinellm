"""Auto-configuration for AI coding agents (OpenClaw, etc.).

Detects installed agents, finds their config files, and patches
baseUrl to route traffic through SentineLLM proxy — no manual editing required.
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

try:
    import questionary
    from questionary import Style
except ImportError:
    questionary = None

from .i18n import t

CUSTOM_STYLE = Style(
    [
        ("qmark", "fg:#673ab7 bold"),
        ("question", "bold"),
        ("answer", "fg:#2196f3 bold"),
        ("pointer", "fg:#673ab7 bold"),
        ("highlighted", "fg:#673ab7 bold"),
        ("selected", "fg:#4caf50"),
        ("separator", "fg:#cc5454"),
    ]
)


# ── Known agent definitions ────────────────────────────────────────────

KNOWN_AGENTS: dict[str, dict[str, Any]] = {
    "openclaw": {
        "name": "OpenClaw",
        "description": "AI agent",
        "config_paths": [
            "~/.openclaw/openclaw.json",
            "~/.openclaw/config.json5",
            "~/.openclaw/config.json",
            "~/.config/openclaw/openclaw.json",
            "~/.config/openclaw/config.json5",
            "~/.config/openclaw/config.json",
        ],
        "env_var": "OPENCLAW_CONFIG_PATH",
        "url_field": "baseUrl",
        "providers_path": ["models", "providers"],
    },
    "cline": {
        "name": "Cline",
        "description": "AI agent (VS Code)",
        "config_paths": [
            "~/.config/cline/config.json",
            "~/.cline/config.json",
        ],
        "env_var": None,
        "url_field": "baseUrl",
        "providers_path": ["providers"],
    },
    "aider": {
        "name": "Aider",
        "description": "AI pair programming",
        "config_paths": [
            "~/.aider.conf.yml",
            ".aider.conf.yml",
        ],
        "env_var": "OPENAI_API_BASE",
        "url_field": "openai-api-base",
        "providers_path": [],
    },
}

# Provider presets: name → default baseUrl
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com",
        "header": "Authorization",
    },
    "anthropic": {
        "name": "Anthropic (Claude)",
        "base_url": "https://api.anthropic.com",
        "header": "x-api-key",
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com",
        "header": "x-goog-api-key",
    },
    "google": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com",
        "header": "x-goog-api-key",
    },
    "ollama": {
        "name": "Ollama (local)",
        "base_url": "http://localhost:11434",
        "header": None,
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api",
        "header": "Authorization",
    },
    "azure": {
        "name": "Azure OpenAI",
        "base_url": "https://<your-resource>.openai.azure.com",
        "header": "api-key",
    },
    "custom": {
        "name": "Otro (personalizado)",
        "base_url": "",
        "header": None,
    },
}

# OpenClaw API type mapping (our provider name → OpenClaw ModelApi enum)
OPENCLAW_API_MAP: dict[str, str] = {
    "openai": "openai-responses",
    "anthropic": "anthropic",
    "gemini": "google-generative-ai",
    "google": "google-generative-ai",
    "ollama": "openai-chat",
    "openrouter": "openai-chat",
    "azure": "openai-chat",
}

# Default model info per provider (id, display name, API key env var)
PROVIDER_DEFAULT_MODELS: dict[str, dict[str, str | None]] = {
    "openai": {
        "id": "gpt-4o",
        "name": "GPT-4o (via SentineLLM)",
        "api_key_env": "OPENAI_API_KEY",  # pragma: allowlist secret
    },
    "anthropic": {
        "id": "claude-sonnet-4-5",
        "name": "Claude Sonnet 4.5 (via SentineLLM)",
        "api_key_env": "ANTHROPIC_API_KEY",  # pragma: allowlist secret
    },
    "gemini": {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash (via SentineLLM)",
        "api_key_env": "GEMINI_API_KEY",  # pragma: allowlist secret
    },
    "google": {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash (via SentineLLM)",
        "api_key_env": "GEMINI_API_KEY",  # pragma: allowlist secret
    },
    "ollama": {
        "id": "llama3.3",
        "name": "Llama 3.3 (via SentineLLM)",
        "api_key_env": None,
    },
    "openrouter": {
        "id": "anthropic/claude-sonnet-4-5",
        "name": "Claude Sonnet 4.5 via OpenRouter (via SentineLLM)",
        "api_key_env": "OPENROUTER_API_KEY",  # pragma: allowlist secret
    },
    "azure": {
        "id": "gpt-4o",
        "name": "GPT-4o Azure (via SentineLLM)",
        "api_key_env": "AZURE_OPENAI_API_KEY",  # pragma: allowlist secret
    },
}

# Available models per provider (for interactive selection)
PROVIDER_MODELS: dict[str, list[dict[str, str]]] = {
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
        {"id": "gpt-4.1", "name": "GPT-4.1"},
        {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini"},
        {"id": "o3-mini", "name": "o3-mini"},
    ],
    "anthropic": [
        {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5"},
        {"id": "claude-3-5-haiku-latest", "name": "Claude 3.5 Haiku"},
        {"id": "claude-3-opus-latest", "name": "Claude 3 Opus"},
    ],
    "gemini": [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
        {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite"},
    ],
    "google": [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
        {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite"},
    ],
    "ollama": [
        {"id": "llama3.3", "name": "Llama 3.3"},
        {"id": "llama3.2", "name": "Llama 3.2"},
        {"id": "mistral", "name": "Mistral 7B"},
        {"id": "codellama", "name": "Code Llama"},
        {"id": "deepseek-coder-v2", "name": "DeepSeek Coder V2"},
    ],
    "openrouter": [
        {"id": "anthropic/claude-sonnet-4-5", "name": "Claude Sonnet 4.5"},
        {"id": "openai/gpt-4o", "name": "GPT-4o"},
        {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
    ],
    "azure": [
        {"id": "gpt-4o", "name": "GPT-4o"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
    ],
}


def _find_agent_config(agent_id: str) -> Path | None:
    """Find the configuration file for a known agent."""
    agent = KNOWN_AGENTS.get(agent_id)
    if not agent:
        return None

    # Check environment variable first
    if agent.get("env_var"):
        env_path = os.environ.get(agent["env_var"])
        if env_path:
            p = Path(env_path).expanduser()
            if p.exists():
                return p

    # Search known paths
    for config_path in agent["config_paths"]:
        p = Path(config_path).expanduser()
        if p.exists():
            return p

    return None


def _detect_installed_agents() -> dict[str, Path]:
    """Detect which AI agents are installed by finding their config files."""
    found = {}
    for agent_id in KNOWN_AGENTS:
        config_path = _find_agent_config(agent_id)
        if config_path:
            found[agent_id] = config_path
    return found


def _read_json5_file(path: Path) -> dict[str, Any]:
    """Read a JSON5 or JSON file, stripping comments and trailing commas."""
    text = path.read_text(encoding="utf-8")

    # Strip single-line comments (//)
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    # Strip multi-line comments (/* ... */)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Strip trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _write_json_file(path: Path, data: dict[str, Any]) -> None:
    """Write data as pretty-printed JSON (compatible with JSON5 readers)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _write_env_file(providers: list[str]) -> Path:
    """Write .sentinellm.env file with TARGET_URL for configured providers.

    Args:
        providers: List of provider IDs (e.g., ["openai", "google"])

    Returns:
        Path to the created .env file
    """
    env_path = Path.home() / ".sentinellm.env"

    # If single provider, use it. If multiple, use first (user can edit)
    provider_id = providers[0] if providers else "openai"
    preset = PROVIDER_PRESETS.get(provider_id, {})
    target_url = preset.get("base_url", "https://api.openai.com")

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("# SentineLLM Proxy Configuration\n")
        f.write("# Auto-generated by 'sllm agent' wizard\n")
        f.write(f"# Active provider: {preset.get('name', provider_id)}\n\n")
        f.write(f"SENTINELLM_TARGET_URL={target_url}\n")

        if len(providers) > 1:
            f.write("\n# Other configured providers (uncomment to use):\n")
            for pid in providers[1:]:
                p = PROVIDER_PRESETS.get(pid, {})
                f.write(
                    f"# SENTINELLM_TARGET_URL={p.get('base_url', '')}  # {p.get('name', pid)}\n"
                )

    return env_path


def _get_proxy_url(host: str = "127.0.0.1", port: int = 8080) -> str:
    """Build the SentineLLM proxy URL."""
    return f"http://{host}:{port}"


def _create_openclaw_default_config() -> dict[str, Any]:
    """Create OpenClaw default config structure with required fields."""
    import secrets
    from datetime import datetime

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    version = "2026.2.6-3"
    # Generate secure random token for gateway auth
    gateway_token = secrets.token_hex(32)

    return {
        "messages": {"ackReactionScope": "group-mentions"},
        "agents": {
            "defaults": {"maxConcurrent": 4, "subagents": {"maxConcurrent": 8}},
        },
        "gateway": {
            "mode": "local",
            "port": 18789,
            "bind": "loopback",
            "auth": {"mode": "token", "token": gateway_token},
            "tailscale": {"mode": "off", "resetOnExit": False},
        },
        "wizard": {
            "lastRunAt": now,
            "lastRunVersion": version,
            "lastRunCommand": "configure",
            "lastRunMode": "local",
        },
        "meta": {"lastTouchedVersion": version, "lastTouchedAt": now},
    }


def _patch_openclaw_config(
    config_data: dict[str, Any],
    provider_name: str,
    proxy_url: str,
    model_id: str | None = None,
    model_name: str | None = None,
    api_key_value: str | None = None,
) -> dict[str, Any]:
    """Patch an OpenClaw config dict to route through SentineLLM.

    Creates a *custom* provider named ``sentinellm-{provider}`` (e.g.,
    ``sentinellm-gemini``) and sets it as the primary model.  This is the
    correct approach per the OpenClaw docs: ``models.providers`` is for
    custom/proxy providers — overriding the ``baseUrl`` of a built-in
    provider (e.g., ``google``) has no effect because OpenClaw uses the
    hardcoded endpoint for built-in providers.

    Args:
      config_data: Existing OpenClaw config dict to patch.
      provider_name: Provider ID (e.g., "gemini", "openai").
      proxy_url: SentineLLM proxy URL.
      model_id: Override the default model ID (e.g., "gemini-2.5-flash").
      model_name: Override the default display name for the model.
      api_key_value: If provided, write this literal API key instead of
                     an env var reference (``${VAR}``).  This avoids the
                     ``MissingEnvVarError`` that OpenClaw raises when the
                     env var does not exist.

    Config written:
      models.mode = "merge"
      models.providers.sentinellm-{provider}.baseUrl  = proxy_url
      models.providers.sentinellm-{provider}.api      = <api-type>
      models.providers.sentinellm-{provider}.apiKey   = ${API_KEY_ENV}
      models.providers.sentinellm-{provider}.models   = [{id, name}]
      agents.defaults.model.primary                   = sentinellm-{provider}/{model-id}
      agents.defaults.models.{model-ref}.alias        = {friendly name}
    """
    # Custom provider name avoids collision with OpenClaw built-ins
    custom_provider = f"sentinellm-{provider_name}"

    # Model info for this provider
    model_info = PROVIDER_DEFAULT_MODELS.get(
        provider_name,
        {
            "id": "default-model",
            "name": f"Audited model (via SentineLLM → {provider_name})",
            "api_key_env": None,
        },
    )

    # Allow overriding model ID and name
    if model_id:
        model_info = dict(model_info)  # shallow copy to avoid mutating global
        model_info["id"] = model_id
        if model_name:
            model_info["name"] = model_name
        else:
            model_info["name"] = f"{model_id} (via SentineLLM)"

    model_ref = f"{custom_provider}/{model_info['id']}"

    # ── models section (mode + providers) ──────────────────────────────
    if "models" not in config_data:
        config_data["models"] = {}
    config_data["models"]["mode"] = "merge"
    if "providers" not in config_data["models"]:
        config_data["models"]["providers"] = {}

    providers = config_data["models"]["providers"]

    # ── Try to recover existing API key from config ────────────────────
    # When the user originally configured OpenClaw, the API key may have
    # been stored as a literal value (e.g. "AIzaSy...") in a built-in or
    # custom provider.  We look in these places (in order of priority):
    #   1. Explicit `api_key_value` parameter (from _ensure_api_keys)
    #   2. Existing `sentinellm-{provider}` entry (re-patching)
    #   3. Built-in provider that matches `provider_name` (first install)
    #   4. Current environment variable
    #   5. Fallback: env var reference `${VAR}` (may cause OpenClaw error)
    resolved_api_key: str | None = api_key_value
    if not resolved_api_key:
        # Check our own custom provider first
        existing_entry = providers.get(custom_provider, {})
        existing_key = existing_entry.get("apiKey", "")
        if existing_key and not existing_key.startswith("${"):
            resolved_api_key = existing_key

    if not resolved_api_key:
        # Check built-in / original providers that OpenClaw may have
        # E.g. "google", "gemini", "openai", provider_name itself
        candidate_names = [provider_name]
        # Map our provider_name to common OpenClaw built-in names
        builtin_aliases = {
            "gemini": ["google", "gemini", "google-generative-ai"],
            "google": ["google", "gemini", "google-generative-ai"],
            "openai": ["openai"],
            "anthropic": ["anthropic"],
        }
        candidate_names = builtin_aliases.get(provider_name, [provider_name])
        for candidate in candidate_names:
            candidate_entry = providers.get(candidate, {})
            candidate_key = candidate_entry.get("apiKey", "")
            if candidate_key and not candidate_key.startswith("${"):
                resolved_api_key = candidate_key
                break

    if not resolved_api_key and model_info.get("api_key_env"):
        # Check if the env var actually exists in the environment
        env_value = os.environ.get(str(model_info["api_key_env"]), "")
        if env_value:
            resolved_api_key = env_value

    # Build provider entry — preserve existing custom model list if present
    existing_models: list = []
    if custom_provider in providers and isinstance(providers[custom_provider].get("models"), list):
        existing_models = providers[custom_provider]["models"]

    # Ensure our default model is in the list
    if not any(m.get("id") == model_info["id"] for m in existing_models):
        existing_models = [{"id": model_info["id"], "name": model_info["name"]}] + existing_models

    provider_entry: dict[str, Any] = {
        "baseUrl": proxy_url,
        "api": OPENCLAW_API_MAP.get(provider_name, "openai-completions"),
        "models": existing_models,
    }
    if model_info.get("api_key_env"):
        # Use resolved literal key if available, otherwise fall back to env var reference
        if resolved_api_key:
            provider_entry["apiKey"] = resolved_api_key  # pragma: allowlist secret
        else:
            provider_entry["apiKey"] = (
                f"${{{model_info['api_key_env']}}}"  # pragma: allowlist secret
            )
    elif provider_name == "ollama":
        provider_entry["apiKey"] = "ollama-local"  # pragma: allowlist secret

    providers[custom_provider] = provider_entry

    # ── agents.defaults: set primary model & allowlist ─────────────────
    if "agents" not in config_data:
        config_data["agents"] = {}
    if "defaults" not in config_data["agents"]:
        config_data["agents"]["defaults"] = {}

    agent_defaults = config_data["agents"]["defaults"]

    # Set model.primary
    if "model" not in agent_defaults:
        agent_defaults["model"] = {}
    agent_defaults["model"]["primary"] = model_ref

    # Add to models allowlist (alias shown in /model list)
    if "models" not in agent_defaults:
        agent_defaults["models"] = {}
    agent_defaults["models"][model_ref] = {"alias": f"{model_info['name']}"}

    return config_data


def configure_agent_interactive(
    proxy_host: str = "127.0.0.1",
    proxy_port: int = 8080,
) -> dict[str, Any] | None:
    """Interactive wizard to auto-configure an AI agent for SentineLLM.

    Returns the updated config dict, or None if cancelled.
    """
    if questionary is None:
        print(f"❌ {t('questionary_error')}")
        return None

    proxy_url = _get_proxy_url(proxy_host, proxy_port)

    print("\n" + "=" * 70)
    print(t("agent_config_title"))
    print("=" * 70)
    print(f"\n{t('agent_config_intro')}")

    # ── Detect installed agents ─────────────────────────────────────────
    print(f"\n{t('agent_scanning')}")
    detected = _detect_installed_agents()

    if detected:
        for agent_id, config_path in detected.items():
            agent = KNOWN_AGENTS[agent_id]
            print(f"  ✅ {agent['name']} → {config_path}")
    else:
        print(f"  {t('agent_none_found')}")

    # ── Choose agent ────────────────────────────────────────────────────
    agent_choices = []
    for agent_id, agent in KNOWN_AGENTS.items():
        status = "✅" if agent_id in detected else "⬚"
        desc = f" ({detected[agent_id]})" if agent_id in detected else ""
        agent_choices.append(
            questionary.Choice(
                f"{status} {agent['name']} — {agent['description']}{desc}",
                value=agent_id,
            )
        )
    agent_choices.append(
        questionary.Choice(
            f"📝 {t('agent_manual')}",
            value="manual",
        )
    )
    agent_choices.append(
        questionary.Choice(
            f"⏭️  {t('agent_skip')}",
            value="skip",
        )
    )

    selected_agent = questionary.select(
        t("agent_select"),
        choices=agent_choices,
        style=CUSTOM_STYLE,
    ).ask()

    if selected_agent == "skip" or selected_agent is None:
        return None

    # ── Proxy settings ──────────────────────────────────────────────────
    change_proxy = questionary.confirm(
        t("agent_change_proxy").format(proxy_url=proxy_url),
        default=False,
        style=CUSTOM_STYLE,
    ).ask()

    if change_proxy:
        proxy_host = questionary.text(
            "Host:",
            default=proxy_host,
            style=CUSTOM_STYLE,
        ).ask()
        proxy_port_str = questionary.text(
            "Port:",
            default=str(proxy_port),
            style=CUSTOM_STYLE,
        ).ask()
        proxy_port = int(proxy_port_str)
        proxy_url = _get_proxy_url(proxy_host, proxy_port)

    # ── Manual mode ─────────────────────────────────────────────────────
    if selected_agent == "manual":
        # For manual, pick a single provider and print instructions
        selected_provider = _select_single_provider()
        if selected_provider is None:
            return None
        preset = PROVIDER_PRESETS[selected_provider]
        target_url = _resolve_target_url(selected_provider, preset)
        _print_manual_instructions(target_url, proxy_url, preset)
        return {"mode": "manual", "target_url": target_url, "proxy_url": proxy_url}

    # ── Resolve config path ─────────────────────────────────────────────
    agent_def = KNOWN_AGENTS[selected_agent]
    config_path = detected.get(selected_agent)

    if not config_path:
        create_new = questionary.confirm(
            t("agent_create_config").format(agent=agent_def["name"]),
            default=True,
            style=CUSTOM_STYLE,
        ).ask()
        if not create_new:
            return None

        config_path = Path(agent_def["config_paths"][0]).expanduser()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Create OpenClaw default config with all required fields
        config_data: dict[str, Any] = (
            _create_openclaw_default_config() if selected_agent == "openclaw" else {}
        )
    else:
        config_data = _read_json5_file(config_path)
        # Merge with defaults if OpenClaw config is missing required fields
        if selected_agent == "openclaw":
            defaults = _create_openclaw_default_config()
            for key in ["messages", "agents", "gateway", "wizard", "meta"]:
                if key not in config_data:
                    config_data[key] = defaults[key]

    # ── OpenClaw: multi-provider selection ──────────────────────────────
    if selected_agent == "openclaw":
        # Detect providers already configured in the JSON
        existing_providers = _detect_existing_providers(config_data)

        # Build multi-select with all available providers
        # (skip "google" alias and "custom" from the checkbox list)
        provider_choices = []
        skip_ids = {"google", "custom"}
        for pid, preset in PROVIDER_PRESETS.items():
            if pid in skip_ids:
                continue
            already = pid in existing_providers
            status = "✅ " if already else ""
            provider_choices.append(
                questionary.Choice(
                    f"{status}{preset['name']} ({preset['base_url']})",
                    value=pid,
                    checked=already,
                )
            )

        print(f"\n{t('agent_select_provider')}")
        print("  💡 Usa ⬆️⬇️ para navegar, ESPACIO para marcar, ENTER para confirmar\n")

        # Get language-specific instruction text for checkbox
        from src.cli.i18n import get_language

        lang = get_language()
        checkbox_instruction = (
            "Usa las flechas para navegar, <espacio> para marcar/desmarcar, <enter> para confirmar"
            if lang == "es"
            else "Use arrow keys to move, <space> to select, <enter> to confirm"
        )

        selected_providers = questionary.checkbox(
            t("agent_multi_provider_question"),
            choices=provider_choices,
            instruction=checkbox_instruction,
            style=CUSTOM_STYLE,
        ).ask()

        if not selected_providers:
            print("  ⚠️  No se seleccionó ningún proveedor.")
            print("     Tip: Usa BARRA ESPACIADORA para marcar opciones antes de presionar ENTER")
            return None

        # Backup original config
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        if config_path.exists():
            shutil.copy2(config_path, backup_path)
            print(f"  📋 {t('agent_backup')} {backup_path}")

        # Select model for each provider
        # pid → (model_id, model_name)
        provider_models: dict[str, tuple[str, str]] = {}
        for provider_id in selected_providers:
            chosen_model_id, chosen_model_name = _select_model_for_provider(provider_id)
            provider_models[provider_id] = (chosen_model_id, chosen_model_name)

        # Ensure API keys are available for each provider
        provider_api_keys = _ensure_api_keys_configured(selected_providers)

        # Patch all selected providers
        for provider_id in selected_providers:
            preset = PROVIDER_PRESETS[provider_id]
            mid, mname = provider_models[provider_id]
            config_data = _patch_openclaw_config(
                config_data,
                provider_id,
                proxy_url,
                model_id=mid,
                model_name=mname,
                api_key_value=provider_api_keys.get(provider_id),
            )
            print(f"  🔌 {preset['name']} ({mid}) → {proxy_url}")

        _write_json_file(config_path, config_data)
        print(f"\n  ✅ {t('agent_config_saved')} {config_path}")

        # Create .sentinellm.env file
        env_path = _write_env_file(selected_providers)
        print(f"  ✅ Environment config saved: {env_path}")

        # Summary for multi-provider
        _print_multi_provider_summary(
            agent_name=agent_def["name"],
            providers=selected_providers,
            proxy_url=proxy_url,
            env_path=env_path,
        )

        return {
            "agent": selected_agent,
            "providers": selected_providers,
            "proxy_url": proxy_url,
            "config_path": str(config_path),
        }

    # ── Other agents: single provider ───────────────────────────────────
    selected_provider = _select_single_provider()
    if selected_provider is None:
        return None
    preset = PROVIDER_PRESETS[selected_provider]
    target_url = _resolve_target_url(selected_provider, preset)
    _print_manual_instructions(target_url, proxy_url, preset)

    _print_agent_summary(
        agent_name=agent_def["name"],
        provider_name=selected_provider,
        target_url=target_url,
        proxy_url=proxy_url,
    )

    return {
        "agent": selected_agent,
        "provider": selected_provider,
        "target_url": target_url,
        "proxy_url": proxy_url,
        "config_path": str(config_path) if config_path else None,
    }


def _ensure_api_keys_configured(
    provider_ids: list[str],
) -> dict[str, str | None]:
    """Check that required API key env vars exist; prompt for missing ones.

    For each provider that needs an API key, checks if the corresponding
    environment variable (e.g. ``GEMINI_API_KEY``) is set.  If not, asks
    the user to enter the key interactively.  The entered key is:

      1. Written to ``~/.sentinellm.env`` (loaded by the proxy).
      2. Set in the current process environment (for subsequent checks).
      3. Returned so the caller can write it as a **literal** value in the
         OpenClaw config — avoiding the ``MissingEnvVarError`` that OpenClaw
         raises when an ``${ENV_VAR}`` reference cannot be resolved.

    Returns:
        dict mapping provider_id → literal API key string (or ``None`` if
        the env var already existed and no literal override is needed).
    """
    result: dict[str, str | None] = {}
    env_path = Path.home() / ".sentinellm.env"

    for pid in provider_ids:
        model_info = PROVIDER_DEFAULT_MODELS.get(pid, {})
        env_var = model_info.get("api_key_env")

        if not env_var:
            # Provider doesn't need an API key (e.g. ollama)
            result[pid] = None
            continue

        existing_value = os.environ.get(env_var)
        if existing_value:
            # Env var already set — no override needed
            result[pid] = None
            continue

        # Env var missing — ask the user
        preset_name = PROVIDER_PRESETS.get(pid, {}).get("name", pid)
        # env_var is the NAME of an env var (e.g. "OPENAI_API_KEY"), not its
        # value. CodeQL flags it as sensitive because the name implies a key.
        # These prints show setup instructions to the user — not a credential leak.
        print(f"\n  ⚠️  Variable de entorno {env_var} no encontrada.")
        print(f"     OpenClaw necesita esta clave para conectar con {preset_name}.")

        if questionary is None:
            print(f"     Por favor establece: export {env_var}=tu-clave")
            result[pid] = None
            continue

        api_key = questionary.password(
            f"  🔑 Introduce tu API key de {preset_name} ({env_var}):",
            style=CUSTOM_STYLE,
        ).ask()

        if not api_key or not api_key.strip():
            print(f"     ⏭️  Omitido. Recuerda establecer {env_var} antes de usar OpenClaw.")
            result[pid] = None
            continue

        api_key = api_key.strip()

        # Set in current process for any further checks
        os.environ[env_var] = api_key

        # Append to ~/.sentinellm.env (so the proxy also picks it up)
        try:
            # Writing in clear text is intentional: .env files are the
            # standard mechanism for supplying API keys to local processes.
            # The file is user-owned (~/.sentinellm.env) and not committed
            # to version control.  Encrypting here would be pointless
            # because the consumer (the proxy) must read the plain value.
            with open(env_path, "a", encoding="utf-8") as f:
                f.write(f"\n# {preset_name} API key (added by sllm agent)\n")
                f.write(f"{env_var}={api_key}\n")
            print(f"     ✅ Guardada en {env_path}")
        except OSError:
            # Writing to ~/.sentinellm.env is best-effort; if it fails (e.g.
            # read-only filesystem) the key is still returned and written
            # directly into the agent config file — non-fatal, skip silently.
            pass

        # Return literal value so it's written directly in openclaw.json
        result[pid] = api_key  # pragma: allowlist secret

    return result


def _select_model_for_provider(provider_id: str) -> tuple[str, str]:
    """Interactive model selection for a provider.

    Shows available models and allows custom input.
    Returns (model_id, model_display_name).
    """
    default_info = PROVIDER_DEFAULT_MODELS.get(provider_id, {})
    default_model_id = default_info.get("id", "default-model")
    available = PROVIDER_MODELS.get(provider_id, [])

    if questionary is None or not available:
        # Non-interactive fallback
        return default_model_id, f"{default_model_id} (via SentineLLM)"

    preset_name = PROVIDER_PRESETS.get(provider_id, {}).get("name", provider_id)
    model_choices = []
    for m in available:
        is_default = m["id"] == default_model_id
        label = f"{'⭐ ' if is_default else ''}{m['name']} ({m['id']})"
        model_choices.append(questionary.Choice(label, value=m["id"]))
    model_choices.append(
        questionary.Choice("✏️  Otro (escribir ID manualmente)", value="__custom__")
    )

    selected = questionary.select(
        f"  Modelo para {preset_name}:",
        choices=model_choices,
        style=CUSTOM_STYLE,
    ).ask()

    if selected == "__custom__":
        custom_id = questionary.text(
            f"  ID del modelo {preset_name} (ej: {default_model_id}):",
            default=default_model_id,
            style=CUSTOM_STYLE,
        ).ask()
        if custom_id:
            return custom_id, f"{custom_id} (via SentineLLM)"
        return default_model_id, f"{default_model_id} (via SentineLLM)"

    if selected is None:
        return default_model_id, f"{default_model_id} (via SentineLLM)"

    # Find display name from catalog
    display = next((m["name"] for m in available if m["id"] == selected), selected)
    return selected, f"{display} (via SentineLLM)"


def _select_single_provider() -> str | None:
    """Show a single-select provider picker. Returns provider id or None."""
    provider_choices = []
    for pid, preset in PROVIDER_PRESETS.items():
        if pid == "google":  # skip alias
            continue
        provider_choices.append(questionary.Choice(f"{preset['name']}", value=pid))

    return questionary.select(
        t("agent_provider_question"),
        choices=provider_choices,
        style=CUSTOM_STYLE,
    ).ask()


def _resolve_target_url(provider_id: str, preset: dict[str, str]) -> str:
    """Resolve the target URL for a provider, prompting if needed."""
    if provider_id == "custom":
        return questionary.text(
            t("agent_custom_url"),
            default="https://api.example.com",
            style=CUSTOM_STYLE,
        ).ask()
    if provider_id == "azure":
        resource = questionary.text(
            t("agent_azure_resource"),
            style=CUSTOM_STYLE,
        ).ask()
        return f"https://{resource}.openai.azure.com"
    return preset["base_url"]


def _detect_existing_providers(config_data: dict[str, Any]) -> set[str]:
    """Detect which providers are already routed through SentineLLM.

    Checks ``models.providers`` for keys in the form ``sentinellm-{provider}``
    (the custom provider pattern written by ``_patch_openclaw_config``).  Also
    includes plain provider names so that manually-configured entries are
    detected correctly.
    """
    try:
        keys = set(config_data.get("models", {}).get("providers", {}).keys())
    except (AttributeError, TypeError):
        return set()

    result: set[str] = set()
    sentinellm_prefix = "sentinellm-"
    for key in keys:
        if key.startswith(sentinellm_prefix):
            # "sentinellm-gemini" → "gemini"
            result.add(key[len(sentinellm_prefix) :])
        else:
            result.add(key)
    return result


def _print_manual_instructions(
    target_url: str,
    proxy_url: str,
    preset: dict[str, str],
) -> None:
    """Print manual configuration instructions."""
    print(f"\n{'─' * 70}")
    print(t("agent_manual_title"))
    print(f"{'─' * 70}")
    print(f"\n  {t('agent_manual_step1')}")
    print(f"    baseUrl: {proxy_url}")
    print(f"\n  {t('agent_manual_step2')}")
    print(f"    SENTINELLM_TARGET_URL={target_url}")
    print(f"\n  {t('agent_manual_example')}")
    print(f"""
    // openclaw.json — models.providers section
    {{
      "models": {{
        "providers": {{
          "{preset["name"].lower().split()[0]}": {{
            "baseUrl": "{proxy_url}"
          }}
        }}
      }}
    }}

    # Start SentineLLM proxy:
    SENTINELLM_TARGET_URL={target_url} sllm proxy --port 8080
""")


def _print_agent_summary(
    agent_name: str,
    provider_name: str,
    target_url: str,
    proxy_url: str,
) -> None:
    """Print configuration summary."""
    print(f"\n{'=' * 70}")
    print(t("agent_summary_title"))
    print(f"{'=' * 70}")
    print(f"  🤖 {t('agent_summary_agent')} {agent_name}")
    print(f"  🔌 {t('agent_summary_provider')} {provider_name}")
    print(f"  🌐 {t('agent_summary_target')} {target_url}")
    print(f"  🛡️  {t('agent_summary_proxy')} {proxy_url}")
    print(f"\n  {t('agent_summary_flow')}")
    print(f"    {agent_name} → SentineLLM ({proxy_url}) → {target_url}")
    print(f"\n  {t('agent_summary_start')}")
    print(f"    SENTINELLM_TARGET_URL={target_url} sllm proxy")
    print(f"    # {t('agent_summary_or')}")
    print(f"    SENTINELLM_TARGET_URL={target_url} python sentinellm.py proxy")
    print(f"{'=' * 70}\n")


def _print_multi_provider_summary(
    agent_name: str,
    providers: list[str],
    proxy_url: str,
    env_path: Path | None = None,
) -> None:
    """Print summary for multi-provider configuration."""
    print(f"\n{'=' * 70}")
    print(t("agent_summary_title"))
    print(f"{'=' * 70}")
    print(f"  🤖 {t('agent_summary_agent')} {agent_name}")
    print(f"  🛡️  {t('agent_summary_proxy')} {proxy_url}")
    print("\n  Configured providers:")
    for pid in providers:
        preset = PROVIDER_PRESETS.get(pid, {})
        name = preset.get("name", pid)
        base_url = preset.get("base_url", "?")
        api_type = OPENCLAW_API_MAP.get(pid, "?")
        print(f"    🔌 {name} (api: {api_type})")
        print(f"       {agent_name} → SentineLLM ({proxy_url}) → {base_url}")

    print(f"\n  {t('agent_summary_start')}")
    if env_path and env_path.exists():
        print(f"    # Target URL already configured in {env_path}")
        print("    # Just run:")
        print("    sllm proxy")
        print(f"\n    # To switch providers, edit {env_path}")
    else:
        print("    # For each provider, start the proxy with its target:")
        for pid in providers:
            preset = PROVIDER_PRESETS.get(pid, {})
            base_url = preset.get("base_url", "")
            print(f"    SENTINELLM_TARGET_URL={base_url} sllm proxy")
    print(f"{'=' * 70}\n")


# ── Quick configuration (non-interactive) ───────────────────────────────


def quick_configure_openclaw(
    provider: str | list[str] = "openai",
    proxy_host: str = "127.0.0.1",
    proxy_port: int = 8080,
    model_id: str | None = None,
) -> bool:
    """Non-interactive: auto-patch OpenClaw config for SentineLLM.

    Args:
        provider: Provider name(s) — a string or list of strings.
                  E.g. "openai" or ["openai", "anthropic", "gemini"]
        proxy_host: SentineLLM proxy host
        proxy_port: SentineLLM proxy port
        model_id: Override the default model ID (applies to all providers).
                  E.g. "gemini-2.5-flash"

    Usage:
        from src.cli.agent_config import quick_configure_openclaw
        quick_configure_openclaw("anthropic")
        quick_configure_openclaw("gemini", model_id="gemini-2.5-flash")
        quick_configure_openclaw(["openai", "anthropic", "gemini"])

    Returns True if successful, False otherwise.
    """
    config_path = _find_agent_config("openclaw")
    if not config_path:
        print("❌ OpenClaw config not found")
        return False

    # Normalize to list
    providers = [provider] if isinstance(provider, str) else list(provider)

    proxy_url = _get_proxy_url(proxy_host, proxy_port)
    config_data = _read_json5_file(config_path)

    # Ensure OpenClaw has all required fields (merge with defaults if missing)
    defaults = _create_openclaw_default_config()
    for key in ["messages", "agents", "gateway", "wizard", "meta"]:
        if key not in config_data:
            config_data[key] = defaults[key]

    # Backup
    backup_path = config_path.with_suffix(config_path.suffix + ".bak")
    shutil.copy2(config_path, backup_path)

    for prov in providers:
        preset = PROVIDER_PRESETS.get(prov)
        if not preset:
            print(f"⚠️  Unknown provider: {prov} (skipped)")
            continue

        config_data = _patch_openclaw_config(
            config_data,
            prov,
            proxy_url,
            model_id=model_id,
        )
        model_label = model_id or PROVIDER_DEFAULT_MODELS.get(prov, {}).get("id", "?")
        print(f"  ✅ {prov} ({model_label}) → {proxy_url} → {preset['base_url']}")

    _write_json_file(config_path, config_data)

    # Create .sentinellm.env file
    _write_env_file(providers)

    print(f"✅ OpenClaw configured with {len(providers)} provider(s)")
    return True


# ── Uninstall / restore ──────────────────────────────────────────────────


def uninstall_agent_interactive() -> bool:
    """Restore an AI agent config to its pre-SentineLLM state.

    When ``sllm agent`` configures an agent it saves a ``<config>.bak`` backup.
    This wizard finds that backup and restores it, effectively undoing the
    SentineLLM integration.  Also offers to delete ``~/.sentinellm.env``.

    Returns True if something was restored, False if cancelled/nothing found.
    """
    if questionary is None:
        print(f"❌ {t('questionary_error')}")
        return False

    print("\n" + "=" * 70)
    print("🗑️  SentineLLM — Uninstall / Restore agent configuration")
    print("=" * 70)

    # ── Detect agents that have a .bak backup created by sllm agent ─────
    detected = _detect_installed_agents()
    if not detected:
        print("\n  ℹ️  No AI agent configuration found on this system.")
        return False

    # agent_id → (config_path, backup_path)
    restorable: dict[str, tuple[Path, Path]] = {}
    for agent_id, config_path in detected.items():
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        if backup_path.exists():
            restorable[agent_id] = (config_path, backup_path)

    if not restorable:
        print("\n  ℹ️  No backup files found.")
        print("     SentineLLM saves a backup when you run 'sllm agent'.")
        print("     If you never ran 'sllm agent', there is nothing to restore.")
        return False

    # ── Choose agent ─────────────────────────────────────────────────────
    agent_choices = []
    for agent_id, (config_path, backup_path) in restorable.items():
        agent_name = KNOWN_AGENTS[agent_id]["name"]
        agent_choices.append(
            questionary.Choice(
                f"  {agent_name}\n    Config:  {config_path}\n    Backup:  {backup_path}",
                value=agent_id,
            )
        )
    agent_choices.append(questionary.Choice("⏭️  Cancel", value="cancel"))

    selected = questionary.select(
        "Which agent do you want to restore?",
        choices=agent_choices,
    ).ask()

    if selected is None or selected == "cancel":
        print("  ℹ️  Cancelled.")
        return False

    config_path, backup_path = restorable[selected]
    agent_name = KNOWN_AGENTS[selected]["name"]

    # ── Confirm ───────────────────────────────────────────────────────────
    print(f"\n  This will replace:\n    {config_path}")
    print(f"  with the original backup:\n    {backup_path}")

    confirm = questionary.confirm(
        "  Proceed?",
        default=True,
    ).ask()

    if not confirm:
        print("  ℹ️  Cancelled.")
        return False

    # ── Restore ───────────────────────────────────────────────────────────
    shutil.copy2(config_path, config_path.with_suffix(config_path.suffix + ".pre-uninstall"))
    shutil.copy2(backup_path, config_path)
    print(f"\n  ✅ {agent_name} config restored from backup.")
    print(
        f"     (Previous state saved to {config_path.with_suffix(config_path.suffix + '.pre-uninstall')})"
    )

    # ── Offer to delete ~/.sentinellm.env ─────────────────────────────────
    env_path = Path.home() / ".sentinellm.env"
    if env_path.exists():
        delete_env = questionary.confirm(
            f"\n  Also delete {env_path}?",
            default=True,
        ).ask()
        if delete_env:
            env_path.unlink()
            print(f"  🗑️  Deleted {env_path}")

    print(f"\n  ✅ Done. Restart {agent_name} for changes to take effect.")
    print("=" * 70)
    return True
