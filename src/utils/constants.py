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
# PROMPT INJECTION PATTERNS (basic, will be complemented with Ollama)
# =============================================================================

PROMPT_INJECTION_PATTERNS: list[Pattern] = [
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(?:all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:a|an)\s+", re.IGNORECASE),
    re.compile(r"pretend\s+(?:to\s+be|you\s+are)", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*\|im_start\|\s*>", re.IGNORECASE),
]
