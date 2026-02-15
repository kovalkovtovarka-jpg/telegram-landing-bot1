"""
Тесты для backend.database.database (init_db, get_db, close_db)
"""
import pytest
from unittest.mock import patch, MagicMock

from backend.database import database


class TestInitDb:
    def test_init_db_calls_create_all(self):
        with patch.object(database.Base.metadata, "create_all") as create_all:
            database.init_db()
            create_all.assert_called_once()
            assert create_all.call_args[1]["bind"] == database.engine

    def test_init_db_prints_message(self, capsys):
        with patch.object(database.Base.metadata, "create_all"):
            database.init_db()
            out, _ = capsys.readouterr()
            assert "инициализирована" in out or "init" in out.lower()


class TestGetDb:
    def test_get_db_yields_session_and_closes(self):
        gen = database.get_db()
        session = next(gen)
        assert session is not None
        try:
            next(gen)
        except StopIteration:
            pass

    def test_get_db_session_has_close(self):
        gen = database.get_db()
        session = next(gen)
        try:
            assert callable(getattr(session, "close", None))
        finally:
            try:
                next(gen)
            except StopIteration:
                pass


class TestCloseDb:
    def test_close_db_calls_remove(self):
        with patch.object(database.SessionLocal, "remove") as remove:
            database.close_db()
            remove.assert_called_once()
