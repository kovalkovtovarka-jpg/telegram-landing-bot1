"""
Тесты для NewPromptBuilder (подбор стиля, цветов, построение промпта)
"""
import pytest
from backend.generator.prompt_builder_new import NewPromptBuilder


class TestNewPromptBuilder:
    """Тесты для NewPromptBuilder"""

    @pytest.fixture
    def builder(self):
        return NewPromptBuilder()

    def test_analyze_product_health_category(self, builder):
        """Категория health для товаров про сон/здоровье"""
        result = builder._analyze_product_and_suggest_style("Ортопедическая подушка", "для сна")
        assert result["category"] == "health"
        assert "primary" in result["colors"]
        assert result["colors"]["primary"] == "#4f46e5"
        assert len(result["fonts"]) == 2
        assert result["fonts"][0] == "Inter"

    def test_analyze_product_beauty_category(self, builder):
        """Категория beauty для косметики"""
        result = builder._analyze_product_and_suggest_style("Крем для лица", "уход")
        assert result["category"] == "beauty"
        assert result["colors"]["primary"] == "#ec4899"

    def test_analyze_product_tech_category(self, builder):
        """Категория tech для электроники"""
        result = builder._analyze_product_and_suggest_style("Смартфон", "новый")
        assert result["category"] == "tech"
        assert result["style"] == "modern"

    def test_analyze_product_general_category(self, builder):
        """Категория general для неизвестного товара"""
        result = builder._analyze_product_and_suggest_style("Разное", "")
        assert result["category"] == "general"
        assert "primary" in result["colors"]
        assert result["style"] in ("modern", "elegant")

    def test_build_prompt_minimal_user_data(self, builder):
        """Промпт строится при минимальных данных"""
        user_data = {
            "landing_type": "single_product",
            "product_name": "Тестовый товар",
            "description_text": "Описание",
            "new_price": "99",
            "old_price": "150",
            "characteristics": [],
            "footer_info": {},
        }
        prompt = builder.build_prompt(user_data)
        assert "Тестовый товар" in prompt
        assert "99" in prompt
        assert "ЦВЕТОВАЯ СХЕМА" in prompt or "primary" in prompt.lower()
        assert "general" in prompt or "Стиль" in prompt
        assert len(prompt) > 500

    def test_build_prompt_includes_preferred_colors(self, builder):
        """Предпочтительные цвета пользователя попадают в промпт"""
        user_data = {
            "landing_type": "single_product",
            "product_name": "Товар",
            "description_text": "",
            "new_price": "99",
            "old_price": "",
            "characteristics": [],
            "footer_info": {},
            "preferred_colors": "синий и белый",
        }
        prompt = builder.build_prompt(user_data)
        assert "синий и белый" in prompt
        assert "ПРЕДПОЧТЕНИЯ" in prompt or "предпочтительные" in prompt.lower()

    def test_get_format_variations_photo_jpeg(self, builder):
        """Вариации формата для photo/jpeg"""
        result = builder._get_format_variations("photo", "jpeg")
        assert "jpg" in result or "jpeg" in result

    def test_get_format_variations_video_mp4(self, builder):
        """Вариации формата для video/mp4"""
        result = builder._get_format_variations("video", "mp4")
        assert "mp4" in result.lower()
