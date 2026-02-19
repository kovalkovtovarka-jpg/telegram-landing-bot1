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
        assert result["colors"]["primary"] == "#5b7c99"
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

    def test_prompt_has_new_structure_blocks_1_to_8(self, builder):
        """Промпт содержит новую структуру: БЛОК 1 … БЛОК 8 (шаблонный лендинг)."""
        user_data = {
            "landing_type": "single_product",
            "product_name": "Тест",
            "description_text": "Описание",
            "new_price": "99",
            "old_price": "150",
            "characteristics": ["Характеристика 1", "Характеристика 2", "Характеристика 3"],
            "footer_info": {"type": "ip", "fio": "Иванов И.И.", "unp": "123", "address": "ул. Test", "phone": "+375291234567", "email": "a@b.by", "schedule": "9-18"},
        }
        prompt = builder.build_prompt(user_data)
        assert "БЛОК 1" in prompt and "HERO" in prompt
        assert "БЛОК 2" in prompt
        assert "БЛОК 3" in prompt and "ОПИСАНИЕ" in prompt
        assert "БЛОК 4" in prompt and "СРЕДНЯЯ ФОРМА" in prompt
        assert "БЛОК 5" in prompt
        assert "БЛОК 6" in prompt and "ОТЗЫВЫ" in prompt
        assert "БЛОК 7" in prompt and "ДУБЛЬ" in prompt
        assert "БЛОК 8" in prompt and "ПОДВАЛ" in prompt
        assert "Порядок блоков" in prompt or "строгий порядок" in prompt

    def test_prompt_has_quality_wording_no_line_counts(self, builder):
        """Промпт требует качество кода (complete, production-ready), без требований по числу строк."""
        user_data = {
            "landing_type": "single_product",
            "product_name": "Товар",
            "description_text": "",
            "new_price": "99",
            "old_price": "150",
            "characteristics": ["А", "Б", "В"],
            "footer_info": {},
        }
        prompt = builder.build_prompt(user_data)
        # Должны быть формулировки про полноту/качество
        assert "complete" in prompt.lower() or "production-ready" in prompt.lower() or "полный" in prompt.lower()
        # Не должно быть жёстких требований по строкам
        assert "500+" not in prompt and "200+" not in prompt
        assert "минимум 500 строк" not in prompt and "минимум 200 строк" not in prompt
        assert "МИНИМУМ 500" not in prompt and "МИНИМУМ 200" not in prompt

    def test_prompt_describes_block_order(self, builder):
        """Промпт задаёт порядок блоков: Hero, описание, средняя форма, галерея, отзывы, дубль hero, подвал."""
        user_data = {
            "landing_type": "single_product",
            "product_name": "Товар",
            "description_text": "",
            "new_price": "99",
            "old_price": "150",
            "characteristics": ["А", "Б", "В"],
            "footer_info": {"type": "ip", "fio": "ФИО", "unp": "1", "address": "а", "phone": "1", "email": "e@e.by", "schedule": ""},
        }
        prompt = builder.build_prompt(user_data)
        assert "Hero" in prompt or "HERO" in prompt
        assert "подвал" in prompt.lower() or "ПОДВАЛ" in prompt or "ИП" in prompt or "ООО" in prompt
        assert "дублируется" in prompt.lower() or "дубликат" in prompt.lower()
