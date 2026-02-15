"""
Тесты для backend.bot.handlers.base_handler (BaseHandler)
"""
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from backend.bot.handlers.base_handler import BaseHandler


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot._get_user_data = MagicMock(return_value={"product_name": "Test"})
    bot._update_user_data = MagicMock()
    bot._save_user_data = MagicMock()
    bot._clear_user_data = MagicMock()
    return bot


@pytest.fixture
def handler(mock_bot):
    return BaseHandler(mock_bot)


class TestBaseHandlerData:
    def test_get_user_data_delegates_to_bot(self, handler, mock_bot):
        data = handler.get_user_data(12345)
        mock_bot._get_user_data.assert_called_once_with(12345)
        assert data == {"product_name": "Test"}

    def test_update_user_data_calls_bot(self, handler, mock_bot):
        handler.update_user_data(12345, product_name="New", price=99)
        mock_bot._update_user_data.assert_called_once_with(12345, product_name="New", price=99)

    def test_save_state_with_data_calls_bot(self, handler, mock_bot):
        data = {"state": "COLLECTING"}
        handler.save_state(12345, "COLLECTING_HERO", data=data, conversation_type="create")
        mock_bot._save_user_data.assert_called_once_with(
            12345, data, state="COLLECTING_HERO", conversation_type="create"
        )

    def test_save_state_without_data_uses_get_user_data(self, handler, mock_bot):
        handler.save_state(12345, "NEXT_STATE", conversation_type="quick")
        mock_bot._get_user_data.assert_called_with(12345)
        mock_bot._save_user_data.assert_called_once()
        assert mock_bot._save_user_data.call_args[0][1] == {"product_name": "Test"}

    def test_clear_user_data_calls_bot(self, handler, mock_bot):
        handler.clear_user_data(12345)
        mock_bot._clear_user_data.assert_called_once_with(12345)


class TestBaseHandlerLog:
    def test_log_info(self, handler, caplog):
        handler.log("info", "test message", user_id=999)
        assert "test message" in caplog.text or "999" in caplog.text

    def test_log_error(self, handler, caplog):
        handler.log("error", "error message")
        assert "error message" in caplog.text

    def test_log_warning(self, handler, caplog):
        handler.log("warning", "warn message")
        assert "warn message" in caplog.text

    def test_log_debug(self, handler, caplog):
        import logging
        with caplog.at_level(logging.DEBUG):
            handler.log("debug", "debug message")
        assert "debug message" in caplog.text


class TestBaseHandlerCheckFileSize:
    def test_file_under_limit_returns_true(self, handler):
        with patch("backend.bot.handlers.base_handler.Config") as Config:
            Config.MAX_FILE_SIZE = 10 * 1024 * 1024
            ok, msg = handler.check_file_size(1024 * 1024, "файл")
        assert ok is True
        assert msg == ""

    def test_file_over_limit_returns_false_and_message(self, handler):
        with patch("backend.bot.handlers.base_handler.Config") as Config:
            Config.MAX_FILE_SIZE = 1024
            ok, msg = handler.check_file_size(2048, "изображение")
        assert ok is False
        assert "большой" in msg or "размер" in msg.lower()
        assert "MB" in msg or "MB" in msg

    def test_zero_size_returns_true(self, handler):
        with patch("backend.bot.handlers.base_handler.Config") as Config:
            Config.MAX_FILE_SIZE = 1024
            ok, msg = handler.check_file_size(0, "файл")
        assert ok is True


class TestBaseHandlerValidateUploadedFile:
    def test_valid_image_returns_true(self, handler):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff")
            path = f.name
        try:
            ok, msg = handler.validate_uploaded_file(path, expected_type="image")
            assert ok is True
            assert msg is None
        finally:
            os.unlink(path)

    def test_nonexistent_file_returns_false(self, handler):
        ok, msg = handler.validate_uploaded_file("/nonexistent/file.jpg", expected_type="image")
        assert ok is False
        assert msg is not None
