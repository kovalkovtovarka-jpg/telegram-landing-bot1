"""
Тесты для webhook (обработчик и запуск).
"""
import pytest
from aiohttp import web
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def webhook_module():
    import webhook as mod
    return mod


class TestHandleWebhook:
    async def test_handle_webhook_no_bot_returns_500(self, webhook_module):
        with patch.object(webhook_module, "bot_instance", None):
            request = MagicMock()
            request.json = AsyncMock(return_value={"update_id": 1})
            response = await webhook_module.handle_webhook(request)
        assert response.status == 500
        assert response.text == "Error"

    async def test_handle_webhook_invalid_json_returns_500(self, webhook_module):
        request = MagicMock()
        request.json = AsyncMock(side_effect=ValueError("invalid json"))
        with patch.object(webhook_module, "bot_instance", MagicMock()):
            response = await webhook_module.handle_webhook(request)
        assert response.status == 500

    async def test_handle_webhook_success_returns_200(self, webhook_module):
        mock_bot_inst = MagicMock()
        mock_bot_inst.app.process_update = AsyncMock()
        request = MagicMock()
        request.json = AsyncMock(return_value={"update_id": 1})
        with patch.object(webhook_module, "bot_instance", mock_bot_inst), \
             patch("telegram.Update") as MockUpdate:
            mock_update_instance = MagicMock()
            MockUpdate.de_json.return_value = mock_update_instance
            response = await webhook_module.handle_webhook(request)
        assert response.status == 200
        assert response.text == "OK"


class TestStartWebhook:
    async def test_start_webhook_raises_when_no_webhook_url(self, webhook_module):
        with patch.object(webhook_module.Config, "validate", return_value=True), \
             patch.object(webhook_module.Config, "WEBHOOK_URL", ""):
            with pytest.raises(ValueError) as exc_info:
                await webhook_module.start_webhook()
            assert "WEBHOOK_URL" in str(exc_info.value)
