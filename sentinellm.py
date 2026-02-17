#!/usr/bin/env python3
"""SentineLLM CLI - Interactive command-line interface.

Quick usage (alias: sllm):
    sllm                          # Interactive menu
    sllm proxy                    # Start proxy (interactive target)
    sllm proxy openai             # Proxy → OpenAI
    sllm proxy anthropic          # Proxy → Anthropic (Claude)
    sllm proxy gemini             # Proxy → Google Gemini
    sllm proxy ollama             # Proxy → Ollama local
    sllm proxy openrouter         # Proxy → OpenRouter
    sllm proxy <URL>              # Proxy → custom URL
    sllm agent                    # Auto-configure AI agent (OpenClaw, etc.)
    sllm setup                    # Full initial setup
    sllm config                   # Change configuration
"""

import logging
import sys
from pathlib import Path

from src.cli.config_wizard import run_config_wizard
from src.cli.i18n import set_language, t
from src.cli.setup import check_ollama_installation, install_ollama_guide, run_setup

logger = logging.getLogger(__name__)

try:
    import questionary
except ImportError:
    print("❌ Error: questionary is not installed")
    print("Install it with: pip install questionary")
    sys.exit(1)


# ── Provider shortcuts ──────────────────────────────────────────────────
PROVIDER_SHORTCUTS: dict[str, str] = {
    "openai": "https://api.openai.com",
    "anthropic": "https://api.anthropic.com",
    "claude": "https://api.anthropic.com",
    "gemini": "https://generativelanguage.googleapis.com",
    "google": "https://generativelanguage.googleapis.com",
    "ollama": "http://localhost:11434",
    "openrouter": "https://openrouter.ai/api",
    "azure": "https://api.openai.com",  # placeholder — user will customize
    "groq": "https://api.groq.com/openai",
    "together": "https://api.together.xyz",
    "mistral": "https://api.mistral.ai",
    "deepseek": "https://api.deepseek.com",
    "local": "http://localhost:11434",
}


def _resolve_target(arg: str | None) -> str | None:
    """Resolve a provider shortcut or URL to a target URL."""
    if arg is None:
        return None
    # If it's a known provider shortcut, resolve it
    if arg.lower() in PROVIDER_SHORTCUTS:
        return PROVIDER_SHORTCUTS[arg.lower()]
    # If it looks like a URL, use it directly
    if arg.startswith(("http://", "https://")):
        return arg
    return None


def select_language():
    """Select language at startup."""
    lang = questionary.select(
        "Select language / Selecciona idioma:",
        choices=["🇬🇧 English", "🇪🇸 Español"],
    ).ask()

    if lang and "English" in lang:
        set_language("en")
    elif lang and "Español" in lang:
        set_language("es")
    else:
        set_language("en")  # Default to English


def _start_proxy(host: str = "127.0.0.1", port: int = 8080, target_url: str | None = None):
    """Start the SentineLLM proxy server."""
    print("\n🔒 Starting SentineLLM Proxy Server...")
    print(f"   Listening on: http://{host}:{port}")
    if target_url:
        # Show friendly provider name if possible
        provider_name = None
        for name, url in PROVIDER_SHORTCUTS.items():
            if url == target_url:
                provider_name = name.capitalize()
                break
        if provider_name:
            print(f"   Target: {provider_name} ({target_url})")
        else:
            print(f"   Target: {target_url}")
    else:
        print("   Target: Dynamic (via X-Target-URL header)")
    print(f"\n   Configure your app to use: http://{host}:{port}")
    print("   Press Ctrl+C to stop\n")

    from src.proxy.server import run_proxy

    run_proxy(host=host, port=port, target_url=target_url)


def _interactive_proxy():
    """Interactively select a provider and start proxy."""
    provider_choices = [
        questionary.Choice("🟢 OpenAI (GPT-4, etc.)", value="openai"),
        questionary.Choice("🟣 Anthropic (Claude)", value="anthropic"),
        questionary.Choice("🔵 Google Gemini", value="gemini"),
        questionary.Choice("🟠 Ollama (local)", value="ollama"),
        questionary.Choice("🌐 OpenRouter", value="openrouter"),
        questionary.Choice("⚡ Groq", value="groq"),
        questionary.Choice("🤝 Together AI", value="together"),
        questionary.Choice("🔷 Mistral AI", value="mistral"),
        questionary.Choice("🐋 DeepSeek", value="deepseek"),
        questionary.Choice("📝 Custom URL", value="custom"),
    ]

    choice = questionary.select(
        t("proxy_select_provider"),
        choices=provider_choices,
    ).ask()

    if choice is None:
        return

    if choice == "custom":
        target_url = questionary.text(
            "LLM provider URL:",
            default="https://api.example.com",
        ).ask()
    else:
        target_url = PROVIDER_SHORTCUTS.get(choice)

    _start_proxy(target_url=target_url)


