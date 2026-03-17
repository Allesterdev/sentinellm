"""Setup wizard for first-time SentineLLM installation."""

import shutil
import subprocess
import sys
from pathlib import Path

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
    ]
)


def check_ollama_installation() -> dict[str, bool | list[str]]:
    """Check Ollama installation status."""
    installed = shutil.which("ollama") is not None
    running = False
    models = []

    if installed:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            running = result.returncode == 0
            if running:
                lines = result.stdout.strip().split("\n")[1:]
                models = [line.split()[0] for line in lines if line.strip()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Ollama is not installed or not responding — return defaults silently.
            pass

    return {"installed": installed, "running": running, "models": models}


def install_ollama_guide():
    """Show Ollama installation guide."""
    print("\n" + "=" * 70)
    print(t("ollama_install_title"))
    print("=" * 70)

    if sys.platform.startswith("linux"):
        print(f"\n{t('linux_section')}")
        print("   curl -fsSL https://ollama.com/install.sh | sh")
        print(f"\n{t('install_after')}")
        print(f"   {t('start_service')}")
        print(f"   {t('download_model_cmd')}")

    elif sys.platform == "darwin":
        print(f"\n{t('mac_section')}")
        print("   curl -fsSL https://ollama.com/install.sh | sh")
        print("\n   Or download from: https://ollama.com/download")
        print(f"\n{t('install_after')}")
        print(f"   {t('start_service')}")
        print(f"   {t('download_model_cmd')}")

    elif sys.platform == "win32":
        print(f"\n{t('windows_section')}")
        print("   Download the installer from: https://ollama.com/download")
        print(f"\n{t('install_after')}")
        print(f"   {t('download_model_cmd')}")

    print(f"\n{t('recommended_models')}")
    print(f"   {t('mistral_model')}")
    print(f"   {t('llama_model')}")
    print(f"   {t('phi_model')}")

    print(f"\n{t('more_info')}")
    print("=" * 70)


def run_setup():
    """Run first-time setup wizard."""
    if questionary is None:
        print(f"❌ {t('questionary_error')}")
        print(t("install_questionary"))
        return

    print("\n" + "=" * 70)
    print(t("setup_welcome"))
    print("=" * 70)
    print(f"\n{t('setup_intro')}")

    # Check Python version
    py_version = sys.version_info
    if py_version < (3, 10):
        print(
            f"⚠️  {t('python_version_warning').format(version=f'{py_version.major}.{py_version.minor}')}"
        )
        print(t("python_required"))
        if not questionary.confirm(t("continue_anyway"), default=False, style=CUSTOM_STYLE).ask():
            return

    # Check dependencies
    print(t("checking_deps"))

    missing_deps = []
    for dep in ["yaml", "httpx"]:
        try:
            __import__(dep)
            print(f"  ✓ {dep}")
        except ImportError:
            print(f"  ✗ {dep} - {t('missing_deps').split(':')[1].strip()}")
            missing_deps.append(dep)

    if missing_deps:
        print(f"\n{t('install_deps')}")
        if questionary.confirm(t("install_deps"), default=True, style=CUSTOM_STYLE).ask():
            print(t("installing"))
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                check=False,
            )

    # Check Ollama
    print(t("checking_ollama"))
    ollama_status = check_ollama_installation()

    if ollama_status["installed"]:
        print(f"  {t('ollama_ready')}")
        if ollama_status["running"]:
            print(f"  {t('ollama_running')}")
            if ollama_status["models"]:
                print(
                    # type: ignore
                    f"  {t('ollama_models')} {', '.join(ollama_status['models'])}"
                )
            else:
                print(f"  {t('ollama_no_models')}")
                if questionary.confirm(
                    t("download_model"),
                    default=True,
                    style=CUSTOM_STYLE,
                ).ask():
                    print(t("downloading"))
                    subprocess.run(["ollama", "pull", "mistral:7b"], check=False)
        else:
            print(f"  {t('ollama_not_running')}")
            print(f"     {t('start_ollama')}")
    else:
        print(f"  {t('ollama_optional_info')}")
        if questionary.confirm(
            t("see_install_guide"),
            default=True,
            style=CUSTOM_STYLE,
        ).ask():
            install_ollama_guide()

    # Create config directory
    config_dir = Path("config")
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
        print(f"\n✓ {t('created_dir')} {config_dir}/")

    # Run configuration wizard
    print("\n" + "=" * 70)
    if questionary.confirm(
        t("run_wizard"),
        default=True,
        style=CUSTOM_STYLE,
    ).ask():
        from .config_wizard import run_config_wizard

        run_config_wizard()
    else:
        print(t("configure_later"))
        print("   python -m src.cli.config_wizard")

    # Offer to auto-configure an AI agent (OpenClaw, etc.)
    print("\n" + "=" * 70)
    configure_agent = questionary.confirm(
        "🤖 Configure an AI agent (OpenClaw, etc.) to use SentineLLM?",
        default=True,
        style=CUSTOM_STYLE,
    ).ask()

    if configure_agent:
        from .agent_config import configure_agent_interactive

        configure_agent_interactive()
    else:
        print("  💡 You can configure agents later with: sllm agent")

    print("\n" + "=" * 70)
    print(t("setup_complete"))
    print("=" * 70)
    print("\n🚀 Next steps:")
    print("  1. Start proxy:  sllm proxy openai    (or gemini, anthropic, ollama...)")
    print("  2. Test demo:    sllm demo")
    print("  3. Read docs:    cat README.md")
    print("\n🔒 To protect OpenClaw or other LLM apps:")
    print("  • Run:  sllm proxy")
    print("  • Or:   sllm agent   (to auto-configure your agent)")
    print("  • Your agent traffic will be audited automatically")


if __name__ == "__main__":
    run_setup()
