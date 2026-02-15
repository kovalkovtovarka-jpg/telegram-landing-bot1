"""
Тесты для backend.bot.handlers.price_handler (PriceHandler).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from backend.bot.handlers.price_handler import PriceHandler
from backend.bot.handlers.states import COLLECTING_PRICES, COLLECTING_FORM_OPTIONS


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot._get_user_data = MagicMock(return_value={})
    bot._update_user_data = MagicMock()
    bot._save_user_data = MagicMock()
    return bot


@pytest.fixture
def handler(mock_bot):
    return PriceHandler(mock_bot)


@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    return MagicMock()


class TestPriceHandlerCollectPrices:
    @pytest.mark.asyncio
    async def test_first_price_saved_as_old_asks_for_new(self, handler, mock_bot, mock_update, mock_context):
        mock_bot._get_user_data.return_value = {}
        mock_update.message.text = "150 BYN"
        result = await handler.collect_prices(mock_update, mock_context)

        mock_bot._update_user_data.assert_called_once_with(12345, old_price="150 BYN")
        assert "скидк" in mock_update.message.reply_text.call_args[0][0].lower() or "Цена" in mock_update.message.reply_text.call_args[0][0]
        assert result == COLLECTING_PRICES

    @pytest.mark.asyncio
    async def test_adds_byn_if_no_currency(self, handler, mock_bot, mock_update, mock_context):
        mock_bot._get_user_data.return_value = {}
        mock_update.message.text = "150"
        await handler.collect_prices(mock_update, mock_context)
        mock_bot._update_user_data.assert_called_once_with(12345, old_price="150 BYN")

    @pytest.mark.asyncio
    async def test_second_price_saved_as_new_transitions_to_form(self, handler, mock_bot, mock_update, mock_context):
        mock_bot._get_user_data.return_value = {"old_price": "150 BYN"}
        mock_update.message.text = "99 BYN"
        result = await handler.collect_prices(mock_update, mock_context)

        mock_bot._update_user_data.assert_called_with(12345, new_price="99 BYN")
        mock_bot._save_user_data.assert_called_once()
        assert mock_bot._save_user_data.call_args[1].get("state") == "COLLECTING_FORM_OPTIONS"
        assert "Форма" in mock_update.message.reply_text.call_args[0][0] or "форма" in mock_update.message.reply_text.call_args[0][0].lower()
        assert result == COLLECTING_FORM_OPTIONS

    @pytest.mark.asyncio
    async def test_collect_new_price_delegates_to_collect_prices(self, handler, mock_bot, mock_update, mock_context):
        mock_bot._get_user_data.return_value = {"old_price": "100"}
        mock_update.message.text = "80 BYN"
        result = await handler.collect_new_price(mock_update, mock_context)
        assert result == COLLECTING_FORM_OPTIONS
