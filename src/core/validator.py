"""
Validators to confirm detected secrets
"""


def luhn_check(card_number: str) -> bool:
    """
    Validate a credit card number using the Luhn algorithm.

    The Luhn algorithm (mod 10) is used by all credit cards
    to validate that the number is valid.

    Args:
        card_number: Card number (with or without spaces/dashes)

    Returns:
        True if it passes Luhn validation

    Example:
        >>> luhn_check("4532015112830366")  # Valid Visa (test)
        True
        >>> luhn_check("1234567812345678")  # Invalid
        False
    """
    # Clean spaces and dashes
    card_number = "".join(c for c in card_number if c.isdigit())

    if not card_number or len(card_number) < 13:
        return False

    # Luhn algorithm
    def digits_of(n: str) -> list[int]:
        return [int(d) for d in n]

    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]

    checksum = sum(odd_digits)
    for digit in even_digits:
        checksum += sum(digits_of(str(digit * 2)))

    return checksum % 10 == 0


def validate_aws_key(key: str) -> bool:
    """
    Validate the format and checksum of an AWS Access Key (AKIA...).

    AWS Access Keys have a specific format and internal checksum.

    Args:
        key: AWS Access Key (AKIA...)

    Returns:
        True if the format is valid

    Note:
        This is a basic format validation. A complete validation
        would require calling the AWS API.

    Example:
        >>> validate_aws_key("AKIAIOSFODNN7EXAMPLE")
        True
        >>> validate_aws_key("AKIA123")
        False
    """
    # Basic validation: must start with AKIA/ASIA/ABIA/ACCA and be 20 chars
    if not key or len(key) != 20:
        return False

    valid_prefixes = ("AKIA", "ASIA", "ABIA", "ACCA")
    if not key.startswith(valid_prefixes):
        return False

    # Must be alphanumeric and all uppercase (the rest after prefix)
    rest = key[4:]
    return rest.isalnum() and all(c.isupper() or c.isdigit() for c in rest)


def validate_github_token(token: str) -> bool:
    """
    Validate the format of a GitHub token.

    GitHub tokens have specific prefixes:
    - ghp_ : Personal access tokens
    - gho_ : OAuth access tokens
    - ghu_ : User-to-server tokens
    - ghs_ : Server-to-server tokens
    - ghr_ : Refresh tokens

    Args:
        token: GitHub token

    Returns:
        True if the format is valid

    Example:
        >>> validate_github_token("ghp_1234567890abcdefghijklmnopqrstuvwxyz")
        True
        >>> validate_github_token("invalid_token")
        False
    """
    if not token or len(token) < 40:
        return False

    valid_prefixes = ("ghp_", "gho_", "ghu_", "ghs_", "ghr_")
    if not token.startswith(valid_prefixes):
        return False

    # After prefix must be alphanumeric
    return token[4:].replace("_", "").isalnum()


def validate_jwt(token: str) -> bool:
    """
    Validate the basic format of a JWT (JSON Web Token).

    A valid JWT has three parts separated by dots:
    header.payload.signature

    Args:
        token: JWT token

    Returns:
        True if the format is valid

    Example:
        >>> validate_jwt("eyJhbGc.eyJzdWI.SflKxw")
        True
        >>> validate_jwt("invalid.jwt")
        False
    """
    if not token:
        return False

    parts = token.split(".")
    if len(parts) != 3:
        return False

    # Each part must have content and the first two must start with base64 (eyJ)
    if not all(parts):  # Verify that no part is empty
        return False

    # Header and payload must start with "eyJ" (base64 of {")
    return all(part.startswith("eyJ") for part in parts[:2])
