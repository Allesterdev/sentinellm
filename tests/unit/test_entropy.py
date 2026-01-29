"""
Tests unitarios para entropy.py
"""

import pytest

from src.core.entropy import (
    analyze_entropy_distribution,
    calculate_entropy,
    is_high_entropy,
)


class TestCalculateEntropy:
    """Tests para la función calculate_entropy"""

    def test_empty_string(self):
        """Test: String vacío debe retornar 0"""
        assert calculate_entropy("") == 0.0

    def test_single_character_repeated(self):
        """Test: String con un solo carácter repetido debe tener entropía 0"""
        assert calculate_entropy("aaaa") == 0.0
        assert calculate_entropy("1111") == 0.0

    def test_low_entropy_string(self):
        """Test: String con baja entropía"""
        entropy = calculate_entropy("password")
        assert 0.0 < entropy < 3.0

    def test_high_entropy_string(self):
        """Test: String con alta entropía (aleatorio)"""
        entropy = calculate_entropy("wJalrXUtnFEMI/K7MDENG")
        assert entropy > 4.0

    def test_aws_key_entropy(self):
        """Test: AWS key tiene entropía moderada-alta"""
        entropy = calculate_entropy("AKIAIOSFODNN7EXAMPLE")
        assert 3.5 <= entropy <= 5.0

    def test_deterministic(self):
        """Test: Mismo input produce mismo output"""
        text = "test123ABC!@#"
        entropy1 = calculate_entropy(text)
        entropy2 = calculate_entropy(text)
        assert entropy1 == entropy2


class TestIsHighEntropy:
    """Tests para la función is_high_entropy"""

    def test_short_string_rejected(self):
        """Test: String menor a min_length es rechazado"""
        assert is_high_entropy("abc", min_length=16) is False

    def test_long_string_rejected(self):
        """Test: String mayor a max_length es rechazado"""
        long_string = "a" * 1000
        assert is_high_entropy(long_string, max_length=512) is False

    def test_high_entropy_accepted(self):
        """Test: String con alta entropía y longitud válida es aceptado"""
        high_entropy_str = "a8f5f167f44f4964e6c998dee827110c"
        # MD5 hash tiene entropía ~3.5, usar threshold más bajo o string más aleatorio
        assert is_high_entropy(high_entropy_str, threshold=3.5) is True

    def test_low_entropy_rejected(self):
        """Test: String con baja entropía es rechazado"""
        low_entropy_str = "passwordpassword"
        assert is_high_entropy(low_entropy_str, threshold=4.5) is False

    def test_custom_threshold(self):
        """Test: Threshold personalizado funciona correctamente"""
        text = "moderateentropy123"
        assert is_high_entropy(text, threshold=3.0) is True
        assert is_high_entropy(text, threshold=5.0) is False


class TestAnalyzeEntropyDistribution:
    """Tests para analyze_entropy_distribution"""

    def test_empty_string(self):
        """Test: String vacío retorna valores en 0"""
        result = analyze_entropy_distribution("")
        assert result["entropy"] == 0.0
        assert result["uppercase_ratio"] == 0.0
        assert result["digit_ratio"] == 0.0
        assert result["special_ratio"] == 0.0

    def test_uppercase_string(self):
        """Test: String todo mayúsculas"""
        result = analyze_entropy_distribution("ABCDEF")
        assert result["uppercase_ratio"] == 1.0
        assert result["digit_ratio"] == 0.0
        assert result["special_ratio"] == 0.0

    def test_digits_only(self):
        """Test: String solo dígitos"""
        result = analyze_entropy_distribution("123456")
        assert result["digit_ratio"] == 1.0
        assert result["uppercase_ratio"] == 0.0

    def test_mixed_string(self):
        """Test: String mixto"""
        result = analyze_entropy_distribution("Abc123!@")
        assert 0 < result["uppercase_ratio"] < 1
        assert 0 < result["digit_ratio"] < 1
        assert 0 < result["special_ratio"] < 1
        assert result["entropy"] > 0

    def test_aws_key_distribution(self):
        """Test: Distribución de AWS key típica"""
        result = analyze_entropy_distribution("AKIAIOSFODNN7EXAMPLE")
        # AWS keys son principalmente mayúsculas con algunos dígitos
        assert result["uppercase_ratio"] > 0.7
        assert result["digit_ratio"] > 0.0
        assert result["special_ratio"] == 0.0
