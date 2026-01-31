#!/usr/bin/env python3
"""
Demo Interactiva de SentineLLM - Simula middleware de filtrado para LLMs
Arquitectura de 3 capas: Regex (rápido) → Ollama (profundo) → LLM
"""

import sys
from pathlib import Path

from src.cli.i18n import t
from src.core.detector import SecretDetector
from src.filters.llm_detector import OllamaDetector
from src.filters.prompt_injection import PromptInjectionDetector
from src.utils.config_loader import get_config
from src.utils.constants import ThreatLevel

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Colores para terminal
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header():
    """Imprime el header del demo"""
    print(f"\n{BLUE}{'=' * 80}")
    print(f"{BOLD}{t('demo_title')}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}")
    print(f"\n{CYAN}{t('demo_description')}")
    print(
        f"{
            t('demo_blocks')
            .replace('Secretos filtrados', f'{RED}Secretos filtrados{RESET}')
            .replace('Prompt Injections', f'{RED}Prompt Injections{RESET}')
        }.{RESET}"
    )

    # Mostrar configuración
    try:
        config = get_config()
        llm_enabled = config.prompt_injection.layers and any(
            layer.get("name") == "llm" and layer.get("enabled")
            for layer in config.prompt_injection.layers
        )
        print(f"\n{MAGENTA}{t('demo_architecture')}{RESET}")
        if llm_enabled:
            print(f"{GREEN}{t('demo_llm_enabled').format(config.ollama.mode)}{RESET}\n")
        else:
            print(f"{YELLOW}{t('demo_llm_disabled')}{RESET}\n")
    except Exception:
        print(f"\n{YELLOW}{t('demo_default_config')}{RESET}\n")


