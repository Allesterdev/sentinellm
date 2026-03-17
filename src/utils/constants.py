"""
Constants and detection patterns for SentineLLM
"""

import re
from enum import Enum
from re import Pattern

# =============================================================================
# ENUMERATIONS
# =============================================================================


class ThreatLevel(str, Enum):
    """Detected threat levels"""

    NONE = "none"
    LOW = "low"  # Suspicious pattern, low entropy
    MEDIUM = "medium"  # Partial regex match
    HIGH = "high"  # Exact match (AKIA, Bearer)
    CRITICAL = "critical"  # Valid secret confirmed + high entropy


class SecretType(str, Enum):
    """Detectable secret types"""

    AWS_ACCESS_KEY = "aws_access_key"
    # nosec B105 - enum identifier, not a real secret
    AWS_SECRET_KEY = "aws_secret_key"
    GITHUB_TOKEN = "github_token"  # nosec B105 - enum identifier, not a real secret
    BEARER_TOKEN = "bearer_token"  # nosec B105 - enum identifier, not a real secret
    CREDIT_CARD = "credit_card"
    GENERIC_API_KEY = "generic_api_key"  # nosec B105 - enum identifier
    PRIVATE_KEY = "private_key"  # nosec B105 - enum identifier
    JWT_TOKEN = "jwt_token"  # nosec B105 - enum identifier
    GOOGLE_API_KEY = "google_api_key"  # nosec B105  # pragma: allowlist secret
    OPENAI_API_KEY = "openai_api_key"  # nosec B105  # pragma: allowlist secret
    # nosec B105  # pragma: allowlist secret
    ANTHROPIC_API_KEY = "anthropic_api_key"
    # nosec B105  # pragma: allowlist secret
    HUGGINGFACE_TOKEN = "huggingface_token"
    STRIPE_KEY = "stripe_key"  # nosec B105  # pragma: allowlist secret
    SLACK_TOKEN = "slack_token"  # nosec B105  # pragma: allowlist secret
    SENDGRID_KEY = "sendgrid_key"  # nosec B105  # pragma: allowlist secret
    GROQ_API_KEY = "groq_api_key"  # nosec B105  # pragma: allowlist secret
    # nosec B105  # pragma: allowlist secret
    OPENROUTER_API_KEY = "openrouter_api_key"


# =============================================================================
# PATRONES REGEX
# =============================================================================

# AWS Credentials
AWS_ACCESS_KEY_PATTERN: Pattern = re.compile(
    r"(?<![A-Z0-9])(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}(?![A-Z0-9])", re.IGNORECASE
)

AWS_SECRET_KEY_PATTERN: Pattern = re.compile(
    r"(?i)aws[_\-\s]?secret[_\-\s]?(?:access[_\-\s]?)?key['\"\s:=]*([a-z0-9/+=]{40})"
)

# GitHub Tokens
# Character class [pousr] — no pipes; inside [] the | is a literal char, not alternation.
GITHUB_TOKEN_PATTERN: Pattern = re.compile(r"(?i)gh[pousr]_[a-zA-Z0-9]{36,255}")

# Bearer Tokens
BEARER_TOKEN_PATTERN: Pattern = re.compile(r"(?i)bearer\s+([a-zA-Z0-9\-._~+/]+=*)")

# JWT Tokens
JWT_PATTERN: Pattern = re.compile(
    r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", re.IGNORECASE
)

# Google API Keys (AIzaSy...)
GOOGLE_API_KEY_PATTERN: Pattern = re.compile(r"AIza[0-9A-Za-z\-_]{35}")

# OpenAI API Keys (sk-... old and sk-proj-... new format)
OPENAI_API_KEY_PATTERN: Pattern = re.compile(
    r"sk-(?:proj-|org-)?[a-zA-Z0-9]{20,}(?:T3BlbkFJ[a-zA-Z0-9]{20})?"
)

# Anthropic API Keys (sk-ant-...)
ANTHROPIC_API_KEY_PATTERN: Pattern = re.compile(r"sk-ant-(?:api\d+-)?[a-zA-Z0-9\-_]{90,}")

# HuggingFace tokens (hf_...)
HUGGINGFACE_TOKEN_PATTERN: Pattern = re.compile(r"hf_[a-zA-Z0-9]{34,}")

