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
        else:
            print(f"{t('unknown_command')} {command}")
            print_help()
    else:
        # Interactive menu
        choice = questionary.select(
            t("main_menu"),
            choices=[
                t("setup_option"),
                t("config_option"),
                t("check_ollama_option"),
                t("install_ollama_option"),
                t("demo_option"),
                t("exit_option"),
            ],
        ).ask()

        if choice == t("setup_option"):
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