def main():
    """Main CLI entry point."""
    # Select language on first run
    select_language()

    print("\n🛡️  SENTINELLM CLI")

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "setup":
            run_setup()
        elif command == "config":
            run_config_wizard()
        elif command == "agent":
            from src.cli.agent_config import configure_agent_interactive

            configure_agent_interactive()
        elif command == "check-ollama":
            status = check_ollama_installation()
            print(f"\n📊 {t('status_title')}")
            print(f"  {t('installed')} {'✅' if status['installed'] else '❌'}")
            print(f"  {t('running')} {'✅' if status['running'] else '❌'}")
            if status["models"]:
                # type: ignore
                print(f"  {t('models')} {', '.join(status['models'])}")
            else:
                print(f"  {t('no_models')}")
        elif command == "install-ollama":
            install_ollama_guide()
        elif command == "demo":
            from examples.interactive_demo import main as demo_main

            demo_main()
        elif command == "proxy":
            # Parse arguments — supports both shortcuts and flags
            host = "127.0.0.1"
            port = 8080
            target_url = None

            # Try to load target URL from .sentinellm.env if not provided
            env_file = Path.home() / ".sentinellm.env"
            if env_file.exists():
                try:
                    for line in env_file.read_text().splitlines():
                        line = line.strip()
                        if line.startswith("SENTINELLM_TARGET_URL="):
                            target_url = line.split("=", 1)[1].strip()
                            break
                except (OSError, ValueError) as e:
                    # Log but don't fail - env file is optional
                    logger.debug("Could not read %s: %s", env_file, e)

            # Check if next arg is a provider shortcut or URL
            remaining = sys.argv[2:]
            if remaining:
                first_arg = remaining[0]
                # Try as provider shortcut or URL (not a flag)
                if not first_arg.startswith("-"):
                    resolved = _resolve_target(first_arg)
                    if resolved:
                        target_url = resolved
                        remaining = remaining[1:]
                    else:
                        print(f"⚠️  Unknown provider: {first_arg}")
                        print(f"   Available: {', '.join(sorted(PROVIDER_SHORTCUTS.keys()))}")
                        return

            # Parse remaining flags
            i = 0
            while i < len(remaining):
                arg = remaining[i]
                if arg in ("--host", "-h") and i + 1 < len(remaining):
                    host = remaining[i + 1]
                    i += 2
                elif arg in ("--port", "-p") and i + 1 < len(remaining):
                    port = int(remaining[i + 1])
                    i += 2
                elif arg in ("--target-url", "-t") and i + 1 < len(remaining):
                    target_url = remaining[i + 1]
                    i += 2
                else:
                    i += 1

            if target_url is None and not remaining:
                # No target specified — interactive provider selection
                _interactive_proxy()
            else:
                _start_proxy(host=host, port=port, target_url=target_url)

        elif command == "api":
            print("\n🔌 Starting SentineLLM API Server...")
            print("   Listening on: http://127.0.0.1:8000 (localhost only)")
            print("   Docs: http://localhost:8000/docs")
            print("   Press Ctrl+C to stop\n")
            import uvicorn

            from src.api.app import app

            uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)  # nosec B104
        elif command in ("--help", "-h", "help"):
            print_help()
        else:
            print(f"{t('unknown_command')} {command}")
            print_help()
    else:
        # Interactive menu
        choice = questionary.select(
            t("main_menu"),
            choices=[
                "🚀 Start Proxy Server (recommended)",
                "🤖 Configure AI Agent (OpenClaw, etc.)",
                "🔌 Start API Server",
                t("setup_option"),
                t("config_option"),
                t("check_ollama_option"),
                t("install_ollama_option"),
                t("demo_option"),
                t("exit_option"),
            ],
        ).ask()

        if choice == "🚀 Start Proxy Server (recommended)":
            _interactive_proxy()
        elif choice == "🤖 Configure AI Agent (OpenClaw, etc.)":
            from src.cli.agent_config import configure_agent_interactive

            configure_agent_interactive()
        elif choice == "🔌 Start API Server":
            print("\n🔌 Starting SentineLLM API Server...")
            print("   API: http://127.0.0.1:8000 (localhost only)")
            print("   Press Ctrl+C to stop\n")
            import uvicorn

            from src.api.app import app

            uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)  # nosec B104
        elif choice == t("setup_option"):
            run_setup()
        elif choice == t("config_option"):
            run_config_wizard()
        elif choice == t("check_ollama_option"):
            status = check_ollama_installation()
            print(f"\n📊 {t('status_title')}")
            print(f"  {t('installed')} {'✅' if status['installed'] else '❌'}")
            print(f"  {t('running')} {'✅' if status['running'] else '❌'}")
            if status["models"]:
                # type: ignore
                print(f"  {t('models')} {', '.join(status['models'])}")
        elif choice == t("install_ollama_option"):
            install_ollama_guide()
        elif choice == t("demo_option"):
            from examples.interactive_demo import main as demo_main

            demo_main()


def print_help():
    """Print help message."""
    print(f"\n{t('help_title')}")
    print(f"{t('help_commands')}")
    print("")
    print("  proxy [PROVIDER]  - Start LLM proxy server (recommended)")
    print("                      Shortcuts: openai, anthropic, gemini, ollama,")
    print("                                 openrouter, groq, together, mistral,")
    print("                                 deepseek, local")
    print("                      Flags: --host HOST --port PORT --target-url URL")
    print("")
    print("  Examples:")
    print("    sllm proxy openai          # Proxy to OpenAI")
    print("    sllm proxy gemini          # Proxy to Google Gemini")
    print("    sllm proxy ollama          # Proxy to Ollama (local)")
    print("    sllm proxy                 # Interactive provider selection")
    print("    sllm proxy https://custom  # Proxy to custom URL")
    print("")
    print("  agent            - Auto-configure AI agent (OpenClaw, etc.)")
    print("  api              - Start validation API server")
    print(f"  {t('help_setup')}")
    print(f"  {t('help_config')}")
    print(f"  {t('help_check')}")
    print(f"  {t('help_install')}")
    print(f"  {t('help_demo')}")
    print(f"{t('help_no_args')}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(t("goodbye"))
        sys.exit(0)