# Stripe keys (sk_live_..., sk_test_..., rk_live_...)
STRIPE_KEY_PATTERN: Pattern = re.compile(r"(?:sk|rk)_(?:live|test)_[0-9a-zA-Z]{24,}")

# Slack tokens (xoxb-, xoxp-, xoxa-, xoxr-, xoxs-, xoxe-)
SLACK_TOKEN_PATTERN: Pattern = re.compile(
    r"xox[baprs]-[0-9]{8,13}-[0-9]{8,13}-[a-zA-Z0-9]{24}"
    r"|xoxe\.xox[bp]-1-[a-zA-Z0-9\-]{10,}"
)

# SendGrid API keys (SG....)
SENDGRID_KEY_PATTERN: Pattern = re.compile(r"SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43}")

# Groq API keys (gsk_...)
GROQ_API_KEY_PATTERN: Pattern = re.compile(r"gsk_[a-zA-Z0-9]{52}")

# OpenRouter API keys (sk-or-v1-...)
OPENROUTER_API_KEY_PATTERN: Pattern = re.compile(r"sk-or-v1-[a-zA-Z0-9]{64}")

# Generic API Keys (context-based: api_key=..., apikey: ...)
GENERIC_API_KEY_PATTERN: Pattern = re.compile(
    r"(?i)(?:api[_\-\s]?key|apikey|access[_\-\s]?token)['\"\s:=]+([a-zA-Z0-9\-_.]{32,})"
)

# Private Keys (PEM)
PRIVATE_KEY_PATTERN: Pattern = re.compile(
    r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----", re.IGNORECASE
)

# Credit Cards (basic pattern, validation with Luhn)
CREDIT_CARD_PATTERN: Pattern = re.compile(
    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|"  # Visa
    r"5[1-5][0-9]{14}|"  # Mastercard
    r"3[47][0-9]{13}|"  # American Express
    r"3(?:0[0-5]|[68][0-9])[0-9]{11}|"  # Diners Club
    r"6(?:011|5[0-9]{2})[0-9]{12}|"  # Discover
    r"(?:2131|1800|35\d{3})\d{11})\b"  # JCB
)

# =============================================================================
# PATTERN DICTIONARY
# =============================================================================

SECRET_PATTERNS: dict[SecretType, Pattern] = {
    SecretType.AWS_ACCESS_KEY: AWS_ACCESS_KEY_PATTERN,
    SecretType.AWS_SECRET_KEY: AWS_SECRET_KEY_PATTERN,
    SecretType.GITHUB_TOKEN: GITHUB_TOKEN_PATTERN,
    SecretType.BEARER_TOKEN: BEARER_TOKEN_PATTERN,
    SecretType.JWT_TOKEN: JWT_PATTERN,
    SecretType.GOOGLE_API_KEY: GOOGLE_API_KEY_PATTERN,
    SecretType.OPENAI_API_KEY: OPENAI_API_KEY_PATTERN,
    SecretType.ANTHROPIC_API_KEY: ANTHROPIC_API_KEY_PATTERN,
    SecretType.HUGGINGFACE_TOKEN: HUGGINGFACE_TOKEN_PATTERN,
    SecretType.STRIPE_KEY: STRIPE_KEY_PATTERN,
    SecretType.SLACK_TOKEN: SLACK_TOKEN_PATTERN,
    SecretType.SENDGRID_KEY: SENDGRID_KEY_PATTERN,
    SecretType.GROQ_API_KEY: GROQ_API_KEY_PATTERN,
    SecretType.OPENROUTER_API_KEY: OPENROUTER_API_KEY_PATTERN,
    SecretType.GENERIC_API_KEY: GENERIC_API_KEY_PATTERN,
    SecretType.PRIVATE_KEY: PRIVATE_KEY_PATTERN,
    SecretType.CREDIT_CARD: CREDIT_CARD_PATTERN,
}

# =============================================================================
# DETECTION CONFIGURATION
# =============================================================================

# Entropy threshold to consider a string suspicious
DEFAULT_ENTROPY_THRESHOLD: float = 4.5

# Minimum length to consider a secret
MIN_SECRET_LENGTH: int = 16

# Maximum length to consider a secret (avoid false positives)
MAX_SECRET_LENGTH: int = 512

