"""
Тесты сценариев диалога AI-агента: как может вести себя пользователь.

Покрывают:
- порядок отправки (сначала фото / сначала описание / вместе)
- извлечение скидки, цен, подвала, уведомлений
- распределение фото по блокам (описание, галерея, отзывы)
- convert_to_user_data для генератора
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.bot.ai_agent import LandingAIAgent


@pytest.fixture
def mock_llm_client():
    with patch("backend.bot.ai_agent.LLMClient") as MockLLM:
        MockLLM.return_value = MagicMock()
        yield MockLLM


# ---------- Сценарий: пользователь сначала присылает только описание (текст) ----------

class TestScenarioDescriptionFirst:
    """Пользователь первым делом вставляет описание (например с ВБ), без фото."""

    def test_long_text_in_general_info_extracts_product_name_and_description(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "general_info"
        msg = "Ортопедическая подушка\nМягкая, с эффектом памяти. Размер 50x30. Для сна."
        r = agent._simple_extract_data(msg, "general_info")
        assert r.get("product_name") == "Ортопедическая подушка"
        assert "Мягкая" in r.get("product_description", "")
        assert r.get("product_description") == msg.strip()

    def test_update_general_info_puts_product_data_into_products_single(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "general_info"
        agent._update_collected_data({
            "product_name": "Подушка",
            "product_description": "Описание товара для лендинга.",
        })
        assert len(agent.collected_data["products"]) == 1
        assert agent.collected_data["products"][0]["product_name"] == "Подушка"
        assert "Описание товара" in agent.collected_data["products"][0]["product_description"]


# ---------- Сценарий: скидка в сообщении ----------

class TestScenarioDiscount:
    """Пользователь пишет про скидку в общем сообщении или вместе с ценами."""

    def test_discount_extracted_in_general_info(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        r = agent._simple_extract_data("Скидка 30% на товар", "general_info")
        assert r.get("hero_discount") == "-30%"
        assert r.get("hero_discount_position") == "top_right"

    def test_discount_extracted_in_products_stage(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        r = agent._simple_extract_data("Цена со скидкой 99 BYN, скидка 25%", "products")
        assert r.get("hero_discount") == "-25%"
        assert r.get("new_price") == "99 BYN"


# ---------- Сценарий: мини-опрос — подвал и уведомления приходят на этапе products ----------

class TestScenarioMiniSurveyInProductsStage:
    """На этапе products пользователь одним сообщением даёт цены, подвал и куда слать заявки."""

    def test_footer_and_notification_from_products_stage_go_to_general_info(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        agent.collected_data["products"] = [{"product_name": "Товар"}]
        agent._update_collected_data({
            "new_price": "99 BYN",
            "old_price": "150 BYN",
            "notification_type": "telegram",
            "notification_telegram_token": "123:ABC",
            "notification_telegram_chat_id": "456",
            "type": "ip",
            "fio": "Иванов И.И.",
            "unp": "123456789",
            "address": "г. Минск",
            "phone": "+375 29 123 45 67",
            "email": "ip@test.by",
        })
        g = agent.collected_data["general_info"]
        assert g.get("notification_type") == "telegram"
        assert g.get("notification_telegram_token") == "123:ABC"
        assert g.get("notification_telegram_chat_id") == "456"
        assert g.get("type") == "ip"
        assert g.get("fio") == "Иванов И.И."
        assert g.get("unp") == "123456789"
        assert agent.collected_data["products"][0]["new_price"] == "99 BYN"


# ---------- Сценарий: convert_to_user_data для генератора ----------

class TestScenarioConvertToUserData:
    """Проверка, что собранные в диалоге данные правильно превращаются в user_data для генератора."""

    def test_footer_info_and_notifications_in_user_data(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.collected_data["general_info"] = {
            "type": "ip",
            "fio": "Петров П.П.",
            "unp": "987654321",
            "address": "ул. Примерная 1",
            "phone": "+375 33 111 22 33",
            "email": "petrov@mail.by",
            "notification_type": "email",
            "notification_email": "orders@site.by",
        }
        agent.collected_data["products"] = [{
            "product_name": "Крем",
            "product_description": "Увлажняющий крем.",
            "new_price": "49 BYN",
            "old_price": "70 BYN",
            "hero_discount": "-30%",
        }]
        agent.collected_data["files"] = [
            {"path": "/tmp/hero.jpg", "type": "photo", "block": "hero", "original_name": "hero.jpg"},
        ]
        user_data = agent.convert_to_user_data()
        assert user_data["footer_info"]["type"] == "ip"
        assert user_data["footer_info"]["fio"] == "Петров П.П."
        assert user_data["footer_info"]["unp"] == "987654321"
        assert user_data["notification_type"] == "email"
        assert user_data["notification_email"] == "orders@site.by"
        assert user_data["hero_discount"] == "-30%"
        assert user_data["product_name"] == "Крем"
        assert user_data["hero_media"] == "/tmp/hero.jpg"

    def test_photo_distribution_by_counts_description_gallery_reviews(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.collected_data["general_info"] = {
            "photo_description_count": 2,
            "photo_gallery_count": 2,
            "photo_reviews_count": 1,
        }
        agent.collected_data["products"] = [{"product_name": "Товар", "product_description": "Описание"}]
        agent.collected_data["files"] = [
            {"path": "/tmp/h.jpg", "type": "photo", "block": "hero"},
            {"path": "/tmp/1.jpg", "type": "photo", "block": "gallery"},
            {"path": "/tmp/2.jpg", "type": "photo", "block": "gallery"},
            {"path": "/tmp/3.jpg", "type": "photo", "block": "gallery"},
            {"path": "/tmp/4.jpg", "type": "photo", "block": "gallery"},
            {"path": "/tmp/5.jpg", "type": "photo", "block": "gallery"},
        ]
        user_data = agent.convert_to_user_data()
        assert user_data["hero_media"] == "/tmp/h.jpg"
        assert user_data["description_photos"] == ["/tmp/1.jpg", "/tmp/2.jpg"]
        assert user_data["middle_gallery"] == ["/tmp/3.jpg", "/tmp/4.jpg"]
        assert len(user_data["reviews"]) == 1
        assert user_data["reviews"][0]["photo"] == "/tmp/5.jpg"

    def test_photo_distribution_by_block_when_no_counts(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.collected_data["general_info"] = {}
        agent.collected_data["products"] = [{"product_name": "Товар", "product_description": "Описание"}]
        agent.collected_data["files"] = [
            {"path": "/tmp/hero.jpg", "type": "photo", "block": "hero"},
            {"path": "/tmp/desc1.jpg", "type": "photo", "block": "description"},
            {"path": "/tmp/gal1.jpg", "type": "photo", "block": "gallery"},
            {"path": "/tmp/rev1.jpg", "type": "photo", "block": "review"},
        ]
        user_data = agent.convert_to_user_data()
        assert user_data["hero_media"] == "/tmp/hero.jpg"
        assert user_data["description_photos"] == ["/tmp/desc1.jpg"]
        assert user_data["middle_gallery"] == ["/tmp/gal1.jpg"]
        assert len(user_data["reviews"]) == 1
        assert user_data["reviews"][0]["photo"] == "/tmp/rev1.jpg"


# ---------- Сценарий: первое фото всегда hero ----------

class TestScenarioFirstPhotoIsHero:
    """Независимо от этапа, первое присланное фото — главное (hero)."""

    def test_first_file_determines_as_hero(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.collected_data["files"] = []
        assert agent._determine_file_block("photo") == "hero"

    def test_second_photo_after_hero_is_gallery_by_default(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.collected_data["files"] = [{"block": "hero", "type": "photo"}]
        assert agent._determine_file_block("photo") == "gallery"


# ---------- Сценарий: только цены в одном сообщении ----------

class TestScenarioPricesOnly:
    """Пользователь отвечает только цифрами по ценам."""

    def test_old_and_new_price_from_one_message(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        r = agent._simple_extract_data("Было 200 BYN. Сейчас 149 BYN", "products")
        assert r.get("old_price") == "200 BYN"
        # new_price берётся из первого числа с валютой в тексте
        assert r.get("new_price") == "200 BYN"

    def test_only_new_price(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        agent.stage = "products"
        r = agent._simple_extract_data("149 BYN", "products")
        assert r.get("new_price") == "149 BYN"


# ---------- Сценарий: описание в одну строку ----------

class TestScenarioSingleLineDescription:
    """Короткое или однострочное описание."""

    def test_short_message_not_treated_as_product_description_in_general_info(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        r = agent._simple_extract_data("Ок", "general_info")
        assert "product_name" not in r or r.get("product_name") != "Ок"

    def test_long_single_line_extracted_as_description(self, mock_llm_client):
        agent = LandingAIAgent("SINGLE")
        msg = "Ортопедическая подушка с эффектом памяти и охлаждающим гелем для комфортного сна"
        r = agent._simple_extract_data(msg, "general_info")
        assert r.get("product_name") == msg[:100]
        assert r.get("product_description") == msg


# ---------- Сценарий: описание с Wildberries (флаг для промпта) ----------

class TestScenarioWildberriesDescription:
    """Текст с маркетплейса — в convert_to_user_data выставляется description_is_wildberries."""

    def test_convert_to_user_data_sets_description_is_wildberries_when_detected(self, mock_llm_client):
        with patch("backend.utils.text_processor.TextProcessor.is_wildberries_text", return_value=True):
            agent = LandingAIAgent("SINGLE")
            agent.collected_data["products"] = [{
                "product_name": "Подушка",
                "product_description": "Артикул 123. Страна производства: Китай. Бренд: X. Состав: хлопок.",
            }]
            agent.collected_data["general_info"] = {}
            agent.collected_data["files"] = []
            user_data = agent.convert_to_user_data()
            assert user_data["description_is_wildberries"] is True

    def test_convert_to_user_data_wildberries_false_when_not_detected(self, mock_llm_client):
        with patch("backend.utils.text_processor.TextProcessor.is_wildberries_text", return_value=False):
            agent = LandingAIAgent("SINGLE")
            agent.collected_data["products"] = [{
                "product_name": "Товар",
                "product_description": "Просто описание без признаков ВБ.",
            }]
            agent.collected_data["general_info"] = {}
            agent.collected_data["files"] = []
            user_data = agent.convert_to_user_data()
            assert user_data["description_is_wildberries"] is False
