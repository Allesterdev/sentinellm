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
        "id": "gemini-2.0-flash",
        "name": "Gemini 2.0 Flash (via SentineLLM)",
        "api_key_env": "GEMINI_API_KEY",  # pragma: allowlist secret
    },
    "google": {
        "id": "gemini-2.0-flash",
        "name": "Gemini 2.0 Flash (via SentineLLM)",
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
    original_base_url: str,
    proxy_url: str,
) -> dict[str, Any]:
    """Patch an OpenClaw config dict to route through SentineLLM.

    Creates a *custom* provider named ``sentinellm-{provider}`` (e.g.,
    ``sentinellm-gemini``) and sets it as the primary model.  This is the
    correct approach per the OpenClaw docs: ``models.providers`` is for
    custom/proxy providers — overriding the ``baseUrl`` of a built-in
    provider (e.g., ``google``) has no effect because OpenClaw uses the
    hardcoded endpoint for built-in providers.

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
    model_ref = f"{custom_provider}/{model_info['id']}"

    # ── models section (mode + providers) ──────────────────────────────
    if "models" not in config_data:
        config_data["models"] = {}
    config_data["models"]["mode"] = "merge"
    if "providers" not in config_data["models"]:
        config_data["models"]["providers"] = {}

    providers = config_data["models"]["providers"]

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
        provider_entry["apiKey"] = f"${{{model_info['api_key_env']}}}"  # pragma: allowlist secret
    elif provider_name == "ollama":
        provider_entry["apiKey"] = "ollama-local"

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

        # Patch all selected providers
        for provider_id in selected_providers:
            preset = PROVIDER_PRESETS[provider_id]
            config_data = _patch_openclaw_config(
                config_data,
                provider_id,
                preset["base_url"],
                proxy_url,
            )
            print(f"  🔌 {preset['name']} → {proxy_url}")

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
) -> bool:
    """Non-interactive: auto-patch OpenClaw config for SentineLLM.

    Args:
        provider: Provider name(s) — a string or list of strings.
                  E.g. "openai" or ["openai", "anthropic", "gemini"]
        proxy_host: SentineLLM proxy host
        proxy_port: SentineLLM proxy port

    Usage:
        from src.cli.agent_config import quick_configure_openclaw
        quick_configure_openclaw("anthropic")
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
            preset["base_url"],
            proxy_url,
        )
        print(f"  ✅ {prov} → {proxy_url} → {preset['base_url']}")

    _write_json_file(config_path, config_data)

    # Create .sentinellm.env file
    _write_env_file(providers)

    print(f"✅ OpenClaw configured with {len(providers)} provider(s)")
    return True
