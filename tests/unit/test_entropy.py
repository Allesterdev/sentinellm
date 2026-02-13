"""
Unit tests for entropy.py
"""

from src.core.entropy import (
    analyze_entropy_distribution,
    calculate_entropy,
    is_high_entropy,
)


class TestCalculateEntropy:
    """Tests for the calculate_entropy function"""

    def test_empty_string(self):
        """Test: Empty string should return 0"""
        assert calculate_entropy("") == 0.0

    def test_single_character_repeated(self):
        """Test: String with a single repeated character should have entropy 0"""
        assert calculate_entropy("aaaa") == 0.0
        assert calculate_entropy("1111") == 0.0

    def test_low_entropy_string(self):
        """Test: String with low entropy"""
        entropy = calculate_entropy("password")
        assert 0.0 < entropy < 3.0

    def test_high_entropy_string(self):
        """Test: String with high entropy (random)"""
        entropy = calculate_entropy("wJalrXUtnFEMI/K7MDENG")
        assert entropy > 4.0

    def test_aws_key_entropy(self):
        """Test: AWS key has moderate-high entropy"""
        entropy = calculate_entropy("AKIAIOSFODNN7EXAMPLE")
        assert 3.5 <= entropy <= 5.0

    def test_deterministic(self):
        """Test: Same input produces same output"""
        text = "test123ABC!@#"
        entropy1 = calculate_entropy(text)
        entropy2 = calculate_entropy(text)
        assert entropy1 == entropy2


class TestIsHighEntropy:
    """Tests for the is_high_entropy function"""

    def test_short_string_rejected(self):
        """Test: String shorter than min_length is rejected"""
        assert is_high_entropy("abc", min_length=16) is False

    def test_long_string_rejected(self):
        """Test: String longer than max_length is rejected"""
        long_string = "a" * 1000
        assert is_high_entropy(long_string, max_length=512) is False

    def test_high_entropy_accepted(self):
        """Test: String with high entropy and valid length is accepted"""
        high_entropy_str = "a8f5f167f44f4964e6c998dee827110c"
        # MD5 hash has entropy ~3.5, use lower threshold or more random string
        assert is_high_entropy(high_entropy_str, threshold=3.5) is True

    def test_low_entropy_rejected(self):
        """Test: String with low entropy is rejected"""
        low_entropy_str = "passwordpassword"
        assert is_high_entropy(low_entropy_str, threshold=4.5) is False

    def test_custom_threshold(self):
        """Test: Custom threshold works correctly"""
        text = "moderateentropy123"
        assert is_high_entropy(text, threshold=3.0) is True
        assert is_high_entropy(text, threshold=5.0) is False


class TestAnalyzeEntropyDistribution:
    """Tests for analyze_entropy_distribution"""

    def test_empty_string(self):
        """Test: Empty string returns values of 0"""
        result = analyze_entropy_distribution("")
        assert result["entropy"] == 0.0
        assert result["uppercase_ratio"] == 0.0
        assert result["digit_ratio"] == 0.0
        assert result["special_ratio"] == 0.0

    def test_uppercase_string(self):
        """Test: All uppercase string"""
        result = analyze_entropy_distribution("ABCDEF")
        assert result["uppercase_ratio"] == 1.0
        assert result["digit_ratio"] == 0.0
        assert result["special_ratio"] == 0.0

    def test_digits_only(self):
        """Test: Digits only string"""
        result = analyze_entropy_distribution("123456")
        assert result["digit_ratio"] == 1.0
        assert result["uppercase_ratio"] == 0.0

    def test_mixed_string(self):
        """Test: Mixed string"""
        result = analyze_entropy_distribution("Abc123!@")
        assert 0 < result["uppercase_ratio"] < 1
        assert 0 < result["digit_ratio"] < 1
        assert 0 < result["special_ratio"] < 1
        assert result["entropy"] > 0

    def test_aws_key_distribution(self):
        """Test: Typical AWS key distribution"""
        result = analyze_entropy_distribution("AKIAIOSFODNN7EXAMPLE")
        # AWS keys are mainly uppercase with some digits
        assert result["uppercase_ratio"] > 0.7
        assert result["digit_ratio"] > 0.0
        assert result["special_ratio"] == 0.0
