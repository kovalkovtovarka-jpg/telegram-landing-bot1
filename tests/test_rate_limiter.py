"""
Тесты для backend.utils.rate_limiter (RateLimiter)
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.utils.rate_limiter import RateLimiter


class TestRateLimiterInMemory:
    """Тесты in-memory проверки лимита (check_rate_limit)"""

    @pytest.mark.asyncio
    async def test_allowed_when_under_limit(self):
        limiter = RateLimiter(max_requests=3, per_seconds=3600)
        allowed, remaining = await limiter.check_rate_limit(12345)
        assert allowed is True
        assert remaining == 2  # 1 запрос учтён, осталось 2

    @pytest.mark.asyncio
    async def test_denied_when_at_limit(self):
        limiter = RateLimiter(max_requests=2, per_seconds=3600)
        await limiter.check_rate_limit(999)
        await limiter.check_rate_limit(999)
        allowed, remaining = await limiter.check_rate_limit(999)
        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_different_users_independent(self):
        limiter = RateLimiter(max_requests=1, per_seconds=3600)
        await limiter.check_rate_limit(1)
        allowed_2, _ = await limiter.check_rate_limit(2)
        assert allowed_2 is True
        allowed_1, _ = await limiter.check_rate_limit(1)
        assert allowed_1 is False

    @pytest.mark.asyncio
    async def test_record_request_appends(self):
        limiter = RateLimiter(max_requests=10, per_seconds=3600)
        await limiter.record_request(111)
        stats = limiter.get_user_stats(111)
        assert stats["requests_count"] == 1
        assert stats["remaining"] == 9


class TestRateLimiterGetUserStats:
    """Тесты get_user_stats (in-memory)"""

    @pytest.mark.asyncio
    async def test_stats_reflect_requests(self):
        limiter = RateLimiter(max_requests=5, per_seconds=3600)
        stats = limiter.get_user_stats(999)
        assert stats["requests_count"] == 0
        assert stats["max_requests"] == 5
        assert stats["remaining"] == 5
        assert stats["period_seconds"] == 3600

        await limiter.check_rate_limit(999)
        await limiter.check_rate_limit(999)
        stats2 = limiter.get_user_stats(999)
        assert stats2["requests_count"] == 2
        assert stats2["remaining"] == 3


class TestRateLimiterDb:
    """Тесты проверки лимита через БД (check_db_rate_limit)"""

    @pytest.mark.asyncio
    async def test_db_allowed_when_under_limit(self):
        limiter = RateLimiter(max_requests=10, per_seconds=3600)
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 2
        mock_db.query.return_value = mock_query

        with patch("backend.utils.rate_limiter.SessionLocal", return_value=mock_db):
            allowed, remaining = await limiter.check_db_rate_limit(12345)

        assert allowed is True
        assert remaining == 8
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_db_denied_when_at_limit(self):
        limiter = RateLimiter(max_requests=5, per_seconds=3600)
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5
        mock_db.query.return_value = mock_query

        with patch("backend.utils.rate_limiter.SessionLocal", return_value=mock_db):
            allowed, remaining = await limiter.check_db_rate_limit(999)

        assert allowed is False
        assert remaining == 0
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_db_exception_fail_open(self):
        limiter = RateLimiter(max_requests=3, per_seconds=3600)
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB error")

        with patch("backend.utils.rate_limiter.SessionLocal", return_value=mock_db):
            allowed, remaining = await limiter.check_db_rate_limit(111)

        assert allowed is True
        assert remaining == 3
        mock_db.close.assert_called_once()
