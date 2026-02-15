"""
Тесты для backend.utils.cache (PromptCache)
"""
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.utils.cache import PromptCache


@pytest.fixture
def temp_cache_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def cache_with_dir(temp_cache_dir):
    """Кэш с временной директорией (без патча Config)."""
    return PromptCache(cache_dir=temp_cache_dir, ttl_hours=24)


class TestPromptCache:
    def test_generate_cache_key_deterministic(self, cache_with_dir):
        user_data = {"product_name": "Товар", "new_price": "99", "old_price": "150"}
        key1 = cache_with_dir._generate_cache_key(user_data)
        key2 = cache_with_dir._generate_cache_key(user_data)
        assert key1 == key2
        assert len(key1) == 32

    def test_generate_cache_key_different_data_different_key(self, cache_with_dir):
        key1 = cache_with_dir._generate_cache_key({"product_name": "A"})
        key2 = cache_with_dir._generate_cache_key({"product_name": "B"})
        assert key1 != key2

    def test_get_miss_returns_none(self, cache_with_dir):
        result = cache_with_dir.get({"product_name": "X"})
        assert result is None

    def test_set_and_get(self, cache_with_dir):
        user_data = {"product_name": "Тест", "landing_type": "single"}
        prompt = "Тестовый промпт для кэша."
        cache_with_dir.set(user_data, prompt)
        result = cache_with_dir.get(user_data)
        assert result == prompt

    def test_get_cache_path(self, cache_with_dir):
        path = cache_with_dir._get_cache_path("abc123")
        assert path.endswith("abc123.json")
        assert cache_with_dir.cache_dir in path

    def test_clear_expired_empty_returns_zero(self, cache_with_dir):
        assert cache_with_dir.clear_expired() == 0

    def test_clear_all_empty_returns_zero(self, cache_with_dir):
        assert cache_with_dir.clear_all() == 0

    def test_clear_all_removes_files(self, cache_with_dir):
        cache_with_dir.set({"product_name": "A"}, "prompt1")
        cache_with_dir.set({"product_name": "B"}, "prompt2")
        count = cache_with_dir.clear_all()
        assert count == 2
        assert cache_with_dir.get({"product_name": "A"}) is None
        assert cache_with_dir.get({"product_name": "B"}) is None

    def test_set_on_exception_returns_false(self, cache_with_dir):
        with patch("builtins.open", side_effect=OSError("disk full")):
            ok = cache_with_dir.set({"product_name": "X"}, "prompt")
        assert ok is False

    def test_get_on_invalid_json_returns_none(self, cache_with_dir):
        user_data = {"product_name": "Y"}
        cache_with_dir.set(user_data, "valid")
        key = cache_with_dir._generate_cache_key(user_data)
        path = cache_with_dir._get_cache_path(key)
        Path(path).write_text("not json", encoding="utf-8")
        result = cache_with_dir.get(user_data)
        assert result is None
