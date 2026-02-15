"""
Тесты точки входа main (минимальные проверки без запуска бота).
"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture
def main_module():
    """Импорт main с возможностью патчить зависимости."""
    import main as main_mod
    return main_mod


class TestMainModule:
    def test_main_is_async_callable(self, main_module):
        assert asyncio.iscoroutinefunction(main_module.main)

    def test_main_catches_value_error_and_exits(self, main_module):
        with patch.object(main_module.Config, "validate", side_effect=ValueError("config error")), \
             patch("main.sys.exit") as mock_exit:
            asyncio.run(main_module.main())
            mock_exit.assert_called_once_with(1)

    def test_main_calls_validate_and_init_db_on_success_path(self, main_module):
        mock_cache = MagicMock()
        mock_cache.clear_expired.return_value = 0
        with patch.object(main_module.Config, "validate", return_value=True), \
             patch.object(main_module, "init_db") as init_db, \
             patch("main.LandingBot") as MockBot, \
             patch("main.os.path.exists", return_value=False), \
             patch("backend.utils.cache.prompt_cache", mock_cache):
            mock_bot_instance = MagicMock()
            mock_bot_instance.start_polling = AsyncMock()
            mock_bot_instance.stop = AsyncMock()
            MockBot.return_value = mock_bot_instance
            asyncio.run(main_module.main())
            init_db.assert_called_once()
            mock_bot_instance.start_polling.assert_called_once()