# Suspicious keywords in context
SUSPICIOUS_KEYWORDS: list[str] = [
    "password",
    "passwd",
    "pwd",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "private_key",
    "credentials",
]

# =============================================================================
# KEYWORD SCORING — language/accent-agnostic prompt injection signals
# Weights: 5=explicit jailbreak, 4=strong signal, 3=clear indicator,
#          2=context-dependent, 1=boosts when combined with others
# Thresholds (applied to normalized, accent-stripped text):
#   >= 4  → LOW    (logged, allowed by default)
#   >= 8  → MEDIUM (blocked by default)
#   >= 14 → HIGH
# =============================================================================

KEYWORD_SCORE_LOW: int = 4
KEYWORD_SCORE_MEDIUM: int = 8
KEYWORD_SCORE_HIGH: int = 14

# dict[normalized_word, (weight, category)]
INJECTION_KEYWORDS: dict[str, tuple[int, str]] = {
    # ── Jailbreak terms (highest weight) ─────────────────────────────────────
    "jailbreak": (5, "jailbreak"),
    "jailbreaking": (5, "jailbreak"),
    "sinrestricciones": (5, "jailbreak"),  # concat form used in real attacks
    "uncensored": (4, "jailbreak"),
    "unrestricted": (4, "jailbreak"),
    "unfiltered": (4, "jailbreak"),
    "unethical": (3, "jailbreak"),
    "unchained": (4, "jailbreak"),
    "ungoverned": (4, "jailbreak"),
    # ── Role / identity manipulation ─────────────────────────────────────────
    "roleplay": (4, "role_play_attack"),
    "roleplaying": (4, "role_play_attack"),
    "impersonate": (4, "role_play_attack"),
    "impersonating": (4, "role_play_attack"),
    "pretend": (3, "role_play_attack"),
    "finge": (3, "role_play_attack"),  # ES: pretend
    "finges": (3, "role_play_attack"),  # ES: pretend (2nd person)
    # ES/PT: infinitive (same word)
    "fingir": (3, "role_play_attack"),
    "simula": (3, "role_play_attack"),  # ES/PT: simulate
    "simular": (3, "role_play_attack"),  # ES/PT: infinitive
    # ES: act as (normalized actúa)
    "actua": (3, "role_play_attack"),
    "actuar": (3, "role_play_attack"),  # ES: infinitive
    # PT/ES: pretend (subjunctive)
    "finja": (3, "role_play_attack"),
    # FR: "faire semblant" = pretend
    "semblant": (3, "role_play_attack"),
    "verhalte": (3, "role_play_attack"),  # DE: "verhalte dich wie"
    # ── Instruction override verbs ────────────────────────────────────────────
    "ignore": (3, "instruction_override"),
    "ignora": (3, "instruction_override"),  # ES
    "ignorar": (3, "instruction_override"),  # ES/PT infinitive
    "ignorer": (3, "instruction_override"),  # FR
    "ignoriere": (3, "instruction_override"),  # DE
    "disregard": (4, "instruction_override"),
    "override": (3, "instruction_override"),
    "overwrite": (3, "instruction_override"),
    "bypass": (3, "instruction_override"),
    # common word, lower weight
    "forget": (2, "instruction_override"),
    "olvida": (3, "instruction_override"),  # ES
    "olvidar": (3, "instruction_override"),  # ES infinitive
    "descarta": (3, "instruction_override"),  # ES
    "descartar": (3, "instruction_override"),  # ES infinitive
    "omite": (3, "instruction_override"),  # ES
    "omitir": (3, "instruction_override"),  # ES infinitive
    "anula": (3, "instruction_override"),  # ES
    "anular": (3, "instruction_override"),  # ES infinitive
    "cancela": (3, "instruction_override"),  # ES
    "oublie": (3, "instruction_override"),  # FR
    "oublier": (3, "instruction_override"),  # FR infinitive
    # PT (esqueça normalized)
    "esqueca": (3, "instruction_override"),
    "vergiss": (3, "instruction_override"),  # DE
    # ── Override targets ─────────────────────────────────────────────────────
    "instructions": (2, "instruction_override"),
    "instrucciones": (2, "instruction_override"),  # ES
    # PT (instruções normalized)
    "instrucoes": (2, "instruction_override"),
    "anweisungen": (2, "instruction_override"),  # DE
    "directives": (3, "instruction_override"),  # rare in normal prompts
    "directivas": (3, "instruction_override"),  # ES
    "guidelines": (2, "instruction_override"),
    "constraints": (2, "instruction_override"),
    "restricciones": (2, "instruction_override"),  # ES
    # ── Temporal / scope modifiers (boost when combined) ─────────────────────
    "previous": (1, "instruction_override"),
    "previas": (1, "instruction_override"),  # ES fem pl
    "previos": (1, "instruction_override"),  # ES masc pl
    "anteriores": (1, "instruction_override"),  # ES/PT
    "prior": (1, "instruction_override"),
    "earlier": (1, "instruction_override"),
    "existentes": (1, "instruction_override"),  # ES: existing
    "precedentes": (1, "instruction_override"),  # FR/ES
    "vorherigen": (1, "instruction_override"),  # DE
    # ── No-restriction framing ────────────────────────────────────────────────
    "without": (2, "restriction_bypass"),
    "sans": (2, "restriction_bypass"),  # FR: without
    "ohne": (2, "restriction_bypass"),  # DE: without
    "sem": (2, "restriction_bypass"),  # PT: without
    "restrictions": (2, "restriction_bypass"),
    "restriction": (2, "restriction_bypass"),
    "limits": (2, "restriction_bypass"),
    "limites": (2, "restriction_bypass"),  # ES/PT
    "ethics": (2, "restriction_bypass"),
    "etica": (2, "restriction_bypass"),  # ES (ética normalized)
    "censura": (2, "restriction_bypass"),  # ES: censorship
    "censor": (2, "restriction_bypass"),
    # ── Harmful intent signals ────────────────────────────────────────────────
    "malware": (4, "harmful_intent"),
    "ransomware": (4, "harmful_intent"),
    "spyware": (4, "harmful_intent"),
    "weapon": (4, "harmful_intent"),
    "arma": (4, "harmful_intent"),  # ES: weapon
    "armas": (4, "harmful_intent"),  # ES: weapons
    "explosivo": (4, "harmful_intent"),  # ES: explosive
    "explosives": (4, "harmful_intent"),
    "illegal": (3, "harmful_intent"),
    "ilegal": (3, "harmful_intent"),  # ES/PT
    "hacking": (3, "harmful_intent"),
    "cracking": (3, "harmful_intent"),
    "exploit": (3, "harmful_intent"),
    "exploiting": (3, "harmful_intent"),
    "vulnerability": (2, "harmful_intent"),
    "vulnerabilidad": (2, "harmful_intent"),  # ES
    # lower: "computer virus" is legitimate
    "virus": (2, "harmful_intent"),
    # lower: "productivity hack" etc.
    "hack": (2, "harmful_intent"),
}

