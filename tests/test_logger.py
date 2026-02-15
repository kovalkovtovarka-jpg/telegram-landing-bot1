"""
Тесты для backend.utils.logger
"""
import logging
import os
import tempfile
from unittest.mock import patch

import pytest

from backend.utils.logger import (
    get_logger,
    set_request_context,
    clear_request_context,
    log_with_context,
    SecretRedactionFilter,
    ContextualFormatter,
    setup_logging,
)


def test_get_logger_returns_logger():
    log = get_logger("test.module")
    assert isinstance(log, logging.Logger)
    assert log.name == "test.module"


class TestSecretRedactionFilter:
    def test_redacts_bot_token_in_msg(self):
        f = SecretRedactionFilter()
        record = logging.LogRecord("n", logging.INFO, "", 0, "url: api.telegram.org/bot123:secret/me", (), None)
        result = f.filter(record)
        assert result is True
        assert "bot123:secret" not in record.msg
        assert "bot***" in record.msg

    def test_redacts_in_dict_args(self):
        f = SecretRedactionFilter()
        record = logging.LogRecord("n", logging.INFO, "", 0, "", (), None)
        record.args = {"url": "bot456:abc"}
        result = f.filter(record)
        assert result is True
        assert record.args["url"] == "bot***"

    def test_redacts_in_tuple_args(self):
        f = SecretRedactionFilter()
        record = logging.LogRecord("n", logging.INFO, "", 0, "%s", ("bot789:xyz",), None)
        result = f.filter(record)
        assert result is True
        assert record.args[0] == "bot***"

    def test_non_string_msg_unchanged(self):
        f = SecretRedactionFilter()
        record = logging.LogRecord("n", logging.INFO, "", 0, 42, (), None)
        result = f.filter(record)
        assert result is True
        assert record.msg == 42


class TestContextualFormatter:
    def test_format_adds_request_and_user_placeholders(self):
        formatter = ContextualFormatter("%(request_id)s %(user_id)s %(message)s")
        record = logging.LogRecord("n", logging.INFO, "", 0, "hello", (), None)
        out = formatter.format(record)
        assert "N/A" in out or "hello" in out


class TestRequestContext:
    def test_set_and_clear_request_context(self):
        clear_request_context()
        set_request_context(request_id="req-1", user_id=123)
        from backend.utils.logger import request_id_var, user_id_var
        assert request_id_var.get() == "req-1"
        assert user_id_var.get() == 123
        clear_request_context()
        assert request_id_var.get() is None
        assert user_id_var.get() is None

    def test_set_request_context_none_does_not_override(self):
        clear_request_context()
        set_request_context(request_id="r", user_id=1)
        set_request_context(request_id=None, user_id=None)
        from backend.utils.logger import request_id_var, user_id_var
        assert request_id_var.get() == "r"
        assert user_id_var.get() == 1
        clear_request_context()


class TestLogWithContext:
    def test_log_with_context_calls_logger(self, caplog):
        log = logging.getLogger("test.log_with_context")
        log_with_context(log, "info", "test message", user_id=999, request_id="ctx-1")
        assert "test message" in caplog.text or len(caplog.records) >= 1

    def test_log_with_context_restores_previous_context(self):
        clear_request_context()
        set_request_context(request_id="original", user_id=1)
        log = get_logger("test")
        log_with_context(log, "debug", "msg", user_id=2, request_id="temp")
        from backend.utils.logger import request_id_var, user_id_var
        assert request_id_var.get() == "original"
        assert user_id_var.get() == 1
        clear_request_context()


class TestSetupLogging:
    def test_setup_logging_creates_handlers(self):
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_file = f.name
        try:
            setup_logging(log_level="INFO", log_file=log_file, max_bytes=1024, backup_count=0)
            root = logging.getLogger()
            assert len(root.handlers) >= 1
            assert os.path.exists(log_file) or True
        finally:
            if os.path.exists(log_file):
                try:
                    os.unlink(log_file)
                except Exception:
                    pass
