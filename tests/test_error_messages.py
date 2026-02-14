"""
Тесты форматирования сообщений об ошибках для пользователя
"""
import pytest
from unittest.mock import patch, MagicMock

from backend.bot.telegram_bot import LandingBot


class TestFormatErrorMessage:
    """Тесты для _format_error_message"""

    @pytest.fixture
    def bot(self, mock_application):
        """Бот с замоканным Application"""
        with patch("backend.bot.telegram_bot.SessionLocal", return_value=MagicMock()):
            with patch("backend.bot.telegram_bot.init_db"):
                with patch.dict(
                    "os.environ",
                    {
                        "TELEGRAM_BOT_TOKEN": "test",
                        "DATABASE_URL": "sqlite:///:memory:",
                        "OPENAI_API_KEY": "test",
                    },
                ):
                    yield LandingBot()

    def test_timeout_message(self, bot):
        msg = bot._format_error_message("Request timeout after 120s")
        assert "Превышено время" in msg or "ожидания" in msg
        assert "Что делать" in msg

    def test_rate_limit_message(self, bot):
        msg = bot._format_error_message("Rate limit exceeded 429")
        assert "лимит" in msg.lower() or "429" in msg
        assert "Что делать" in msg

    def test_network_message(self, bot):
        msg = bot._format_error_message("Network connection failed")
        assert "подключен" in msg.lower() or "сеть" in msg.lower()
        assert "Что делать" in msg

    def test_api_key_message(self, bot):
        msg = bot._format_error_message("Invalid API key")
        assert "настройки" in msg or "ключ" in msg.lower() or "конфигурац" in msg.lower()
        assert "Что делать" in msg

    def test_retries_exhausted_message(self, bot):
        msg = bot._format_error_message("Failed after 3 attempts")
        assert "перегружен" in msg or "попыток" in msg
        assert "/ai" in msg or "генерировать" in msg

    def test_generic_error_message(self, bot):
        msg = bot._format_error_message("Some unknown error")
        assert "Ошибка" in msg
        assert "Что делать" in msg
