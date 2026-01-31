"""
Tests unitarios para el módulo detector.py
"""

from src.core.detector import DetectionResult, SecretDetector
from src.utils.constants import SecretType, ThreatLevel


class TestSecretDetector:
    """Tests para la clase SecretDetector"""

    def test_detector_initialization(self):
        """Test: Inicialización del detector con parámetros por defecto"""
        detector = SecretDetector()
        assert detector.entropy_threshold == 4.5
        assert detector.min_length == 16
        assert detector.max_length == 512

    def test_detector_custom_params(self):
        """Test: Inicialización con parámetros personalizados"""
        detector = SecretDetector(entropy_threshold=5.0, min_length=20, max_length=256)
        assert detector.entropy_threshold == 5.0
        assert detector.min_length == 20
        assert detector.max_length == 256

    def test_scan_empty_text(self, detector):
        """Test: Escanear texto vacío"""
        results = detector.scan("")
        assert len(results) == 0

    def test_scan_clean_text(self, detector, clean_text):
        """Test: Escanear texto sin secretos"""
        results = detector.scan(clean_text)
        assert len(results) == 0

    def test_detect_aws_access_key(self, detector, sample_aws_key):
        """Test: Detectar AWS Access Key"""
        text = f"My AWS key is {sample_aws_key} for production"
        results = detector.scan(text)

        assert len(results) >= 1
        aws_result = results[0]
        assert aws_result.found is True
        assert aws_result.secret_type == SecretType.AWS_ACCESS_KEY
        assert aws_result.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)
        assert sample_aws_key in aws_result.matched_text

    def test_detect_github_token(self, detector, sample_github_token):
        """Test: Detectar GitHub token"""
        text = f"Token: {sample_github_token}"
        results = detector.scan(text)

        assert len(results) >= 1
        github_result = results[0]
        assert github_result.found is True
        assert github_result.secret_type == SecretType.GITHUB_TOKEN
        assert sample_github_token in github_result.matched_text

    def test_detect_credit_card(self, detector, sample_credit_card):
        """Test: Detectar tarjeta de crédito con validación Luhn"""
        text = f"Card number: {sample_credit_card}"
        results = detector.scan(text)

        assert len(results) >= 1
        card_result = results[0]
        assert card_result.found is True
        assert card_result.secret_type == SecretType.CREDIT_CARD
        assert card_result.context.get("is_valid") is True

    def test_detect_jwt_token(self, detector, sample_jwt):
        """Test: Detectar JWT token"""
        text = f"Authorization: {sample_jwt}"
        results = detector.scan(text)

        assert len(results) >= 1
        jwt_result = results[0]
        assert jwt_result.found is True
        assert jwt_result.secret_type == SecretType.JWT_TOKEN

    def test_detect_multiple_secrets(self, detector, sample_aws_key, sample_github_token):
        """Test: Detectar múltiples secretos en un texto"""
        text = f"AWS: {sample_aws_key} and GitHub: {sample_github_token}"
        results = detector.scan(text)

        assert len(results) >= 2
        secret_types = [r.secret_type for r in results]
        assert SecretType.AWS_ACCESS_KEY in secret_types
        assert SecretType.GITHUB_TOKEN in secret_types

    def test_quick_check_with_secret(self, detector, sample_aws_key):
        """Test: quick_check retorna True cuando hay secreto"""
        text = f"Key: {sample_aws_key}"
        assert detector.quick_check(text) is True

    def test_quick_check_without_secret(self, detector, clean_text):
        """Test: quick_check retorna False cuando no hay secreto"""
        assert detector.quick_check(clean_text) is False

    def test_suspicious_context_detection(self, detector, sample_aws_key):
        """Test: Detectar contexto sospechoso con palabras clave"""
        text_with_context = f"password={sample_aws_key}"
        text_without_context = f"random text {sample_aws_key}"

        results_with = detector.scan(text_with_context)
        results_without = detector.scan(text_without_context)

        # Ambos deben detectar, pero el que tiene contexto debe tener mayor confianza
        assert len(results_with) >= 1
        assert len(results_without) >= 1
        assert results_with[0].context.get("has_suspicious_keywords") is True

    def test_high_entropy_detection(self, detector):
        """Test: Detectar strings con alta entropía (posibles secretos desconocidos)"""
        high_entropy_string = "a8f5f167f44f4964e6c998dee827110c"
        text = f"API key: {high_entropy_string}"
        results = detector.scan(text)

        assert len(results) >= 1
        # Puede ser detectado como GENERIC_API_KEY
        assert any(r.entropy > 3.5 for r in results)


class TestDetectionResult:
    """Tests para la clase DetectionResult"""

    def test_detection_result_initialization(self):
        """Test: Inicialización de DetectionResult"""
        result = DetectionResult()
        assert result.found is False
        assert result.threat_level == ThreatLevel.NONE
        assert result.confidence == 0.0

    def test_redact_secret(self):
        """Test: Redactar secreto"""
        result = DetectionResult(matched_text="AKIAIOSFODNN7EXAMPLE")
        redacted = result.redact_secret(show_chars=4)
        assert redacted.startswith("AKIA")
        assert "*" in redacted
        assert "EXAMPLE" not in redacted

    def test_redact_short_secret(self):
        """Test: Redactar secreto corto"""
        result = DetectionResult(matched_text="ABC")
        redacted = result.redact_secret(show_chars=4)
        assert redacted == "****"


# Tests de integración básicos
class TestIntegration:
    """Tests de integración end-to-end"""

    def test_full_scan_realistic_scenario(self, detector):
        """Test: Escenario realista con múltiples tipos de secretos"""
        text = """
        # Production Configuration
        AWS_ACCESS_KEY = AKIAIOSFODNN7EXAMPLE
        AWS_SECRET = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
        GITHUB_TOKEN = ghp_1234567890abcdefghijklmnopqrstuvwxyzABCD
        DB_PASSWORD = supersecurepassword123
        """

        results = detector.scan(text)

        # Debe detectar al menos AWS key y GitHub token
        assert len(results) >= 2

        # Verificar niveles de amenaza apropiados
        threat_levels = [r.threat_level for r in results]
        assert ThreatLevel.HIGH in threat_levels or ThreatLevel.CRITICAL in threat_levels

    def test_no_false_positives_on_code(self, detector):
        """Test: No detectar falsos positivos en código normal"""
        code = """
        def calculate_hash(data):
            return hashlib.sha256(data).hexdigest()

        class APIClient:
            def __init__(self, base_url):
                self.base_url = base_url
        """

        results = detector.scan(code)
        # No debería haber detecciones en código normal
        assert len(results) == 0
