"""
Unit tests for validator.py
"""

from src.core.validator import (
    luhn_check,
    validate_aws_key,
    validate_github_token,
    validate_jwt,
)


class TestLuhnCheck:
    """Tests for the Luhn algorithm"""

    def test_valid_visa_card(self):
        """Test: Valid Visa card"""
        assert luhn_check("4532015112830366") is True

    def test_valid_mastercard(self):
        """Test: Valid Mastercard card"""
        assert luhn_check("5425233430109903") is True

    def test_invalid_card(self):
        """Test: Invalid card"""
        assert luhn_check("1234567812345678") is False

    def test_card_with_spaces(self):
        """Test: Card with spaces should be validated"""
        assert luhn_check("4532 0151 1283 0366") is True

    def test_card_with_dashes(self):
        """Test: Card with dashes should be validated"""
        assert luhn_check("4532-0151-1283-0366") is True

    def test_empty_string(self):
        """Test: Empty string should return False"""
        assert luhn_check("") is False

    def test_short_string(self):
        """Test: Very short string should return False"""
        assert luhn_check("123") is False

    def test_non_numeric(self):
        """Test: Non-numeric string should return False"""
        assert luhn_check("abcd1234efgh5678") is False


class TestValidateAWSKey:
    """Tests for AWS Access Key validation"""

    def test_valid_akia_key(self):
        """Test: Valid AWS Access Key with AKIA prefix"""
        assert validate_aws_key("AKIAIOSFODNN7EXAMPLE") is True

    def test_valid_asia_key(self):
        """Test: Temporary AWS Access Key with ASIA prefix"""
        assert validate_aws_key("ASIA1234567890ABCDEF") is True

    def test_valid_abia_key(self):
        """Test: AWS Access Key with ABIA prefix"""
        assert validate_aws_key("ABIA1234567890ABCDEF") is True

    def test_invalid_prefix(self):
        """Test: Invalid prefix should fail"""
        assert validate_aws_key("INVALID0ACCESSKEYEXAM") is False

    def test_wrong_length(self):
        """Test: Incorrect length should fail"""
        assert validate_aws_key("AKIA123") is False
        assert validate_aws_key("AKIAIOSFODNN7EXAMPLEEXTRALONG") is False

    def test_empty_string(self):
        """Test: Empty string should return False"""
        assert validate_aws_key("") is False

    def test_lowercase_characters(self):
        """Test: Lowercase characters should fail"""
        assert validate_aws_key("AKIAiosfodnn7example") is False

    def test_special_characters(self):
        """Test: Special characters should fail"""
        assert validate_aws_key("AKIAIOSFODN!7EXAMPLE") is False


class TestValidateGitHubToken:
    """Tests for GitHub token validation"""

    def test_valid_ghp_token(self):
        """Test: Valid personal access token"""
        assert validate_github_token("ghp_1234567890abcdefghijklmnopqrstuvwxyzABCD") is True

    def test_valid_gho_token(self):
        """Test: Valid OAuth token"""
        assert validate_github_token("gho_1234567890abcdefghijklmnopqrstuvwxyzABCD") is True

    def test_valid_ghs_token(self):
        """Test: Valid server token"""
        assert validate_github_token("ghs_1234567890abcdefghijklmnopqrstuvwxyzABCD") is True

    def test_invalid_prefix(self):
        """Test: Invalid prefix should fail"""
        assert validate_github_token("invalid_1234567890abcdefghijklmnopqr") is False

    def test_too_short(self):
        """Test: Too short token should fail"""
        assert validate_github_token("ghp_123") is False

    def test_empty_string(self):
        """Test: Empty string should return False"""
        assert validate_github_token("") is False

    def test_special_characters_allowed(self):
        """Test: Underscores are allowed in the token"""
        assert validate_github_token("ghp_1234567890abcdefghijk_lmnopqrstuvwxyzABCD") is True


class TestValidateJWT:
    """Tests for JWT token validation"""

    def test_valid_jwt(self):
        """Test: Valid JWT with three parts"""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        assert validate_jwt(jwt) is True

    def test_invalid_parts_count(self):
        """Test: JWT with incorrect number of parts should fail"""
        assert validate_jwt("eyJhbGc.eyJzdWI") is False
        assert validate_jwt("eyJhbGc.eyJzdWI.extra.part") is False

    def test_empty_string(self):
        """Test: Empty string should return False"""
        assert validate_jwt("") is False

    def test_invalid_base64_header(self):
        """Test: Header without valid base64 format should fail"""
        assert validate_jwt("invalid.eyJzdWI.signature") is False

    def test_missing_eyj_prefix(self):
        """Test: Header/payload without 'eyJ' prefix should fail"""
        jwt = "aGVsbG8.d29ybGQ.c2lnbmF0dXJl"
        assert validate_jwt(jwt) is False


# Tests de casos edge
class TestEdgeCases:
    """Edge case tests"""

    def test_luhn_with_only_zeros(self):
        """Test: Card with only zeros"""
        assert luhn_check("0000000000000000") is True  # Mathematically valid

    def test_aws_key_boundary_length(self):
        """Test: AWS key exactly 20 characters"""
        valid_key = "AKIA" + "A" * 16
        assert validate_aws_key(valid_key) is True
        assert validate_aws_key(valid_key + "X") is False

    def test_github_token_minimum_length(self):
        """Test: GitHub token with minimum length"""
        min_token = "ghp_" + "a" * 36  # Total 40 chars
        assert validate_github_token(min_token) is True

    def test_jwt_with_empty_parts(self):
        """Test: JWT with empty parts"""
        assert validate_jwt("..") is False
        assert validate_jwt("eyJhbGc..signature") is False

    def test_aws_key_with_lowercase_fails(self):
        """Test: AWS key with lowercase fails"""
        lowercase_key = "AKIAiosfodnn7example"  # Has lowercase
        assert validate_aws_key(lowercase_key) is False

    def test_github_token_alphanumeric_check(self):
        """Test: GitHub token alphanumeric validation"""
        # Valid token with alphanumerics (40 characters)
        valid_token = "ghp_1234567890abcdefghijklmnopqrstuv1234"  # pragma: allowlist secret
        assert validate_github_token(valid_token) is True

        # Token with special characters (not valid)
        invalid_token = "ghp_abc#123defghijklmnopqrstuvwxyz123456"
        assert validate_github_token(invalid_token) is False
