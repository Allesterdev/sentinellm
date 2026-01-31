"""Tests for i18n module."""

import pytest

from src.cli.i18n import STRINGS, get_language, set_language, t


class TestI18n:
    """Test internationalization functionality."""

    def test_default_language_is_english(self):
        """Test that default language is English."""
        assert "en" in STRINGS
        assert "es" in STRINGS

    def test_set_language_english(self):
        """Test setting language to English."""
        set_language("en")
        assert get_language() == "en"

    def test_set_language_spanish(self):
        """Test setting language to Spanish."""
        set_language("es")
        assert get_language() == "es"

    def test_set_language_invalid(self):
        """Test setting invalid language raises error."""
        with pytest.raises(ValueError):
            set_language("invalid")

    def test_translate_english(self):
        """Test translation in English."""
        set_language("en")
        assert t("demo_title") == "🛡️  SentineLLM - AI Security Gateway - Interactive Demo"

    def test_translate_spanish(self):
        """Test translation in Spanish."""
        set_language("es")
        assert t("demo_title") == "🛡️  SentineLLM - AI Security Gateway - Demo Interactiva"

    def test_translate_missing_key_fallback(self):
        """Test that missing keys fallback to English."""
        set_language("es")
        result = t("nonexistent_key")
        assert result.startswith("[MISSING:")

    def test_all_english_keys_have_spanish(self):
        """Test that all English keys have Spanish translations."""
        en_keys = set(STRINGS["en"].keys())
        es_keys = set(STRINGS["es"].keys())
        assert en_keys == es_keys, f"Missing keys: {en_keys - es_keys}"

    def test_main_menu_translations(self):
        """Test main menu translations exist."""
        set_language("en")
        assert "What would you like to do?" in t("main_menu")

        set_language("es")
        assert "¿Qué quieres hacer?" in t("main_menu")

    def test_scenario_translations(self):
        """Test scenario translations exist."""
        set_language("en")
        assert "Safe Prompt" == t("scenario_safe")

        set_language("es")
        assert "Prompt Seguro" == t("scenario_safe")

    def test_prompt_translations(self):
        """Test prompt translations exist."""
        set_language("en")
        assert "What is the capital of France?" == t("prompt_safe")

        set_language("es")
        assert "¿Cuál es la capital de Francia?" == t("prompt_safe")

    def test_all_demo_prompts_translated(self):
        """Test all demo prompts have translations."""
        demo_keys = [
            "prompt_safe",
            "prompt_ignore",
            "prompt_identity",
            "prompt_system",
            "prompt_aws",
            "prompt_github",
            "prompt_credit",
            "prompt_combined",
        ]

        set_language("en")
        for key in demo_keys:
            result = t(key)
            assert not result.startswith("[MISSING:"), f"Missing English translation for {key}"

        set_language("es")
        for key in demo_keys:
            result = t(key)
            assert not result.startswith("[MISSING:"), f"Missing Spanish translation for {key}"

    def test_strings_dict_structure(self):
        """Test STRINGS dictionary has correct structure."""
        from src.cli.i18n import STRINGS

        assert "en" in STRINGS
        assert "es" in STRINGS
        assert isinstance(STRINGS["en"], dict)
        assert isinstance(STRINGS["es"], dict)
