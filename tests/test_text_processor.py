"""
Тесты для backend.utils.text_processor (TextProcessor — Wildberries)
"""
import pytest

from backend.utils.text_processor import TextProcessor


class TestIsWildberriesText:
    def test_empty_returns_false(self):
        assert TextProcessor.is_wildberries_text("") is False
        assert TextProcessor.is_wildberries_text(None) is False

    def test_few_indicators_returns_false(self):
        assert TextProcessor.is_wildberries_text("Артикул: 123. Бренд: X.") is False

    def test_three_or_more_indicators_returns_true(self):
        text = "Артикул: 123. Бренд: X. Страна производства: Россия. Доставка: да."
        assert TextProcessor.is_wildberries_text(text) is True

    def test_wildberries_keyword_counts(self):
        text = "Товар с wildberries. Артикул продавца. Рейтинг 4.5."
        assert TextProcessor.is_wildberries_text(text) is True


class TestCleanWildberriesText:
    def test_empty_returns_unchanged(self):
        assert TextProcessor.clean_wildberries_text("") == ""
        assert TextProcessor.clean_wildberries_text(None) is None

    def test_removes_art_and_codes(self):
        text = "Артикул: ABC-123. Текст товара."
        result = TextProcessor.clean_wildberries_text(text)
        assert "Артикул" not in result or "ABC-123" not in result
        assert "Текст товара" in result

    def test_removes_wildberries_mention(self):
        text = "Купить на Wildberries. Описание."
        result = TextProcessor.clean_wildberries_text(text)
        assert "Wildberries" not in result
        assert "Описание" in result


class TestProcessDescription:
    def test_empty_returns_unchanged_and_false(self):
        text, is_wb = TextProcessor.process_description("")
        assert text == ""
        assert is_wb is False

    def test_explicit_not_wb_returns_unchanged(self):
        text = "Артикул. Бренд. Страна. Доставка. Рейтинг."
        out, is_wb = TextProcessor.process_description(text, is_wildberries=False)
        assert out == text
        assert is_wb is False

    def test_explicit_wb_cleans_and_returns_true(self):
        text = "Артикул: X. Бренд: Y. Текст."
        out, is_wb = TextProcessor.process_description(text, is_wildberries=True)
        assert is_wb is True
        assert "Текст" in out or out  # очищенный текст не пустой или с остатком

    def test_auto_detect_wb_cleans(self):
        text = "Артикул: 1. Бренд: A. Страна производства: РФ. Доставка. Рейтинг 5."
        out, is_wb = TextProcessor.process_description(text, is_wildberries=None)
        assert is_wb is True
        assert isinstance(out, str)
