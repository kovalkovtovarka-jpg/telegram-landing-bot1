"""
Тесты для backend.utils.prompt_compressor
"""
import pytest
from unittest.mock import patch

from backend.utils.prompt_compressor import PromptCompressor


class TestCompressDescription:
    def test_empty_returns_unchanged(self):
        assert PromptCompressor.compress_description("") == ""
        assert PromptCompressor.compress_description(None) is None

    def test_short_description_unchanged(self):
        short = "Короткий текст."
        assert PromptCompressor.compress_description(short) == short

    def test_long_description_truncated_at_sentence(self):
        long_text = "Первое предложение. " + "Слово " * 200 + "Последнее предложение."
        result = PromptCompressor.compress_description(long_text, max_length=100)
        assert len(result) <= 103  # 100 + "..."
        assert result.endswith(".") or result.endswith("...")

    def test_custom_max_length(self):
        text = "Один. Два. Три. " + "Четыре. " * 50
        result = PromptCompressor.compress_description(text, max_length=30)
        assert len(result) <= 33

    def test_sentence_end_in_last_30_percent(self):
        # Если последняя точка в последних 30% - обрезаем по ней
        base = "Начало. " * 10
        end = " Конец предложения."
        text = base + end
        result = PromptCompressor.compress_description(text, max_length=len(base) + 5)
        assert "." in result


class TestCompressReviews:
    def test_empty_returns_unchanged(self):
        assert PromptCompressor.compress_reviews([]) == []
        assert PromptCompressor.compress_reviews(None) is None

    def test_dict_reviews_compressed(self):
        reviews = [
            {"text": "Короткий отзыв.", "author": "A"},
            {"text": "Длинный " * 100, "author": "B"},
        ]
        result = PromptCompressor.compress_reviews(reviews, max_reviews=5, max_length_per_review=50)
        assert len(result) == 2
        assert len(result[0]["text"]) <= 53
        assert len(result[1]["text"]) <= 53

    def test_str_reviews_compressed(self):
        reviews = ["Короткий.", "Очень длинный отзыв. " * 50]
        result = PromptCompressor.compress_reviews(reviews, max_length_per_review=30)
        assert len(result) == 2
        assert len(result[1]) <= 33

    def test_max_reviews_limit(self):
        reviews = [{"text": f"Отзыв {i}.", "id": i} for i in range(10)]
        result = PromptCompressor.compress_reviews(reviews, max_reviews=3)
        assert len(result) == 3


class TestCompressUserData:
    def test_empty_user_data_unchanged(self):
        data = {}
        assert PromptCompressor.compress_user_data(data) == {}

    def test_description_compressed(self):
        data = {"description": "Короткий."}
        result = PromptCompressor.compress_user_data(data)
        assert result["description"] == "Короткий."

    def test_reviews_compressed(self):
        data = {"reviews": [{"text": "Один. " * 100}]}
        result = PromptCompressor.compress_user_data(data)
        assert len(result["reviews"]) == 1
        assert len(result["reviews"][0]["text"]) <= 203

    def test_characteristics_list_truncated(self):
        data = {"characteristics_list": [f"x{i}" for i in range(20)]}
        result = PromptCompressor.compress_user_data(data)
        assert len(result["characteristics_list"]) == 10


class TestCheckAndCompressPrompt:
    def test_short_prompt_unchanged(self):
        short = "Короткий промпт."
        with patch.object(PromptCompressor, "MAX_PROMPT_LENGTH", 50000):
            result, was_compressed = PromptCompressor.check_and_compress_prompt(short)
        assert result == short
        assert was_compressed is False

    def test_long_prompt_compressed(self):
        long_prompt = "A" * 20000
        with patch.object(PromptCompressor, "MAX_PROMPT_LENGTH", 1000):
            result, was_compressed = PromptCompressor.check_and_compress_prompt(long_prompt)
        assert was_compressed is True
        assert len(result) <= len(long_prompt)
