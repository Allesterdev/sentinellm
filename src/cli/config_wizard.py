"""Interactive configuration wizard for SentineLLM."""

import shutil
import subprocess
from pathlib import Path
from typing import Any

try:
    import questionary
    from questionary import Style
except ImportError:
    questionary = None

import yaml

from .i18n import t

# Custom style for better UX
CUSTOM_STYLE = Style(
    [
        ("qmark", "fg:#673ab7 bold"),  # Purple question mark
        ("question", "bold"),
        ("answer", "fg:#2196f3 bold"),  # Blue answers
        ("pointer", "fg:#673ab7 bold"),  # Purple pointer
        ("highlighted", "fg:#673ab7 bold"),
        ("selected", "fg:#4caf50"),  # Green selected
        ("separator", "fg:#cc5454"),
        ("instruction", ""),
        ("text", ""),
    ]
)


def check_ollama_installed() -> bool:
    """Check if Ollama is installed and running."""
    return shutil.which("ollama") is not None


def check_ollama_running() -> bool:
    """Check if Ollama service is running."""
    try:
        result = subprocess.run(
            ["ollama", "list"],  # noqa: S607
            capture_output=True,
            timeout=3,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_ollama_models() -> list[str]:
    """Get list of installed Ollama models."""
    try:
        result = subprocess.run(
            ["ollama", "list"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            return [line.split()[0] for line in lines if line.strip()]
        return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def print_welcome():
    """Print welcome message."""
    print("\n" + "=" * 70)
    print(t("welcome_title"))
    print("=" * 70)
    print(f"\n{t('welcome_intro')}")
    print(t("welcome_protects"))
    print(f"  {t('prompt_injection')}")
    print(f"  {t('secret_leaks')}")
    print(f"  {t('memory_attacks')}\n")


def print_ollama_info():
    """Print information about Ollama."""
    print(f"\n{t('about_ollama')}")
    print("-" * 70)
    print(t("ollama_description"))
    print(t("ollama_optional"))
    print(f"\n{t('why_ollama')}")
    print(f"  {t('ollama_deep')}")
    print(f"  {t('ollama_semantic')}")
    print(f"  {t('ollama_private')}")
    print(f"\n{t('ollama_install')}")
    print(f"  {t('ollama_linux')}")
    print(f"  {t('ollama_windows')}")
    print(f"  {t('ollama_model')}\n")


def run_config_wizard() -> dict[str, Any]:
    """Run interactive configuration wizard."""
    if questionary is None:
        print(f"❌ {t('questionary_error')}")
        print(t("install_questionary"))
        return {}

    print_welcome()

    config: dict[str, Any] = {
        "prompt_injection": {"enabled": True, "layers": {}},
        "secret_detection": {"enabled": True},
        "ollama": {},
    }

    # 1. Ask about prompt injection detection
    if questionary.confirm(
        t("enable_prompt_injection"),
        default=True,
        style=CUSTOM_STYLE,
    ).ask():
        config["prompt_injection"]["enabled"] = True

        # Regex layer (always recommended)
        config["prompt_injection"]["layers"]["regex"] = {
            "enabled": True,
            "threat_threshold": "medium",
        }

        # Ask about Ollama
        print_ollama_info()

        ollama_installed = check_ollama_installed()
        ollama_running = check_ollama_running() if ollama_installed else False

        if ollama_installed:
            if ollama_running:
                print(f"✅ {t('ollama_installed')}")
                models = get_ollama_models()
                if models:
                    print(f"{t('ollama_available_models')} {', '.join(models)}")
            else:
                print(f"⚠️  {t('ollama_installed_not_running')}")
                print(f"   {t('start_ollama')}")
        else:
            print(f"❌ {t('ollama_not_installed')}")

        use_ollama = questionary.confirm(
            t("use_ollama"),
            default=ollama_installed and ollama_running,
            style=CUSTOM_STYLE,
        ).ask()

        if use_ollama:
            config["prompt_injection"]["layers"]["llm"] = {"enabled": True}

            # Ask about deployment mode
            deployment_mode = questionary.select(
                t("deployment_mode"),
                choices=[
                    questionary.Choice(t("local_mode"), value="local"),
                    questionary.Choice(t("vpc_mode"), value="vpc"),
                    questionary.Choice(t("external_mode"), value="external"),
                ],
                style=CUSTOM_STYLE,
            ).ask()

            config["ollama"]["mode"] = deployment_mode

            if deployment_mode == "local":
                host = questionary.text(
                    t("ollama_host"),
                    default="localhost",
                    style=CUSTOM_STYLE,
                ).ask()
                port = questionary.text(
                    t("ollama_port"),
                    default="11434",
                    style=CUSTOM_STYLE,
                ).ask()

                config["ollama"]["local"] = {
                    "host": host,
                    "port": int(port),
                    "timeout": 30,
                }

                if ollama_running:
                    models = get_ollama_models()
                    if models:
                        model = questionary.select(
                            t("select_model"),
                            choices=models + [t("other_model")],
                            style=CUSTOM_STYLE,
                        ).ask()
                        if model != t("other_model"):
                            config["ollama"]["model"] = model
                        else:
                            model = questionary.text(
                                t("model_name"),
                                default="mistral:7b",
                                style=CUSTOM_STYLE,
                            ).ask()
                            config["ollama"]["model"] = model
                    else:
                        config["ollama"]["model"] = "mistral:7b"
                else:
                    config["ollama"]["model"] = "mistral:7b"

            elif deployment_mode == "vpc":
                print(f"\n{t('vpc_config')}")
                load_balancer = questionary.text(
                    t("load_balancer"),
                    default="http://ollama-lb.internal:11434",
                    style=CUSTOM_STYLE,
                ).ask()

                instances = []
                add_instances = questionary.confirm(
                    t("add_instances"),
                    default=True,
                    style=CUSTOM_STYLE,
                ).ask()

                if add_instances:
                    while True:
                        instance = questionary.text(
                            t("instance_prompt").format(num=len(instances) + 1),
                            default=(
                                f"http://ollama-{len(instances) + 1}.internal:11434"
                                if len(instances) == 0
                                else ""
                            ),
                            style=CUSTOM_STYLE,
                        ).ask()

                        if not instance:
                            break
                        instances.append(instance)

                        if not questionary.confirm(
                            t("add_another"),
                            default=False,
                            style=CUSTOM_STYLE,
                        ).ask():
                            break

                config["ollama"]["vpc"] = {
                    "load_balancer": load_balancer,
                    "instances": instances,
                    "strategy": "round_robin",
                    "health_check_interval": 60,
                }
                config["ollama"]["model"] = "mistral:7b"

            else:  # external
                endpoint = questionary.text(
                    t("api_endpoint"),
                    default="https://ollama-api.example.com",
                    style=CUSTOM_STYLE,
                ).ask()

                config["ollama"]["external"] = {
                    "endpoint": endpoint,
                    "timeout": 30,
                }
                config["ollama"]["model"] = "mistral:7b"

                # API key for external service
                if questionary.confirm(
                    t("require_api_key"),
                    default=True,
                    style=CUSTOM_STYLE,
                ).ask():
                    env_var_name = questionary.text(
                        t("api_key_env_var"),
                        default="SENTINELLM_OLLAMA_API_KEY",
                        style=CUSTOM_STYLE,
                    ).ask()
                    # Store only the env var *name*, never the actual key value.
                    # The key must be set in the environment before running SentineLLM:
                    #   export SENTINELLM_OLLAMA_API_KEY=<your-key>
                    config["ollama"]["external"]["api_key_env"] = env_var_name
                    print(t("api_key_env_warning").format(env_var_name))

            # Circuit breaker configuration
            print(f"\n{t('circuit_breaker_title')}")
            config["ollama"]["circuit_breaker"] = {
                "failure_threshold": int(
                    questionary.text(
                        t("failure_threshold"),
                        default="3",
                        style=CUSTOM_STYLE,
                    ).ask()
                ),
                "recovery_timeout": int(
                    questionary.text(
                        t("recovery_timeout"),
                        default="60",
                        style=CUSTOM_STYLE,
                    ).ask()
                ),
            }

            # Fallback strategy
            fallback_mode = questionary.select(
                t("fallback_strategy"),
                choices=[
                    questionary.Choice(t("fallback_regex"), value="regex_only"),
                    questionary.Choice(t("fallback_block"), value="block_all"),
                    questionary.Choice(t("fallback_allow"), value="allow_all"),
                ],
                style=CUSTOM_STYLE,
            ).ask()

            config["ollama"]["fallback"] = {"mode": fallback_mode}

        else:
            # No Ollama, only regex
            config["prompt_injection"]["layers"]["llm"] = {"enabled": False}

    else:
        config["prompt_injection"]["enabled"] = False

    # 2. Secret detection
    if questionary.confirm(
        t("enable_secrets"),
        default=True,
        style=CUSTOM_STYLE,
    ).ask():
        config["secret_detection"]["enabled"] = True
        config["secret_detection"]["patterns"] = ["aws", "github", "jwt", "generic"]
    else:
        config["secret_detection"]["enabled"] = False

    # 3. Save configuration
    print(f"\n{t('saving')}")

    config_path = Path("config/security_config.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)

    print(f"✅ {t('config_saved')} {config_path}")

    # 4. Summary
    print("\n" + "=" * 70)
    print(t("summary_title"))
    print("=" * 70)
    print(f"✓ {t('prompt_injection_status')} {config['prompt_injection']['enabled']}")
    if config["prompt_injection"]["enabled"]:
        print(f"  {t('regex_layer')} {config['prompt_injection']['layers']['regex']['enabled']}")
        print(
            f"  {t('llm_layer')} {config['prompt_injection']['layers'].get('llm', {}).get('enabled', False)}"
        )
        if config["prompt_injection"]["layers"].get("llm", {}).get("enabled"):
            print(f"  {t('deployment_mode_label')} {config['ollama'].get('mode', 'local')}")
    # config may be tainted in CodeQL's analysis because it stores api_key_env
    # (the Ollama API key env var name), but this field only accesses a boolean.
    # fmt: off
    print(f"✓ {t('secrets_status')} {config['secret_detection']['enabled']}")  # lgtm[py/clear-text-logging-sensitive-data]
    # fmt: on

    print(f"\n{t('ready')}")
    print("   python examples/interactive_demo.py")
    print(f"\n{t('reconfigure_anytime')}")
    print("   python -m src.cli.config_wizard")

    return config


if __name__ == "__main__":
    run_config_wizard()
