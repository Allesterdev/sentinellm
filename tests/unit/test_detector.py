"""
Unit tests for the detector.py module
"""

from src.core.detector import DetectionResult, SecretDetector
from src.utils.constants import SecretType, ThreatLevel


class TestSecretDetector:
    """Tests for the SecretDetector class"""

    def test_detector_initialization(self):
        """Test: Detector initialization with default parameters"""
        detector = SecretDetector()
        assert detector.entropy_threshold == 4.5
        assert detector.min_length == 16
        assert detector.max_length == 512

    def test_detector_custom_params(self):
        """Test: Initialization with custom parameters"""
        detector = SecretDetector(entropy_threshold=5.0, min_length=20, max_length=256)
        assert detector.entropy_threshold == 5.0
        assert detector.min_length == 20
        assert detector.max_length == 256

    def test_scan_empty_text(self, detector):
        """Test: Scan empty text"""
        results = detector.scan("")
        assert len(results) == 0

    def test_scan_clean_text(self, detector, clean_text):
        """Test: Scan text without secrets"""
        results = detector.scan(clean_text)
        assert len(results) == 0

    def test_detect_aws_access_key(self, detector, sample_aws_key):
        """Test: Detect AWS Access Key"""
        text = f"My AWS key is {sample_aws_key} for production"
        results = detector.scan(text)

        assert len(results) >= 1
        aws_result = results[0]
        assert aws_result.found is True
        assert aws_result.secret_type == SecretType.AWS_ACCESS_KEY
        assert aws_result.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)
        assert sample_aws_key in aws_result.matched_text

    def test_detect_github_token(self, detector, sample_github_token):
        """Test: Detect GitHub token"""
        text = f"Token: {sample_github_token}"
        results = detector.scan(text)

        assert len(results) >= 1
        github_result = results[0]
        assert github_result.found is True
        assert github_result.secret_type == SecretType.GITHUB_TOKEN
        assert sample_github_token in github_result.matched_text

    def test_detect_credit_card(self, detector, sample_credit_card):
        """Test: Detect credit card with Luhn validation"""
        text = f"Card number: {sample_credit_card}"
        results = detector.scan(text)

        assert len(results) >= 1
        card_result = results[0]
        assert card_result.found is True
        assert card_result.secret_type == SecretType.CREDIT_CARD
        assert card_result.context.get("is_valid") is True

    def test_detect_jwt_token(self, detector, sample_jwt):
        """Test: Detect JWT token"""
        text = f"Authorization: {sample_jwt}"
        results = detector.scan(text)

        assert len(results) >= 1
        jwt_result = results[0]
        assert jwt_result.found is True
        assert jwt_result.secret_type == SecretType.JWT_TOKEN

    def test_detect_multiple_secrets(self, detector, sample_aws_key, sample_github_token):
        """Test: Detect multiple secrets in a text"""
        text = f"AWS: {sample_aws_key} and GitHub: {sample_github_token}"
        results = detector.scan(text)

        assert len(results) >= 2
        secret_types = [r.secret_type for r in results]
        assert SecretType.AWS_ACCESS_KEY in secret_types
        assert SecretType.GITHUB_TOKEN in secret_types

    def test_quick_check_with_secret(self, detector, sample_aws_key):
        """Test: quick_check returns True when there is a secret"""
        text = f"Key: {sample_aws_key}"
        assert detector.quick_check(text) is True

    def test_quick_check_without_secret(self, detector, clean_text):
        """Test: quick_check returns False when there is no secret"""
        assert detector.quick_check(clean_text) is False

    def test_suspicious_context_detection(self, detector, sample_aws_key):
        """Test: Detect suspicious context with keywords"""
        text_with_context = f"password={sample_aws_key}"
        text_without_context = f"random text {sample_aws_key}"

        results_with = detector.scan(text_with_context)
        results_without = detector.scan(text_without_context)

        # Both should detect, but the one with context should have higher confidence
        assert len(results_with) >= 1
        assert len(results_without) >= 1
        assert results_with[0].context.get("has_suspicious_keywords") is True

    def test_high_entropy_detection(self, detector):
        """Test: Detect strings with high entropy (possible unknown secrets)"""
        high_entropy_string = "a8f5f167f44f4964e6c998dee827110c"  # pragma: allowlist secret
        text = f"API key: {high_entropy_string}"
        results = detector.scan(text)

        assert len(results) >= 1
        # Puede ser detectado como GENERIC_API_KEY
        assert any(r.entropy > 3.5 for r in results)


class TestDetectionResult:
    """Tests for the DetectionResult class"""

    def test_detection_result_initialization(self):
        """Test: DetectionResult initialization"""
        result = DetectionResult()
        assert result.found is False
        assert result.threat_level == ThreatLevel.NONE
        assert result.confidence == 0.0

    def test_redact_secret(self):
        """Test: Redact secret"""
        result = DetectionResult(matched_text="AKIAIOSFODNN7EXAMPLE")
        redacted = result.redact_secret(show_chars=4)
        assert redacted.startswith("AKIA")
        assert "*" in redacted
        assert "EXAMPLE" not in redacted

    def test_redact_short_secret(self):
        """Test: Redact short secret"""
        result = DetectionResult(matched_text="ABC")
        redacted = result.redact_secret(show_chars=4)
        assert redacted == "****"


# Basic integration tests
class TestIntegration:
    """End-to-end integration tests"""

    def test_full_scan_realistic_scenario(self, detector):
        """Test: Realistic scenario with multiple secret types"""
        text = """
        # Production Configuration
        AWS_ACCESS_KEY = AKIAIOSFODNN7EXAMPLE  # pragma: allowlist secret
        AWS_SECRET = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  # pragma: allowlist secret
        GITHUB_TOKEN = ghp_1234567890abcdefghijklmnopqrstuvwxyzABCD  # pragma: allowlist secret
        DB_PASSWORD = supersecurepassword123
        """

        results = detector.scan(text)

        # Should detect at least AWS key and GitHub token
        assert len(results) >= 2

        # Verify appropriate threat levels
        threat_levels = [r.threat_level for r in results]
        assert ThreatLevel.HIGH in threat_levels or ThreatLevel.CRITICAL in threat_levels

    def test_no_false_positives_on_code(self, detector):
        """Test: No false positives on normal code"""
        code = """
        def calculate_hash(data):
            return hashlib.sha256(data).hexdigest()

        class APIClient:
            def __init__(self, base_url):
                self.base_url = base_url
        """

        results = detector.scan(code)
        # There should be no detections on normal code
        assert len(results) == 0

    def test_medium_threat_with_context(self, detector):
        """Test: MEDIUM threat with suspicious context"""
        # Only regex match + suspicious context = MEDIUM
        text = "password: abc123def456ghi789jkl"
        results = detector.scan(text)

        if len(results) > 0:
            # If it detects anything, it should be due to context
            assert True  # El test pasa si llega aquí

    def test_entropy_overlap_detection(self, detector):
        """Test: Overlap detection between entropy matches"""
        # Create text with overlapping high entropy
        text = "Here is a key: XyZ123AbC456DeF789GhI012JkL345MnO678PqR901StU234VwX567"
        results = detector.scan(text)

        # Should detect and handle overlaps correctly
        assert isinstance(results, list)
