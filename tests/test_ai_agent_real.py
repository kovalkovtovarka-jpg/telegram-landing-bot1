"""
Тесты для реального LandingAIAgent (backend.bot.ai_agent) с моками LLM.
Повышают покрытие ai_agent.py без вызовов к API.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.bot.ai_agent import LandingAIAgent


@pytest.fixture
def mock_llm_client():
    """Мок LLMClient, чтобы не вызывать реальный API."""
    with patch("backend.bot.ai_agent.LLMClient") as MockLLM:
        mock = MagicMock()
        mock.chat_async = AsyncMock(return_value="Ответ от модели")
        MockLLM.return_value = mock
        yield MockLLM


class TestLandingAIAgentInit:
    def test_init_single_mode(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        assert agent.mode == "SINGLE"
        assert agent.stage == "general_info"
        assert agent.collected_data["mode"] == "SINGLE"
        assert agent.collected_data["general_info"] == {}
        assert agent.collected_data["products"] == []

    def test_init_multi_mode(self, mock_llm_client):
        agent = LandingAIAgent("MULTI")
        assert agent.mode == "MULTI"
        assert agent.stage == "general_info"

    def test_init_invalid_mode_raises(self, mock_llm_client):
        with pytest.raises(ValueError, match="Mode must be 'SINGLE' or 'MULTI'"):
            LandingAIAgent("INVALID")


class TestLandingAIAgentStartConversation:
    @pytest.mark.asyncio
    async def test_start_conversation_returns_greeting(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        greeting = await agent.start_conversation()
        assert greeting is not None
        assert "лендинг" in greeting.lower() or "товара" in greeting.lower()
        assert "1/4" in greeting or "Общая информация" in greeting
        assert len(agent.conversation_history) == 1
        assert agent.conversation_history[0]["role"] == "assistant"


class TestLandingAIAgentSimpleExtractData:
    def test_simple_extract_goal_sale(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        r = agent._simple_extract_data("Хочу продать товар", "general_info")
        assert r.get("goal") == "продажа"

    def test_simple_extract_goal_contacts(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        r = agent._simple_extract_data("Нужны заявки и обратная связь", "general_info")
        assert r.get("goal") == "заявки"

    def test_simple_extract_style_minimal(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        r = agent._simple_extract_data("Стиль минималистичный", "general_info")
        assert r.get("style") == "минималистичный"

    def test_simple_extract_notification_email(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        r = agent._simple_extract_data("Пишите на test@mail.ru", "general_info")
        assert r.get("notification_type") == "email"

    def test_simple_extract_price_products_stage(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        r = agent._simple_extract_data("Цена 99 BYN", "products")
        assert r.get("new_price") == "99 BYN"

    def test_simple_extract_old_price(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        r = agent._simple_extract_data("Было 150 руб, сейчас 99 BYN", "products")
        assert r.get("new_price") == "99 BYN"
        assert r.get("old_price") == "150 BYN"


class TestLandingAIAgentDetermineFileBlock:
    def test_first_file_products_stage_is_hero(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        agent.collected_data["files"] = []
        assert agent._determine_file_block("photo") == "hero"

    def test_second_photo_after_hero_is_gallery(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        agent.collected_data["files"] = [{"block": "hero"}]
        assert agent._determine_file_block("photo") == "gallery"

    def test_video_after_hero_is_middle_video(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        agent.collected_data["files"] = [{"block": "hero"}]
        assert agent._determine_file_block("video") == "middle_video"

    def test_no_hero_returns_hero(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        agent.collected_data["files"] = [{"block": "gallery"}]
        assert agent._determine_file_block("photo") == "hero"


class TestLandingAIAgentUpdateCollectedData:
    def test_update_general_info(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent._update_collected_data({"goal": "продажа", "style": "минималистичный"})
        assert agent.collected_data["general_info"]["goal"] == "продажа"
        assert agent.collected_data["general_info"]["style"] == "минималистичный"

    def test_update_products_single_creates_product(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        agent._update_collected_data({"product_name": "Подушка"})
        assert len(agent.collected_data["products"]) == 1
        assert agent.collected_data["products"][0]["product_name"] == "Подушка"

    def test_update_products_single_appends_to_existing(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        agent.collected_data["products"] = [{"product_name": "Товар"}]
        agent._update_collected_data({"new_price": "99 BYN"})
        assert agent.collected_data["products"][0]["new_price"] == "99 BYN"


class TestLandingAIAgentProcessMessage:
    @pytest.mark.asyncio
    async def test_process_message_calls_extract_and_generate(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        await agent.start_conversation()  # add assistant message to history
        with patch.object(agent, "_extract_data", new_callable=AsyncMock, return_value={"goal": "продажа"}):
            with patch.object(agent, "_generate_response", new_callable=AsyncMock, return_value="Спасибо!"):
                with patch.object(agent, "_check_stage_transition", new_callable=AsyncMock):
                    out = await agent.process_message("Цель - продажа", user_id=1)
        assert out == "Спасибо!"
        agent._extract_data.assert_called_once()
        agent._generate_response.assert_called_once()
        assert agent.collected_data["general_info"].get("goal") == "продажа"

    @pytest.mark.asyncio
    async def test_process_message_appends_history(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        await agent.start_conversation()
        initial_len = len(agent.conversation_history)
        with patch.object(agent, "_extract_data", new_callable=AsyncMock, return_value={}):
            with patch.object(agent, "_generate_response", new_callable=AsyncMock, return_value="Ок"):
                with patch.object(agent, "_check_stage_transition", new_callable=AsyncMock):
                    await agent.process_message("Привет", user_id=1)
        assert len(agent.conversation_history) == initial_len + 2  # user + assistant
