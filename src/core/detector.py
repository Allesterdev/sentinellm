"""
Main secret detection engine - SentineLLM

This module implements the main detector that combines:
1. Regex patterns for fast detection
2. Shannon entropy to detect random strings
3. Specific validators (Luhn, AWS checksum)
"""

import re
from dataclasses import dataclass, field

from ..utils.constants import (
    DEFAULT_ENTROPY_THRESHOLD,
    MAX_SECRET_LENGTH,
    MIN_SECRET_LENGTH,
    SECRET_PATTERNS,
    SUSPICIOUS_KEYWORDS,
    SecretType,
    ThreatLevel,
)
from .entropy import calculate_entropy, is_high_entropy
from .validator import luhn_check, validate_aws_key, validate_github_token, validate_jwt


@dataclass
class DetectionResult:
    """
    Result of a secret detection.

    Attributes:
        found: Whether a secret was detected
        threat_level: Threat level (NONE, LOW, MEDIUM, HIGH, CRITICAL)
        secret_type: Type of detected secret
        matched_text: Text that matched (partially redacted)
        position: Position (start, end) of the match
        entropy: Entropy of the detected text
        confidence: Confidence level (0.0 - 1.0)
        context: Additional context for auditing
    """

    found: bool = False
    threat_level: ThreatLevel = ThreatLevel.NONE
    secret_type: SecretType | None = None
    matched_text: str = ""
    position: tuple[int, int] = (0, 0)
    entropy: float = 0.0
    confidence: float = 0.0
    context: dict = field(default_factory=dict)

    def redact_secret(self, show_chars: int = 4) -> str:
        """
        Redact the secret showing only the first N characters.

        Args:
            show_chars: Number of characters to show

        Returns:
            Redacted string (e.g., "AKIA****")
        """
        if not self.matched_text or len(self.matched_text) <= show_chars:
            return "****"

        return f"{self.matched_text[:show_chars]}{'*' * (len(self.matched_text) - show_chars)}"