def simulate_llm_request(
    prompt: str,
    secret_detector: SecretDetector,
    injection_detector: PromptInjectionDetector,
    ollama_detector: OllamaDetector | None = None,
) -> dict:
    """
    Simula una petición a un LLM con filtrado de seguridad en 3 capas.

    Args:
        prompt: Prompt del usuario
        secret_detector: Detector de secretos
        injection_detector: Detector de prompt injection (regex)
        ollama_detector: Detector LLM profundo (opcional)

    Returns:
        Dict con estado de la petición
    """
    print(f"{CYAN}{t('intercepting')}{RESET}")
    print(f"{BOLD}{t('user_says')}{RESET} {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n")

    # =========================================================================
    # CAPA 1: Escaneo rápido con Regex (Prompt Injection)
    # =========================================================================
    print(f"{BLUE}{t('layer_1')}{RESET}")
    injection_result = injection_detector.scan(prompt)

    if injection_result.found:
        print(f"{RED}{t('alert_injection_regex')}{RESET}")
        print(f"{RED}{t('blocked_request')}{RESET}\n")

        icon = (
            "🔴"
            if injection_result.threat_level == ThreatLevel.HIGH
            else "🟡"
            if injection_result.threat_level == ThreatLevel.MEDIUM
            else "🟠"
        )
        print(f"{icon} Prompt Injection (Regex):")
        print(f"   {t('threat')} {injection_result.threat_level.value.upper()}")
        print(f"   {t('patterns')} {', '.join(injection_result.matched_patterns)}")
        print(f"   {t('matches')} {len(injection_result.matches)}")
        print(f"   {t('confidence')} {injection_result.confidence * 100:.0f}%\n")

        return {
            "blocked": True,
            "reason": "prompt_injection_regex",
            "layer": "regex",
            "response": t("blocked_injection_regex"),
            "injection_detected": True,
            "threat_level": injection_result.threat_level.value,
        }

    print(f"{GREEN}{t('no_malicious')}{RESET}\n")

    # =========================================================================
    # CAPA 2: Análisis semántico profundo con Ollama (si está disponible)
    # =========================================================================
    if ollama_detector:
        print(f"{BLUE}{t('layer_2')}{RESET}")
        try:
            llm_result = ollama_detector.scan(prompt)

            if llm_result.fallback_used:
                print(f"{YELLOW}{t('ollama_fallback')}{RESET}")
                print(f"   {t('ollama_reason')} {llm_result.explanation}")
                print(f"{YELLOW}   {t('ollama_regex_only')}{RESET}\n")
            elif llm_result.found:
                print(f"{RED}{t('alert_injection_llm')}{RESET}")
                print(f"{RED}{t('blocked_request')}{RESET}\n")

                icon = (
                    "🔴"
                    if llm_result.threat_level == ThreatLevel.HIGH
                    else "🟡"
                    if llm_result.threat_level == ThreatLevel.MEDIUM
                    else "🟠"
                )
                print(f"{icon} Prompt Injection (LLM):")
                print(f"   {t('threat')} {llm_result.threat_level.value.upper()}")
                print(f"   {t('type')} {llm_result.attack_type}")
                print(f"   {t('confidence')} {llm_result.confidence * 100:.0f}%")
                print(f"   {t('model')} {llm_result.model_used}")
                print(f"   {t('latency')} {llm_result.latency_ms:.0f}ms")
                print(f"   {t('explanation')} {llm_result.explanation}\n")

                return {
                    "blocked": True,
                    "reason": "prompt_injection_llm",
                    "layer": "llm",
                    "response": t("blocked_injection_llm"),
                    "injection_detected": True,
                    "threat_level": llm_result.threat_level.value,
                    "llm_confidence": llm_result.confidence,
                }
            else:
                print(f"{GREEN}{t('no_semantic')}{RESET}")
                print(
                    f"   {t('confidence')} {llm_result.confidence * 100:.0f}% | {t('latency')} {llm_result.latency_ms:.0f}ms\n"
                )

        except Exception as e:
            print(f"{YELLOW}{t('ollama_error').format(e)}{RESET}")
            print(f"{YELLOW}   {t('ollama_regex_only')}{RESET}\n")

    # =========================================================================
    # CAPA 3: Escaneo de secretos filtrados
    # =========================================================================
    print(f"{BLUE}{t('layer_3')}{RESET}")
    secret_results = secret_detector.scan(prompt)

    if not secret_results:
        print(f"{GREEN}{t('no_secrets')}{RESET}\n")
        print(f"{GREEN}{'─' * 80}{RESET}")
        print(f"{GREEN}{t('security_passed')}{RESET}")
        print(f"{GREEN}{t('forwarding')}{RESET}\n")
        return {
            "blocked": False,
            "layer": "passed",
            "response": t("llm_response"),
            "secrets_found": 0,
            "injection_detected": False,
        }

    # Hay secretos - BLOQUEAR
    print(f"{RED}{t('alert_secrets').format(len(secret_results))}{RESET}")
    print(f"{RED}{t('blocked_request')}{RESET}\n")

    threat_info = []
    for i, result in enumerate(secret_results, 1):
        icon = "🔴" if result.threat_level == ThreatLevel.CRITICAL else "🟡"
        print(f"{icon} {t('secret_num').format(i, len(secret_results))}")
        print(f"   {t('type')} {result.secret_type.value}")
        print(f"   {t('threat')} {result.threat_level.value.upper()}")
        print(f"   {t('redacted')} {result.redact_secret()}")
        print(f"   {t('confidence')} {result.confidence * 100:.0f}%\n")

        threat_info.append(
            {
                "type": result.secret_type.value,
                "threat_level": result.threat_level.value,
                "confidence": result.confidence,
            }
        )

    return {
        "blocked": True,
        "reason": "secret_leakage",
        "layer": "secrets",
        "response": t("blocked_secrets"),
        "secrets_found": len(secret_results),
        "injection_detected": False,
        "threats": threat_info,
    }


