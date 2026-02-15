"""
Тесты для backend.bot.handlers.product_handler (ProductHandler).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from backend.bot.handlers.product_handler import ProductHandler
from backend.bot.handlers.states import COLLECTING_HERO_MEDIA, COLLECTING_TIMER_SETTINGS, COLLECTING_CHARACTERISTICS


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot._get_user_data = MagicMock(return_value={})
    bot._update_user_data = MagicMock()
    bot._save_user_data = MagicMock()
    bot._clear_user_data = MagicMock()
    return bot


@pytest.fixture
def handler(mock_bot):
    return ProductHandler(mock_bot)


@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.text = "Тестовый товар"
    update.message.reply_text = AsyncMock(return_value=update.message)
    return update


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    return ctx


class TestProductHandlerCollectProductName:
    @pytest.mark.asyncio
    async def test_collect_product_name_saves_and_returns_hero_state(self, handler, mock_bot, mock_update, mock_context):
        mock_update.message.text = "  Ортопедическая подушка  "
        result = await handler.collect_product_name(mock_update, mock_context)

        mock_bot._update_user_data.assert_called_once_with(12345, product_name="Ортопедическая подушка")
        mock_bot._save_user_data.assert_called_once()
        call_args = mock_bot._save_user_data.call_args
        assert call_args[0][0] == 12345
        assert call_args[1].get("state") == "COLLECTING_HERO_MEDIA"
        mock_update.message.reply_text.assert_called_once()
        assert "Hero" in mock_update.message.reply_text.call_args[0][0] or "фото" in mock_update.message.reply_text.call_args[0][0].lower()
        assert result == COLLECTING_HERO_MEDIA

    @pytest.mark.asyncio
    async def test_collect_product_name_strips_whitespace(self, handler, mock_bot, mock_update, mock_context):
        mock_update.message.text = "  Товар  "
        await handler.collect_product_name(mock_update, mock_context)
        mock_bot._update_user_data.assert_called_once_with(12345, product_name="Товар")


class TestProductHandlerCollectCharacteristics:
    @pytest.mark.asyncio
    async def test_collect_characteristics_three_lines_success(self, handler, mock_bot, mock_update, mock_context):
        mock_bot._get_user_data.return_value = {}
        mock_update.message.text = "Легкая\nУдобная\nКачественная"
        result = await handler.collect_characteristics(mock_update, mock_context)

        mock_bot._update_user_data.assert_called_once_with(12345, characteristics=["Легкая", "Удобная", "Качественная"])
        mock_bot._save_user_data.assert_called_once()
        assert mock_bot._save_user_data.call_args[1].get("state") == "COLLECTING_TIMER_SETTINGS"
        assert "Таймер" in mock_update.message.reply_text.call_args[0][0] or "таймер" in mock_update.message.reply_text.call_args[0][0].lower()
        assert result == COLLECTING_TIMER_SETTINGS

    @pytest.mark.asyncio
    async def test_collect_characteristics_less_than_three_asks_for_more(self, handler, mock_bot, mock_update, mock_context):
        mock_update.message.text = "Одна\nДве"
        result = await handler.collect_characteristics(mock_update, mock_context)

        mock_bot._update_user_data.assert_not_called()
        mock_bot._save_user_data.assert_not_called()
        assert "2" in mock_update.message.reply_text.call_args[0][0] or "минимум" in mock_update.message.reply_text.call_args[0][0].lower()
        assert result == COLLECTING_CHARACTERISTICS

    @pytest.mark.asyncio
    async def test_collect_characteristics_more_than_three_truncates_to_three(self, handler, mock_bot, mock_update, mock_context):
        mock_bot._get_user_data.return_value = {}
        mock_update.message.text = "Х1\nХ2\nХ3\nХ4\nХ5"
        await handler.collect_characteristics(mock_update, mock_context)
        mock_bot._update_user_data.assert_called_once_with(12345, characteristics=["Х1", "Х2", "Х3"])
