"""
Тесты проверки конфигурации при старте (Config.validate)
"""
import pytest
from unittest.mock import patch

from backend.config import Config


class TestConfigValidate:
    """Тесты для Config.validate() — обязательные переменные при старте"""

    def test_valid_config_passes(self):
        with patch.object(Config, "TELEGRAM_BOT_TOKEN", "123:abc"), \
             patch.object(Config, "DATABASE_URL", "sqlite:///test.db"), \
             patch.object(Config, "OPENAI_API_KEY", "sk-test"), \
             patch.object(Config, "LLM_PROVIDER", "openai"):
            assert Config.validate() is True

    def test_missing_telegram_token_raises(self):
        with patch.object(Config, "TELEGRAM_BOT_TOKEN", ""), \
             patch.object(Config, "DATABASE_URL", "sqlite:///test.db"), \
             patch.object(Config, "OPENAI_API_KEY", "sk-test"):
            with pytest.raises(ValueError) as exc_info:
                Config.validate()
            assert "TELEGRAM_BOT_TOKEN" in str(exc_info.value)
            assert "Railway" in str(exc_info.value) or "переменные окружения" in str(exc_info.value).lower()

    def test_missing_database_url_raises(self):
        with patch.object(Config, "TELEGRAM_BOT_TOKEN", "123:abc"), \
             patch.object(Config, "DATABASE_URL", ""), \
             patch.object(Config, "OPENAI_API_KEY", "sk-test"):
            with pytest.raises(ValueError) as exc_info:
                Config.validate()
            assert "DATABASE_URL" in str(exc_info.value)

    def test_missing_openai_key_raises_when_provider_openai(self):
        with patch.object(Config, "TELEGRAM_BOT_TOKEN", "123:abc"), \
             patch.object(Config, "DATABASE_URL", "sqlite:///test.db"), \
             patch.object(Config, "OPENAI_API_KEY", ""), \
             patch.object(Config, "LLM_PROVIDER", "openai"):
            with pytest.raises(ValueError) as exc_info:
                Config.validate()
            assert "OPENAI_API_KEY" in str(exc_info.value)
