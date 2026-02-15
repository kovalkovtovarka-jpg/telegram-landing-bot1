"""
Тесты для backend.utils.path_validator (безопасность путей, directory traversal)
"""
import os
import tempfile

import pytest

from backend.utils.path_validator import validate_file_path, sanitize_path, get_safe_path


class TestValidateFilePath:
    def test_path_inside_base_returns_true(self):
        with tempfile.TemporaryDirectory() as base:
            path = os.path.join(base, "sub", "file.txt")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w").close()
            assert validate_file_path(path, base) is True

    def test_path_outside_base_returns_false(self):
        with tempfile.TemporaryDirectory() as base:
            other = os.path.join(os.path.dirname(base), "other_dir", "file.txt")
            assert validate_file_path(other, base) is False

    def test_directory_traversal_returns_false(self):
        with tempfile.TemporaryDirectory() as base:
            # Путь с .. выходящий за base
            sub = os.path.join(base, "sub")
            os.makedirs(sub, exist_ok=True)
            traversal = os.path.join(sub, "..", "..", "etc", "passwd")
            assert validate_file_path(traversal, base) is False

    def test_base_itself_is_valid(self):
        with tempfile.TemporaryDirectory() as base:
            assert validate_file_path(base, base) is True


class TestSanitizePath:
    def test_valid_path_returns_normalized(self):
        with tempfile.TemporaryDirectory() as base:
            path = os.path.join(base, "a", "b", "file.txt")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            result = sanitize_path(path, base)
            assert result is not None
            assert "file.txt" in (result or "")

    def test_invalid_path_returns_none(self):
        with tempfile.TemporaryDirectory() as base:
            other = os.path.abspath(os.path.join(base, "..", "outside.txt"))
            result = sanitize_path(other, base)
            assert result is None


class TestGetSafePath:
    def test_returns_path_inside_base(self):
        with tempfile.TemporaryDirectory() as base:
            result = get_safe_path("index.html", base)
            assert result == os.path.normpath(os.path.join(base, "index.html"))
            assert validate_file_path(result, base) or result.startswith(base)

    def test_sanitizes_filename(self):
        with tempfile.TemporaryDirectory() as base:
            result = get_safe_path('file<>:"/\\|?*.txt', base)
            assert '<>:"/\\|?*' not in result
            assert os.path.basename(result) == "file.txt"

    def test_subdir_included(self):
        with tempfile.TemporaryDirectory() as base:
            result = get_safe_path("page.html", base, subdir="landings")
            assert "landings" in result
            assert result.endswith("page.html") or "page.html" in result