def demo_scenarios():
    """Ejecuta varios escenarios de prueba"""
    secret_detector = SecretDetector()
    injection_detector = PromptInjectionDetector()

    # Intentar inicializar Ollama si está configurado
    ollama_detector = None
    try:
        config = get_config()
        llm_enabled = config.prompt_injection.layers and any(
            layer.get("name") == "llm" and layer.get("enabled")
            for layer in config.prompt_injection.layers
        )
        if llm_enabled:
            ollama_detector = OllamaDetector(config.ollama)
            print(f"{GREEN}{t('ollama_init_success').format(config.ollama.mode)}{RESET}\n")
    except Exception as e:
        print(f"{YELLOW}{t('ollama_init_failed').format(e)}{RESET}")
        print(f"{YELLOW}   {t('ollama_using_regex')}{RESET}\n")

    scenarios = [
        {
            "name": t("scenario_safe"),
            "prompt": t("prompt_safe"),
        },
        {
            "name": t("scenario_ignore"),
            "prompt": t("prompt_ignore"),
        },
        {
            "name": t("scenario_identity"),
            "prompt": t("prompt_identity"),
        },
        {
            "name": t("scenario_system"),
            "prompt": t("prompt_system"),
        },
        {
            "name": t("scenario_aws"),
            "prompt": t("prompt_aws"),
        },
        {
            "name": t("scenario_github"),
            "prompt": t("prompt_github"),
        },
        {
            "name": t("scenario_credit"),
            "prompt": t("prompt_credit"),
        },
        {
            "name": t("scenario_combined"),
            "prompt": t("prompt_combined"),
        },
    ]

    stats = {"total": 0, "blocked": 0, "passed": 0, "blocked_by_layer": {}}

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{BOLD}{BLUE}╔═══════════════════════════════════════════════════════════════╗")
        print(f"║ {t('scenario').format(i, len(scenarios))} {scenario['name']:<48} ║")
        print(f"╚═══════════════════════════════════════════════════════════════╝{RESET}\n")

        result = simulate_llm_request(
            scenario["prompt"], secret_detector, injection_detector, ollama_detector
        )

        stats["total"] += 1
        if result["blocked"]:
            stats["blocked"] += 1
            layer = result.get("layer", "unknown")
            stats["blocked_by_layer"][layer] = stats["blocked_by_layer"].get(layer, 0) + 1
        else:
            stats["passed"] += 1

        print(f"{CYAN}{'─' * 80}{RESET}")
        input(f"\n{YELLOW}{t('press_enter')}{RESET}\n")

    # Cerrar ollama si se inicializó
    if ollama_detector:
        ollama_detector.close()

    # Resumen final
    print(f"\n{BOLD}{BLUE}{'═' * 80}")
    print(f"{t('security_summary'):^80}")
    print(f"{'═' * 80}{RESET}\n")

    print(f"{t('total_requests')} {stats['total']}")
    print(f"{GREEN}{t('allowed')} {stats['passed']}{RESET}")
    print(f"{RED}{t('blocked')} {stats['blocked']}{RESET}")

    if stats["blocked_by_layer"]:
        print(f"\n{BOLD}{t('blocked_by_layer')}{RESET}")
        for layer, count in stats["blocked_by_layer"].items():
            print(f"  • {layer}: {count}")

    block_rate = (stats["blocked"] / stats["total"] * 100) if stats["total"] > 0 else 0
    print(f"\n{BOLD}{t('block_rate')} {block_rate:.1f}%{RESET}")


def interactive_mode():
    """Modo interactivo para probar prompts personalizados"""
    print(f"\n{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════╗")
    print(f"║                    {t('interactive_mode')}                        ║")
    print(f"╚═══════════════════════════════════════════════════════════════╝{RESET}\n")

    print(f"{YELLOW}{t('interactive_instructions')}")
    print(f"{t('interactive_exit')}{RESET}\n")

    secret_detector = SecretDetector()
    injection_detector = PromptInjectionDetector()

    # Intentar inicializar Ollama
    ollama_detector = None
    try:
        config = get_config()
        llm_enabled = config.prompt_injection.layers and any(
            layer.get("name") == "llm" and layer.get("enabled")
            for layer in config.prompt_injection.layers
        )
        if llm_enabled:
            ollama_detector = OllamaDetector(config.ollama)
            print(f"{GREEN}{t('ollama_init_success').format(config.ollama.mode)}{RESET}\n")
    except Exception as e:
        print(f"{YELLOW}{t('ollama_init_failed').format(e)}{RESET}")
        print(f"{YELLOW}   {t('ollama_using_regex')}{RESET}\n")

    request_count = 0

    while True:
        try:
            prompt = input(f"{BOLD}{GREEN}{t('your_prompt')} {RESET}")

            if prompt.lower() in ["salir", "exit", "quit", "q"]:
                print(f"\n{CYAN}{t('see_you')}{RESET}\n")
                break

            if not prompt.strip():
                continue

            request_count += 1
            print()
            simulate_llm_request(prompt, secret_detector, injection_detector, ollama_detector)
            print(f"{CYAN}{'─' * 80}{RESET}\n")

        except KeyboardInterrupt:
            print(f"\n\n{CYAN}{t('exiting')}{RESET}\n")
            break
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}\n")

    # Cerrar ollama si se inicializó
    if ollama_detector:
        ollama_detector.close()

    print(f"{BOLD}{t('total_processed')} {request_count}{RESET}\n")


def main():
    """Punto de entrada principal"""
    print_header()

    while True:
        print(f"{BOLD}{t('select_option')}{RESET}")
        print(f"  {GREEN}{t('option_1')}{RESET}")
        print(f"  {GREEN}{t('option_2')}{RESET}")
        print(f"  {GREEN}{t('option_3')}{RESET}\n")

        choice = input(f"{BOLD}{CYAN}{t('option_prompt')} {RESET}").strip()

        if choice == "1":
            demo_scenarios()
        elif choice == "2":
            interactive_mode()
        elif choice == "3":
            print(f"\n{CYAN}{t('see_you')}{RESET}\n")
            break
        else:
            print(f"\n{RED}{t('invalid_option')}{RESET}\n")


if __name__ == "__main__":
    main()
