"""
Тесты для backend.bot.handlers.timer_handler (TimerHandler).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from backend.bot.handlers.timer_handler import TimerHandler
from backend.bot.handlers.states import COLLECTING_TIMER_SETTINGS, COLLECTING_PRICES


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot._get_user_data = MagicMock(return_value={})
    bot._update_user_data = MagicMock()
    bot._save_user_data = MagicMock()
    return bot


@pytest.fixture
def handler(mock_bot):
    return TimerHandler(mock_bot)


@pytest.fixture
def mock_update_callback():
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.data = "timer_yes"
    return update


@pytest.fixture
def mock_update_message():
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.text = "31.12.2024"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    return MagicMock()


class TestTimerHandlerSelectTimerOption:
    @pytest.mark.asyncio
    async def test_timer_no_goes_to_prices(self, handler, mock_bot, mock_update_callback, mock_context):
        mock_update_callback.callback_query.data = "timer_no"
        result = await handler.select_timer_option(mock_update_callback, mock_context)

        mock_bot._update_user_data.assert_called_with(12345, timer_enabled=False, timer_type=None, timer_date=None)
        assert mock_bot._save_user_data.call_args[1].get("state") == "COLLECTING_PRICES"
        assert result == COLLECTING_PRICES

    @pytest.mark.asyncio
    async def test_timer_yes_asks_type(self, handler, mock_bot, mock_update_callback, mock_context):
        result = await handler.select_timer_option(mock_update_callback, mock_context)

        mock_bot._update_user_data.assert_any_call(12345, timer_enabled=True)
        mock_update_callback.callback_query.edit_message_text.assert_called_once()
        assert "тип" in mock_update_callback.callback_query.edit_message_text.call_args[0][0].lower()
        assert result == COLLECTING_TIMER_SETTINGS


class TestTimerHandlerCollectTimerDate:
    @pytest.mark.asyncio
    async def test_valid_date_saves_and_goes_to_prices(self, handler, mock_bot, mock_update_message, mock_context):
        mock_update_message.message.text = "25.12.2025"
        result = await handler.collect_timer_date(mock_update_message, mock_context)

        mock_bot._update_user_data.assert_called_once_with(12345, timer_date="25.12.2025")
        assert mock_bot._save_user_data.call_args[1].get("state") == "COLLECTING_PRICES"
        assert result == COLLECTING_PRICES

    @pytest.mark.asyncio
    async def test_invalid_date_asks_again(self, handler, mock_bot, mock_update_message, mock_context):
        mock_update_message.message.text = "invalid"
        result = await handler.collect_timer_date(mock_update_message, mock_context)

        mock_bot._update_user_data.assert_not_called()
        mock_bot._save_user_data.assert_not_called()
        assert "ДД.ММ.ГГГГ" in mock_update_message.message.reply_text.call_args[0][0] or "формат" in mock_update_message.message.reply_text.call_args[0][0].lower()
        assert result == COLLECTING_TIMER_SETTINGS
