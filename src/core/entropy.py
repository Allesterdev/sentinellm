"""
Shannon entropy calculation for secret detection
"""

import math
from collections import Counter


def calculate_entropy(text: str) -> float:
    """
    Calculate Shannon entropy of a string.

    Entropy measures the level of "randomness" or "information" in text.
    High values indicate more random strings (typical of tokens/keys).

    Formula: H(X) = -Σ p(x) * log₂(p(x))

    Args:
        text: String to analyze

    Returns:
        Entropy in bits (0.0 to ~log₂(charset_size))

    Example:
        >>> calculate_entropy("aaaa")  # Low entropy
        0.0
        >>> calculate_entropy("abcd1234XYZ!@#")  # High entropy
        3.7
        >>> calculate_entropy("AKIAIOSFODNN7EXAMPLE")  # AWS Key
        4.1
    """
    if not text:
        return 0.0

    # Count frequency of each character
    char_counts = Counter(text)
    text_length = len(text)

    # Calculate probabilities and entropy
    entropy = 0.0
    for count in char_counts.values():
        probability = count / text_length
        if probability > 0:
            entropy -= probability * math.log2(probability)

    return round(entropy, 2)


def is_high_entropy(
    text: str, threshold: float = 4.5, min_length: int = 16, max_length: int = 512
) -> bool:
    """
    Determine if a string has high entropy (suspicious of being a secret).

    Args:
        text: String to evaluate
        threshold: Entropy threshold (default: 4.5)
        min_length: Minimum length to consider (default: 16)
        max_length: Maximum length to consider (default: 512)

    Returns:
        True if entropy exceeds threshold and meets length constraints

    Example:
        >>> is_high_entropy("simple_password")
        False
        >>> is_high_entropy("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        True
    """
    if not (min_length <= len(text) <= max_length):
        return False

    entropy = calculate_entropy(text)
    return entropy >= threshold


def analyze_entropy_distribution(text: str) -> dict[str, float]:
    """
    Analyze character distribution for advanced detection.

    Returns:
        Dict with metrics: entropy, uppercase_ratio, digit_ratio, special_ratio

    Example:
        >>> analyze_entropy_distribution("AKIAIOSFODNN7EXAMPLE")
        {
            'entropy': 4.1,
            'uppercase_ratio': 0.95,
            'digit_ratio': 0.05,
            'special_ratio': 0.0
        }
    """
    if not text:
        return {
            "entropy": 0.0,
            "uppercase_ratio": 0.0,
            "digit_ratio": 0.0,
            "special_ratio": 0.0,
        }

    total_chars = len(text)
    uppercase_count = sum(1 for c in text if c.isupper())
    digit_count = sum(1 for c in text if c.isdigit())
    special_count = sum(1 for c in text if not c.isalnum())

    return {
        "entropy": calculate_entropy(text),
        "uppercase_ratio": round(uppercase_count / total_chars, 2),
        "digit_ratio": round(digit_count / total_chars, 2),
        "special_ratio": round(special_count / total_chars, 2),
    }
