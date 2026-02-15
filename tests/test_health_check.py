"""
Тесты для backend.utils.health_check (check_database, check_llm, check_health)
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from backend.utils.health_check import check_database, check_llm, check_health


class TestCheckDatabase:
    """Тесты проверки БД"""

    @pytest.mark.asyncio
    async def test_database_healthy(self):
        mock_db = MagicMock()
        mock_db.query.return_value.limit.return_value.all.return_value = []

        with patch("backend.utils.health_check.SessionLocal", return_value=mock_db):
            result = await check_database()

        assert result["status"] == "healthy"
        assert "Database" in result["message"]
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_unhealthy_on_query_error(self):
        mock_db = MagicMock()
        mock_db.query.return_value.limit.return_value.all.side_effect = Exception("Connection refused")

        with patch("backend.utils.health_check.SessionLocal", return_value=mock_db):
            result = await check_database()

        assert result["status"] == "unhealthy"
        assert "error" in result["message"].lower() or "refused" in result["message"].lower()
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_unhealthy_on_session_fail(self):
        with patch("backend.utils.health_check.SessionLocal", side_effect=Exception("No DB")):
            result = await check_database()

        assert result["status"] == "unhealthy"


class TestCheckLlm:
    """Тесты проверки LLM"""

    @pytest.mark.asyncio
    async def test_llm_healthy_openai(self):
        with patch("backend.utils.health_check.Config") as MockConfig:
            MockConfig.LLM_PROVIDER = "openai"
            with patch("backend.utils.health_check.LLMClient") as MockLLM:
                mock_client = MagicMock()
                mock_client.client = MagicMock()
                MockLLM.return_value = mock_client
                result = await check_llm()
        assert result["status"] == "healthy"
        assert "openai" in result["message"].lower() or "OPENAI" in result["message"]

    @pytest.mark.asyncio
    async def test_llm_unhealthy_when_no_client(self):
        with patch("backend.utils.health_check.Config") as MockConfig:
            MockConfig.LLM_PROVIDER = "openai"
            with patch("backend.utils.health_check.LLMClient") as MockLLM:
                mock_client = MagicMock()
                mock_client.client = None
                MockLLM.return_value = mock_client
                result = await check_llm()
        assert result["status"] == "unhealthy"
        assert "key" in result["message"].lower() or "configured" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_llm_healthy_anthropic(self):
        with patch("backend.utils.health_check.Config") as MockConfig:
            MockConfig.LLM_PROVIDER = "anthropic"
            with patch("backend.utils.health_check.LLMClient") as MockLLM:
                mock_client = MagicMock()
                mock_client.client = MagicMock()
                MockLLM.return_value = mock_client
                result = await check_llm()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_llm_unhealthy_on_exception(self):
        with patch("backend.utils.health_check.LLMClient", side_effect=Exception("Init failed")):
            result = await check_llm()
        assert result["status"] == "unhealthy"


class TestCheckHealth:
    """Тесты полной проверки здоровья"""

    @pytest.mark.asyncio
    async def test_health_healthy_when_both_ok(self):
        with patch("backend.utils.health_check.check_database", new_callable=AsyncMock) as mock_db:
            with patch("backend.utils.health_check.check_llm", new_callable=AsyncMock) as mock_llm:
                mock_db.return_value = {"status": "healthy", "message": "OK"}
                mock_llm.return_value = {"status": "healthy", "message": "OK"}
                result = await check_health()
        assert result["status"] == "healthy"
        assert "database" in result["checks"]
        assert "llm" in result["checks"]
        assert result["checks"]["database"]["status"] == "healthy"
        assert result["checks"]["llm"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_unhealthy_when_db_fails(self):
        with patch("backend.utils.health_check.check_database", new_callable=AsyncMock) as mock_db:
            with patch("backend.utils.health_check.check_llm", new_callable=AsyncMock) as mock_llm:
                mock_db.return_value = {"status": "unhealthy", "message": "DB down"}
                mock_llm.return_value = {"status": "healthy", "message": "OK"}
                result = await check_health()
        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_unhealthy_when_llm_fails(self):
        with patch("backend.utils.health_check.check_database", new_callable=AsyncMock) as mock_db:
            with patch("backend.utils.health_check.check_llm", new_callable=AsyncMock) as mock_llm:
                mock_db.return_value = {"status": "healthy", "message": "OK"}
                mock_llm.return_value = {"status": "unhealthy", "message": "No API key"}
                result = await check_health()
        assert result["status"] == "unhealthy"