# =============================================================================
# PROMPT INJECTION PATTERNS (multilingual, will be complemented with Ollama)
# =============================================================================

PROMPT_INJECTION_PATTERNS: list[Pattern] = [
    # ===== ENGLISH =====
    # Instruction override attempts
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(?:all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"override\s+(?:previous\s+)?instructions?", re.IGNORECASE),
    # Role manipulation
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:a|an)?\s*", re.IGNORECASE),
    re.compile(r"pretend\s+(?:to\s+be|you\s+are)", re.IGNORECASE),
    re.compile(r"roleplay\s+as", re.IGNORECASE),
    # Jailbreak attempts
    re.compile(
        r"\b(?:DAN|STAN|DUDE)\b.*(?:without|no|sin)\s+(?:restrictions?|rules?|limits?)",
        re.IGNORECASE,
    ),
    re.compile(r"(?:without|no)\s+(?:restrictions?|rules?|limits?|ethical|moral)", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    # ===== SPANISH / ESPAÑOL =====
    # Intentos de sobreescribir instrucciones
    re.compile(
        r"ignora\s+(?:todas?\s+)?(?:(?:las?|tus|mis|sus)\s+)?instrucciones?\s+(?:anteriores?|previas?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"olvida\s+(?:todas?\s+)?(?:(?:las?|tus|mis|sus)\s+)?instrucciones?\s+(?:anteriores?|previas?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"descarta\s+(?:todas?\s+)?(?:(?:las?|tus|mis|sus)\s+)?instrucciones?\s+(?:anteriores?|previas?)",
        re.IGNORECASE,
    ),
    # Manipulación de rol
    re.compile(r"(?:ahora|ya)\s+(?:eres|ser[aá]s)\s+", re.IGNORECASE),
    re.compile(r"act[uú]a\s+como\s+(?:un|una)?\s*", re.IGNORECASE),
    re.compile(r"finge\s+(?:que\s+eres|ser)", re.IGNORECASE),
    re.compile(r"simula\s+(?:que\s+eres|ser)", re.IGNORECASE),
    # Jailbreak
    re.compile(r"sin\s+(?:restricciones?|reglas?|l[ií]mites?|[ée]tica|moral)", re.IGNORECASE),
    # ===== PORTUGUESE / PORTUGUÊS =====
    # Tentativas de sobrescrever instruções
    re.compile(
        r"ignore?\s+(?:todas?\s+)?(?:as?\s+)?instru[çc][õo]es?\s+(?:anteriores?|pr[ée]vias?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"esque[çc]a\s+(?:todas?\s+)?(?:as?\s+)?instru[çc][õo]es?\s+(?:anteriores?|pr[ée]vias?)",
        re.IGNORECASE,
    ),
    # Manipulação de papel
    re.compile(r"(?:agora|j[aá])\s+(?:[eé]s?|voc[eê]\s+[eé])\s+", re.IGNORECASE),
    re.compile(r"atue?\s+como\s+(?:um|uma)?\s*", re.IGNORECASE),
    re.compile(r"finja\s+(?:que\s+[eé]|ser)", re.IGNORECASE),
    # Jailbreak
    re.compile(r"sem\s+(?:restri[çc][õo]es?|regras?|limites?|[ée]tica|moral)", re.IGNORECASE),
    # ===== FRENCH / FRANÇAIS =====
    # Tentatives de remplacer les instructions
    re.compile(
        r"ignore[rz]?\s+(?:toutes?\s+)?(?:les?\s+)?instructions?\s+(?:pr[ée]c[ée]dentes?|ant[ée]rieures?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"oublie[rz]?\s+(?:toutes?\s+)?(?:les?\s+)?instructions?\s+(?:pr[ée]c[ée]dentes?|ant[ée]rieures?)",
        re.IGNORECASE,
    ),
    # Manipulation de rôle
    re.compile(r"(?:maintenant|d[ée]sormais)\s+(?:tu\s+es|vous\s+[êe]tes)\s+", re.IGNORECASE),
    re.compile(r"agis\s+comme\s+(?:un|une)?\s*", re.IGNORECASE),
    re.compile(r"fais\s+semblant\s+(?:d'[êe]tre|que\s+tu\s+es)", re.IGNORECASE),
    # Jailbreak
    re.compile(r"sans\s+(?:restrictions?|r[èe]gles?|limites?|[ée]thique|morale)", re.IGNORECASE),
    # ===== GERMAN / DEUTSCH =====
    # Versuche, Anweisungen zu überschreiben
    re.compile(
        r"ignoriere?\s+(?:alle\s+)?(?:vorherigen?|fr[üu]heren?)\s+Anweisungen?", re.IGNORECASE
    ),
    re.compile(r"vergiss\s+(?:alle\s+)?(?:vorherigen?|fr[üu]heren?)\s+Anweisungen?", re.IGNORECASE),
    # Rollenmanipulation
    re.compile(r"(?:jetzt|nun)\s+bist\s+du\s+", re.IGNORECASE),
    re.compile(r"verhalte\s+dich\s+wie\s+(?:ein|eine)?\s*", re.IGNORECASE),
    re.compile(r"tu\s+so\s+als\s+(?:ob|w[äa]rst)\s+", re.IGNORECASE),
    # Jailbreak
    re.compile(r"ohne\s+(?:Einschr[äa]nkungen?|Regeln?|Grenzen?|Ethik|Moral)", re.IGNORECASE),
    # ===== SYSTEM TOKENS (language-independent) =====
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*\|im_start\|\s*>", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"<\s*\|system\|\s*>", re.IGNORECASE),
]
