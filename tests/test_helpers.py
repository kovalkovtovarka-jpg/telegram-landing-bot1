"""
Тесты для backend.utils.helpers
"""
import os
import tempfile
import time
from pathlib import Path

import pytest

from backend.utils.helpers import ensure_dir, cleanup_old_files, format_file_size, sanitize_filename


class TestEnsureDir:
    def test_creates_missing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = os.path.join(tmp, "a", "b", "c")
            ensure_dir(sub)
            assert os.path.isdir(sub)

    def test_existing_directory_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_dir(tmp)
            assert os.path.isdir(tmp)


class TestCleanupOldFiles:
    def test_removes_old_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "old.txt")
            Path(path).write_text("x")
            # Сделать файл «старым»: изменить время создания (на Windows mtime)
            old_time = time.time() - (10 * 24 * 60 * 60)
            os.utime(path, (old_time, old_time))
            cleanup_old_files(tmp, days_old=7)
            assert not os.path.exists(path)

    def test_keeps_recent_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "new.txt")
            Path(path).write_text("x")
            cleanup_old_files(tmp, days_old=7)
            assert os.path.exists(path)


class TestFormatFileSize:
    def test_bytes(self):
        assert "100.0 B" == format_file_size(100)

    def test_kilobytes(self):
        assert "1.0 KB" == format_file_size(1024)

    def test_megabytes(self):
        assert "1.0 MB" == format_file_size(1024 * 1024)

    def test_gigabytes(self):
        assert "1.0 GB" == format_file_size(1024 * 1024 * 1024)

    def test_fractional(self):
        out = format_file_size(1536)
        assert "KB" in out
        assert "1.5" in out


class TestSanitizeFilename:
    def test_removes_forbidden_chars(self):
        assert sanitize_filename('file<>:"/\\|?*name.txt') == "filename.txt"

    def test_preserves_safe_chars(self):
        assert sanitize_filename("normal_name-123.txt") == "normal_name-123.txt"

    def test_truncates_long_filenames(self):
        long_name = "a" * 250
        result = sanitize_filename(long_name)
        assert len(result) == 200
        assert result == "a" * 200

    def test_empty_after_removal(self):
        result = sanitize_filename('<>:"/\\|?*')
        assert result == ""
