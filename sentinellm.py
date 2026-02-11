#!/usr/bin/env python3
"""SentineLLM CLI - Interactive command-line interface."""

import sys

try:
    import questionary
except ImportError:
    print("❌ Error: questionary is not installed")
    print("Install it with: pip install questionary")
    sys.exit(1)

from src.cli.config_wizard import run_config_wizard
from src.cli.i18n import set_language, t
from src.cli.setup import check_ollama_installation, install_ollama_guide, run_setup


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
            # Parse optional arguments
            host = "127.0.0.1"
            port = 8080
            target_url = None

            for i, arg in enumerate(sys.argv[2:], start=2):
                if arg in ("--host", "-h") and i + 1 < len(sys.argv):
                    host = sys.argv[i + 1]
                elif arg in ("--port", "-p") and i + 1 < len(sys.argv):
                    port = int(sys.argv[i + 1])
                elif arg in ("--target-url", "-t") and i + 1 < len(sys.argv):
                    target_url = sys.argv[i + 1]

            print("\n🔒 Starting SentineLLM Proxy Server...")
            print(f"   Listening on: http://{host}:{port}")
            if target_url:
                print(f"   Target: {target_url}")
            else:
                print("   Target: OpenAI API (default)")
            print(f"\n   Configure your app to use: http://{host}:{port}/v1/chat/completions")
            print("   Press Ctrl+C to stop\n")

            from src.proxy.server import run_proxy

            run_proxy(host=host, port=port, target_url=target_url)
        elif command == "api":
            print("\n🔌 Starting SentineLLM API Server...")
            print("   Listening on: http://127.0.0.1:8000 (localhost only)")
            print("   Docs: http://localhost:8000/docs")
            print("   Press Ctrl+C to stop\n")
            import uvicorn

            from src.api.app import app

            uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)  # nosec B104
        else:
            print(f"{t('unknown_command')} {command}")
            print_help()
    else:
        # Interactive menu
        choice = questionary.select(
            t("main_menu"),
            choices=[
                "🚀 Start Proxy Server (recommended)",
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
            print("\n🔒 Starting SentineLLM Proxy Server...")
            print("   Listening on: http://127.0.0.1:8080 (localhost only)")
            print("\n   Configure your app to use: http://localhost:8080")
            print("   Press Ctrl+C to stop\n")
            from src.proxy.server import run_proxy

            run_proxy()
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
    print("  proxy          - Start LLM proxy server (recommended)")
    print("                   Options: --host HOST --port PORT --target-url URL")
    print(
        "                   Example: proxy --target-url https://generativelanguage.googleapis.com"
    )
    print("  api            - Start validation API server")
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
