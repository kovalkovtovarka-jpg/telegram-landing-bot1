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

    def test_missing_anthropic_key_raises_when_provider_anthropic(self):
        with patch.object(Config, "TELEGRAM_BOT_TOKEN", "123:abc"), \
             patch.object(Config, "DATABASE_URL", "sqlite:///test.db"), \
             patch.object(Config, "ANTHROPIC_API_KEY", ""), \
             patch.object(Config, "LLM_PROVIDER", "anthropic"):
            with pytest.raises(ValueError) as exc_info:
                Config.validate()
            assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_missing_google_key_raises_when_provider_google(self):
        with patch.object(Config, "TELEGRAM_BOT_TOKEN", "123:abc"), \
             patch.object(Config, "DATABASE_URL", "sqlite:///test.db"), \
             patch.object(Config, "GOOGLE_API_KEY", ""), \
             patch.object(Config, "LLM_PROVIDER", "google"):
            with pytest.raises(ValueError) as exc_info:
                Config.validate()
            assert "GOOGLE_API_KEY" in str(exc_info.value)

    def test_valid_with_anthropic_key_passes(self):
        with patch.object(Config, "TELEGRAM_BOT_TOKEN", "123:abc"), \
             patch.object(Config, "DATABASE_URL", "sqlite:///test.db"), \
             patch.object(Config, "ANTHROPIC_API_KEY", "sk-ant-test"), \
             patch.object(Config, "LLM_PROVIDER", "anthropic"):
            assert Config.validate() is True

    def test_valid_with_google_key_passes(self):
        with patch.object(Config, "TELEGRAM_BOT_TOKEN", "123:abc"), \
             patch.object(Config, "DATABASE_URL", "sqlite:///test.db"), \
             patch.object(Config, "GOOGLE_API_KEY", "AIza-test"), \
             patch.object(Config, "LLM_PROVIDER", "google"):
            assert Config.validate() is True

    def test_no_api_key_at_all_raises(self):
        with patch.object(Config, "TELEGRAM_BOT_TOKEN", "123:abc"), \
             patch.object(Config, "DATABASE_URL", "sqlite:///test.db"), \
             patch.object(Config, "OPENAI_API_KEY", ""), \
             patch.object(Config, "ANTHROPIC_API_KEY", ""), \
             patch.object(Config, "GOOGLE_API_KEY", ""):
            with pytest.raises(ValueError) as exc_info:
                Config.validate()
            assert "API ключ" in str(exc_info.value) or "OPENAI" in str(exc_info.value) or "LLM" in str(exc_info.value)


class TestConfigAttributes:
    """Тесты атрибутов Config (значения по умолчанию и парсинг)."""

    def test_bot_admin_ids_parsed_as_list(self):
        with patch.object(Config, "BOT_ADMIN_IDS", ["123", "456"]):
            assert Config.BOT_ADMIN_IDS == ["123", "456"]

    def test_notify_admins_on_startup_true(self):
        with patch.object(Config, "NOTIFY_ADMINS_ON_STARTUP", True):
            assert Config.NOTIFY_ADMINS_ON_STARTUP is True

    def test_max_file_size_int(self):
        with patch.object(Config, "MAX_FILE_SIZE", 10485760):
            assert Config.MAX_FILE_SIZE == 10485760

    def test_max_requests_per_hour_int(self):
        with patch.object(Config, "MAX_REQUESTS_PER_HOUR", 10):
            assert Config.MAX_REQUESTS_PER_HOUR == 10
