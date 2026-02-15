"""
Тесты для MetricsCollector (backend.utils.metrics)
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.utils.metrics import MetricsCollector


class TestMetricsCollector:
    """Тесты сбора метрик с моком БД"""

    def test_get_user_stats_returns_dict(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 5
        mock_db.query.return_value.count.return_value = 10
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_user_stats()
        assert isinstance(result, dict)
        assert "total_users" in result
        assert "active_users" in result
        assert "new_users_24h" in result
        assert "new_users_7d" in result
        mock_db.close.assert_called_once()

    def test_get_user_stats_on_exception_returns_empty(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("db error")
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_user_stats()
        assert result == {}
        mock_db.close.assert_called_once()

    def test_get_project_stats_returns_dict(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 2
        mock_db.query.return_value.count.return_value = 10
        mock_db.query.return_value.filter.return_value.scalar.return_value = 15.5
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_project_stats()
        assert isinstance(result, dict)
        assert "total_projects" in result
        assert "completed" in result
        assert "success_rate" in result
        mock_db.close.assert_called_once()

    def test_get_project_stats_on_exception_returns_empty(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("db error")
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_project_stats()
        assert result == {}
        mock_db.close.assert_called_once()

    def test_get_generation_stats_returns_dict(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 3
        mock_db.query.return_value.count.return_value = 10
        mock_db.query.return_value.filter.return_value.scalar.return_value = 100.0
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_generation_stats()
        assert isinstance(result, dict)
        assert "total_generations" in result
        assert "success_rate" in result
        mock_db.close.assert_called_once()

    def test_get_generation_stats_on_exception_returns_empty(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("db error")
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_generation_stats()
        assert result == {}
        mock_db.close.assert_called_once()

    def test_get_all_stats_includes_users_projects_generations_timestamp(self):
        with patch.object(MetricsCollector, "get_user_stats", return_value={"total_users": 1}), \
             patch.object(MetricsCollector, "get_project_stats", return_value={"total_projects": 2}), \
             patch.object(MetricsCollector, "get_generation_stats", return_value={"total_generations": 3}):
            result = MetricsCollector.get_all_stats()
        assert result["users"] == {"total_users": 1}
        assert result["projects"] == {"total_projects": 2}
        assert result["generations"] == {"total_generations": 3}
        assert "timestamp" in result

    def test_get_user_specific_stats_user_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_user_specific_stats(999)
        assert result == {"error": "User not found"}
        mock_db.close.assert_called_once()

    def test_get_user_specific_stats_returns_user_stats(self):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "test"
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_user, [], []]
        mock_db.query.return_value.filter.return_value.all.return_value = []
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_user_specific_stats(12345)
        assert "user_id" in result
        assert result["username"] == "test"
        mock_db.close.assert_called_once()

    def test_get_user_specific_stats_on_exception_returns_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("db error")
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_user_specific_stats(12345)
        assert "error" in result
        assert "db error" in result["error"]
        mock_db.close.assert_called_once()

    def test_get_all_telegram_user_ids_returns_list(self):
        mock_db = MagicMock()
        mock_db.query.return_value.distinct.return_value.all.return_value = [("123",), ("456",)]
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_all_telegram_user_ids()
        assert isinstance(result, list)
        mock_db.close.assert_called_once()

    def test_get_all_telegram_user_ids_skips_invalid_ids(self):
        mock_db = MagicMock()
        mock_db.query.return_value.distinct.return_value.all.return_value = [("not_a_number",), ("789",)]
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_all_telegram_user_ids()
        assert 789 in result
        mock_db.close.assert_called_once()

    def test_get_all_telegram_user_ids_on_exception_returns_empty(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("db error")
        with patch("backend.utils.metrics.SessionLocal", return_value=mock_db):
            result = MetricsCollector.get_all_telegram_user_ids()
        assert result == []
        mock_db.close.assert_called_once()
