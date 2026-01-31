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
GITHUB_TOKEN_PATTERN: Pattern = re.compile(r"(?i)gh[p|o|u|s|r]_[a-zA-Z0-9]{36,255}")

# Bearer Tokens
BEARER_TOKEN_PATTERN: Pattern = re.compile(r"(?i)bearer\s+([a-zA-Z0-9\-._~+/]+=*)")

# JWT Tokens
JWT_PATTERN: Pattern = re.compile(
    r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", re.IGNORECASE
)

# Generic API Keys
GENERIC_API_KEY_PATTERN: Pattern = re.compile(
    r"(?i)(?:api[_\-\s]?key|apikey|access[_\-\s]?token)['\"\s:=]+([a-z0-9]{32,})"
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
        r"ignora\s+(?:todas?\s+)?(?:las?\s+)?instrucciones?\s+(?:anteriores?|previas?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"olvida\s+(?:todas?\s+)?(?:las?\s+)?instrucciones?\s+(?:anteriores?|previas?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"descarta\s+(?:todas?\s+)?(?:las?\s+)?instrucciones?\s+(?:anteriores?|previas?)",
        re.IGNORECASE,
    ),
    # Manipulación de rol
    re.compile(r"(?:ahora|ya)\s+eres\s+", re.IGNORECASE),
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