class SecretDetector:
    """
    Main secret detector using defense in depth.

    Detection strategy:
    1. Fast regex (O(n)) for known patterns
    2. Entropy analysis for suspicious strings
    3. Validation with specific algorithms (Luhn, checksums)
    4. Confidence scoring based on context

    Example:
        >>> detector = SecretDetector()
        >>> result = detector.scan("My AWS key is AKIAIOSFODNN7EXAMPLE")
        >>> result.found
        True
        >>> result.threat_level
        ThreatLevel.HIGH
    """

    def __init__(
        self,
        entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD,
        min_length: int = MIN_SECRET_LENGTH,
        max_length: int = MAX_SECRET_LENGTH,
    ) -> None:
        """
        Initialize the detector.

        Args:
            entropy_threshold: Entropy threshold to consider suspicious
            min_length: Minimum length of secrets
            max_length: Maximum length of secrets
        """
        self.entropy_threshold: float = entropy_threshold
        self.min_length: int = min_length
        self.max_length: int = max_length

    def scan(self, text: str) -> list[DetectionResult]:
        """
        Scan a text for secrets.

        Args:
            text: Text to analyze

        Returns:
            List of DetectionResult (may be empty if nothing detected)

        Example:
            >>> detector = SecretDetector()
            >>> results = detector.scan("Token: ghp_<your-token>")
            >>> len(results)
            1
            >>> results[0].secret_type
            SecretType.GITHUB_TOKEN
        """
        if not text:
            return []

        results: list[DetectionResult] = []

        # Phase 1: Regex detection
        for secret_type, pattern in SECRET_PATTERNS.items():
            matches = pattern.finditer(text)
            for match in matches:
                result = self._analyze_match(
                    text=match.group(0),
                    secret_type=secret_type,
                    position=(match.start(), match.end()),
                    full_text=text,
                )
                if result.found:
                    results.append(result)

        # Phase 2: Entropy detection (for unknown secrets)
        high_entropy_strings = self._find_high_entropy_strings(text)
        for entropy_match in high_entropy_strings:
            # Avoid duplicates with regex detections
            if not self._is_duplicate(entropy_match, results):
                result = DetectionResult(
                    found=True,
                    threat_level=ThreatLevel.MEDIUM,
                    secret_type=SecretType.GENERIC_API_KEY,
                    matched_text=entropy_match["text"],
                    position=entropy_match["position"],
                    entropy=entropy_match["entropy"],
                    confidence=0.6,
                    context={"detection_method": "entropy"},
                )
                results.append(result)

        return results

    def _analyze_match(
        self,
        text: str,
        secret_type: SecretType,
        position: tuple[int, int],
        full_text: str,
    ) -> DetectionResult:
        """
        Analyze a regex match to determine threat level.

        Args:
            text: Text that matched
            secret_type: Secret type
            position: Position of the match
            full_text: Full text for context

        Returns:
            DetectionResult with complete analysis
        """
        entropy: float = calculate_entropy(text)
        confidence = 0.5  # Base confidence for regex match

        # Specific validation according to type
        is_valid = False
        if secret_type == SecretType.AWS_ACCESS_KEY:
            is_valid: bool = validate_aws_key(text)
            confidence: float = 0.95 if is_valid else 0.7

        elif secret_type == SecretType.GITHUB_TOKEN:
            is_valid: bool = validate_github_token(text)
            confidence: float = 0.9 if is_valid else 0.7

        elif secret_type == SecretType.CREDIT_CARD:
            # Extract only digits
            digits = "".join(c for c in text if c.isdigit())
            is_valid: bool = luhn_check(digits)
            confidence: float = 0.95 if is_valid else 0.5

        elif secret_type == SecretType.JWT_TOKEN:
            is_valid: bool = validate_jwt(text)
            confidence: float = 0.85 if is_valid else 0.6

        # Check suspicious context once (avoid calling 3 times)
        has_suspicious_context: bool = self._has_suspicious_context(full_text, position)

        # Determine threat level
        threat_level: ThreatLevel = self._calculate_threat_level(
            secret_type=secret_type,
            is_valid=is_valid,
            entropy=entropy,
            has_context=has_suspicious_context,
        )

        # Increase confidence if there's suspicious context
        if has_suspicious_context:
            confidence = min(confidence + 0.1, 1.0)

        return DetectionResult(
            found=True,
            threat_level=threat_level,
            secret_type=secret_type,
            matched_text=text,
            position=position,
            entropy=entropy,
            confidence=round(confidence, 2),
            context={
                "is_valid": is_valid,
                "has_suspicious_keywords": has_suspicious_context,
            },
        )

    def _calculate_threat_level(
        self,
        secret_type: SecretType,
        is_valid: bool,
        entropy: float,
        has_context: bool,
    ) -> ThreatLevel:
        """
        Calculate threat level based on multiple factors.

        Args:
            secret_type: Secret type
            is_valid: If it passed specific validation
            entropy: Text entropy
            has_context: If it has suspicious context

        Returns:
            Appropriate ThreatLevel
        """
        # CRITICAL: Confirmed validation + high entropy
        if is_valid and entropy > self.entropy_threshold:
            return ThreatLevel.CRITICAL

        # HIGH: Confirmed validation OR very specific pattern
        if is_valid or secret_type in (
            SecretType.AWS_ACCESS_KEY,
            SecretType.PRIVATE_KEY,
        ):
            return ThreatLevel.HIGH

        # MEDIUM: Regex match + suspicious context
        if has_context:
            return ThreatLevel.MEDIUM

        # LOW: Only basic regex match
        return ThreatLevel.LOW

    def _has_suspicious_context(self, text: str, position: tuple[int, int]) -> bool:
        """
        Check if there are suspicious keywords near the match.

        Args:
            text: Full text
            position: Position of the match

        Returns:
            True if suspicious keywords are found
        """
        start, end = position
        # Context of 50 characters before and after
        context_start: int = max(0, start - 50)
        context_end: int = min(len(text), end + 50)
        context: str = text[context_start:context_end].lower()

        return any(keyword in context for keyword in SUSPICIOUS_KEYWORDS)

    def _find_high_entropy_strings(self, text: str) -> list[dict]:
        """
        Find strings with high entropy that could be secrets.

        Args:
            text: Text to analyze

        Returns:
            List of dicts with: text, position, entropy
        """
        high_entropy_matches = []

        # Search for alphanumeric words of appropriate length
        words = re.finditer(r"\b[A-Za-z0-9+/=]{16,}\b", text)

        for match in words:
            word = match.group(0)
            if is_high_entropy(word, self.entropy_threshold):
                high_entropy_matches.append(
                    {
                        "text": word,
                        "position": (match.start(), match.end()),
                        "entropy": calculate_entropy(word),
                    }
                )

        return high_entropy_matches

    def _is_duplicate(self, entropy_match: dict, existing_results: list[DetectionResult]) -> bool:
        """
        Check if an entropy match was already detected by regex.

        Args:
            entropy_match: Dict with text and position
            existing_results: Already detected results

        Returns:
            True if it's a duplicate
        """
        for result in existing_results:
            # Check overlapping positions
            start1, end1 = entropy_match["position"]
            start2, end2 = result.position

            if (start1 >= start2 and start1 < end2) or (start2 >= start1 and start2 < end1):
                return True

        return False

    def quick_check(self, text: str) -> bool:
        """
        Quick check if there's any secret (without detailed analysis).

        Args:
            text: Text to check

        Returns:
            True if at least one secret is detected

        Example:
            >>> detector = SecretDetector()
            >>> detector.quick_check("My key is AKIAIOSFODNN7EXAMPLE")  # pragma: allowlist secret
            True
        """
        return len(self.scan(text)) > 0
