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
        "description": "AI coding agent",
        "config_paths": [
            "~/.config/openclaw/config.json5",
            "~/.config/openclaw/config.json",
            "~/.openclaw/config.json5",
            "~/.openclaw/config.json",
            "~/openclaw/config.json",
            "/usr/local/lib/node_modules/openclaw/config.json",
        ],
        "env_var": "OPENCLAW_CONFIG",
        "url_field": "baseUrl",
        "providers_path": ["models", "providers"],
    },
    "cline": {
        "name": "Cline",
        "description": "AI coding agent (VS Code)",
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


def _get_proxy_url(host: str = "127.0.0.1", port: int = 8080) -> str:
    """Build the SentineLLM proxy URL."""
    return f"http://{host}:{port}"


def _patch_openclaw_config(
    config_data: dict[str, Any],
    provider_name: str,
    original_base_url: str,
    proxy_url: str,
) -> dict[str, Any]:
    """Patch an OpenClaw config dict to route through SentineLLM.

    Adds/updates a provider entry with:
      - baseUrl pointing to SentineLLM proxy
      - x-sentinellm-target header with the original URL
    """
    # Ensure models.providers exists
    if "models" not in config_data:
        config_data["models"] = {}
    if "providers" not in config_data["models"]:
        config_data["models"]["providers"] = {}

    providers = config_data["models"]["providers"]

    # Create or update the provider entry
    if provider_name not in providers:
        providers[provider_name] = {}

    provider = providers[provider_name]

    # Save original URL as fallback info
    if "baseUrl" in provider and provider["baseUrl"] != proxy_url:
        provider["_original_baseUrl"] = provider["baseUrl"]

    # Point to SentineLLM proxy
    provider["baseUrl"] = proxy_url

    # Add target header so the proxy knows where to forward
    if "headers" not in provider:
        provider["headers"] = {}
    provider["headers"]["X-Target-URL"] = original_base_url

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

    # ── Choose provider ─────────────────────────────────────────────────
    print(f"\n{t('agent_select_provider')}")

    provider_choices = []
    for pid, preset in PROVIDER_PRESETS.items():
        provider_choices.append(questionary.Choice(f"{preset['name']}", value=pid))

    selected_provider = questionary.select(
        t("agent_provider_question"),
        choices=provider_choices,
        style=CUSTOM_STYLE,
    ).ask()

    if selected_provider is None:
        return None

    preset = PROVIDER_PRESETS[selected_provider]

    # Get the target URL (original LLM endpoint)
    if selected_provider == "custom":
        target_url = questionary.text(
            t("agent_custom_url"),
            default="https://api.example.com",
            style=CUSTOM_STYLE,
        ).ask()
    elif selected_provider == "azure":
        resource = questionary.text(
            t("agent_azure_resource"),
            style=CUSTOM_STYLE,
        ).ask()
        target_url = f"https://{resource}.openai.azure.com"
    else:
        target_url = preset["base_url"]

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

    # ── Apply configuration ─────────────────────────────────────────────
    if selected_agent == "manual":
        # Just print instructions
        _print_manual_instructions(target_url, proxy_url, preset)
        return {"mode": "manual", "target_url": target_url, "proxy_url": proxy_url}

    agent_def = KNOWN_AGENTS[selected_agent]
    config_path = detected.get(selected_agent)

    if not config_path:
        # Config file doesn't exist — create it
        create_new = questionary.confirm(
            t("agent_create_config").format(agent=agent_def["name"]),
            default=True,
            style=CUSTOM_STYLE,
        ).ask()
        if not create_new:
            _print_manual_instructions(target_url, proxy_url, preset)
            return None

        # Use first known path
        config_path = Path(agent_def["config_paths"][0]).expanduser()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_data: dict[str, Any] = {}
    else:
        # Read existing config
        config_data = _read_json5_file(config_path)

    # Choose a provider name/key for the config
    provider_name = questionary.text(
        t("agent_provider_name"),
        default=selected_provider,
        style=CUSTOM_STYLE,
    ).ask()

    if selected_agent == "openclaw":
        # Backup original config
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        if config_path.exists():
            shutil.copy2(config_path, backup_path)
            print(f"  📋 {t('agent_backup')} {backup_path}")

        # Patch config
        config_data = _patch_openclaw_config(
            config_data,
            provider_name,
            target_url,
            proxy_url,
        )
        _write_json_file(config_path, config_data)
        print(f"\n  ✅ {t('agent_config_saved')} {config_path}")

    else:
        # For other agents, print manual instructions
        _print_manual_instructions(target_url, proxy_url, preset)

    # ── Summary ─────────────────────────────────────────────────────────
    _print_agent_summary(
        agent_name=agent_def["name"],
        provider_name=provider_name,
        target_url=target_url,
        proxy_url=proxy_url,
    )

    return {
        "agent": selected_agent,
        "provider": provider_name,
        "target_url": target_url,
        "proxy_url": proxy_url,
        "config_path": str(config_path),
    }


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
    print(f"    X-Target-URL: {target_url}")
    print(f"\n  {t('agent_manual_example')}")
    print(f"""
    // config.json5  (OpenClaw example)
    {{
      "models": {{
        "providers": {{
          "{preset["name"].lower().split()[0]}": {{
            "baseUrl": "{proxy_url}",
            "headers": {{
              "X-Target-URL": "{target_url}"
            }}
          }}
        }}
      }}
    }}
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
    print(f"    sllm proxy {provider_name}")
    print(f"    # {t('agent_summary_or')}")
    print(f"    python sentinellm.py proxy -t {target_url}")
    print(f"{'=' * 70}\n")


# ── Quick configuration (non-interactive) ───────────────────────────────


def quick_configure_openclaw(
    provider: str = "openai",
    proxy_host: str = "127.0.0.1",
    proxy_port: int = 8080,
) -> bool:
    """Non-interactive: auto-patch OpenClaw config for SentineLLM.

    Usage:
        from src.cli.agent_config import quick_configure_openclaw
        quick_configure_openclaw("anthropic")

    Returns True if successful, False otherwise.
    """
    config_path = _find_agent_config("openclaw")
    if not config_path:
        print("❌ OpenClaw config not found")
        return False

    preset = PROVIDER_PRESETS.get(provider)
    if not preset:
        print(f"❌ Unknown provider: {provider}")
        return False

    proxy_url = _get_proxy_url(proxy_host, proxy_port)
    config_data = _read_json5_file(config_path)

    # Backup
    backup_path = config_path.with_suffix(config_path.suffix + ".bak")
    shutil.copy2(config_path, backup_path)

    config_data = _patch_openclaw_config(
        config_data,
        provider,
        preset["base_url"],
        proxy_url,
    )
    _write_json_file(config_path, config_data)

    print(f"✅ OpenClaw configured: {provider} → {proxy_url} → {preset['base_url']}")
    return True
