"""
Tests unitarios para validator.py
"""

from src.core.validator import (
    luhn_check,
    validate_aws_key,
    validate_github_token,
    validate_jwt,
)


class TestLuhnCheck:
    """Tests para el algoritmo de Luhn"""

    def test_valid_visa_card(self):
        """Test: Tarjeta Visa válida"""
        assert luhn_check("4532015112830366") is True

    def test_valid_mastercard(self):
        """Test: Tarjeta Mastercard válida"""
        assert luhn_check("5425233430109903") is True

    def test_invalid_card(self):
        """Test: Tarjeta inválida"""
        assert luhn_check("1234567812345678") is False

    def test_card_with_spaces(self):
        """Test: Tarjeta con espacios debe ser validada"""
        assert luhn_check("4532 0151 1283 0366") is True

    def test_card_with_dashes(self):
        """Test: Tarjeta con guiones debe ser validada"""
        assert luhn_check("4532-0151-1283-0366") is True

    def test_empty_string(self):
        """Test: String vacío debe retornar False"""
        assert luhn_check("") is False

    def test_short_string(self):
        """Test: String muy corto debe retornar False"""
        assert luhn_check("123") is False

    def test_non_numeric(self):
        """Test: String no numérico debe retornar False"""
        assert luhn_check("abcd1234efgh5678") is False


class TestValidateAWSKey:
    """Tests para validación de AWS Access Keys"""

    def test_valid_akia_key(self):
        """Test: AWS Access Key válida con prefijo AKIA"""
        assert validate_aws_key("AKIAIOSFODNN7EXAMPLE") is True

    def test_valid_asia_key(self):
        """Test: AWS Access Key temporal con prefijo ASIA"""
        assert validate_aws_key("ASIA1234567890ABCDEF") is True

    def test_valid_abia_key(self):
        """Test: AWS Access Key con prefijo ABIA"""
        assert validate_aws_key("ABIA1234567890ABCDEF") is True

    def test_invalid_prefix(self):
        """Test: Prefijo inválido debe fallar"""
        assert validate_aws_key("INVALID0ACCESSKEYEXAM") is False

    def test_wrong_length(self):
        """Test: Longitud incorrecta debe fallar"""
        assert validate_aws_key("AKIA123") is False
        assert validate_aws_key("AKIAIOSFODNN7EXAMPLEEXTRALONG") is False

    def test_empty_string(self):
        """Test: String vacío debe retornar False"""
        assert validate_aws_key("") is False

    def test_lowercase_characters(self):
        """Test: Caracteres en minúsculas deben fallar"""
        assert validate_aws_key("AKIAiosfodnn7example") is False

    def test_special_characters(self):
        """Test: Caracteres especiales deben fallar"""
        assert validate_aws_key("AKIAIOSFODN!7EXAMPLE") is False


class TestValidateGitHubToken:
    """Tests para validación de GitHub tokens"""

    def test_valid_ghp_token(self):
        """Test: Personal access token válido"""
        assert validate_github_token("ghp_1234567890abcdefghijklmnopqrstuvwxyzABCD") is True

    def test_valid_gho_token(self):
        """Test: OAuth token válido"""
        assert validate_github_token("gho_1234567890abcdefghijklmnopqrstuvwxyzABCD") is True

    def test_valid_ghs_token(self):
        """Test: Server token válido"""
        assert validate_github_token("ghs_1234567890abcdefghijklmnopqrstuvwxyzABCD") is True

    def test_invalid_prefix(self):
        """Test: Prefijo inválido debe fallar"""
        assert validate_github_token("invalid_1234567890abcdefghijklmnopqr") is False

    def test_too_short(self):
        """Test: Token muy corto debe fallar"""
        assert validate_github_token("ghp_123") is False

    def test_empty_string(self):
        """Test: String vacío debe retornar False"""
        assert validate_github_token("") is False

    def test_special_characters_allowed(self):
        """Test: Underscores están permitidos en el token"""
        assert validate_github_token("ghp_1234567890abcdefghijk_lmnopqrstuvwxyzABCD") is True


class TestValidateJWT:
    """Tests para validación de JWT tokens"""

    def test_valid_jwt(self):
        """Test: JWT válido con tres partes"""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        assert validate_jwt(jwt) is True

    def test_invalid_parts_count(self):
        """Test: JWT con número incorrecto de partes debe fallar"""
        assert validate_jwt("eyJhbGc.eyJzdWI") is False
        assert validate_jwt("eyJhbGc.eyJzdWI.extra.part") is False

    def test_empty_string(self):
        """Test: String vacío debe retornar False"""
        assert validate_jwt("") is False

    def test_invalid_base64_header(self):
        """Test: Header sin formato base64 válido debe fallar"""
        assert validate_jwt("invalid.eyJzdWI.signature") is False

    def test_missing_eyj_prefix(self):
        """Test: Header/payload sin prefijo 'eyJ' debe fallar"""
        jwt = "aGVsbG8.d29ybGQ.c2lnbmF0dXJl"
        assert validate_jwt(jwt) is False


# Tests de casos edge
class TestEdgeCases:
    """Tests de casos límite y edge cases"""

    def test_luhn_with_only_zeros(self):
        """Test: Tarjeta con solo ceros"""
        assert luhn_check("0000000000000000") is True  # Matemáticamente válido

    def test_aws_key_boundary_length(self):
        """Test: AWS key exactamente 20 caracteres"""
        valid_key = "AKIA" + "A" * 16
        assert validate_aws_key(valid_key) is True
        assert validate_aws_key(valid_key + "X") is False

    def test_github_token_minimum_length(self):
        """Test: GitHub token con longitud mínima"""
        min_token = "ghp_" + "a" * 36  # Total 40 chars
        assert validate_github_token(min_token) is True

    def test_jwt_with_empty_parts(self):
        """Test: JWT con partes vacías"""
        assert validate_jwt("..") is False
        assert validate_jwt("eyJhbGc..signature") is False

    def test_aws_key_with_lowercase_fails(self):
        """Test: AWS key con minúsculas falla (línea 74)"""
        lowercase_key = "AKIAiosfodnn7example"  # Tiene minúsculas
        assert validate_aws_key(lowercase_key) is False

    def test_github_token_alphanumeric_check(self):
        """Test: GitHub token validación alfanumérica (línea 109)"""
        # Token válido con alfanuméricos (40 caracteres)
        valid_token = "ghp_1234567890abcdefghijklmnopqrstuv1234"  # pragma: allowlist secret
        assert validate_github_token(valid_token) is True

        # Token con caracteres especiales (no válido)
        invalid_token = "ghp_abc#123defghijklmnopqrstuvwxyz123456"
        assert validate_github_token(invalid_token) is False
