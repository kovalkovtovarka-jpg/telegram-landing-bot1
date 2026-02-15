"""
Тесты для backend.utils.file_validator
"""
import os
import tempfile
from pathlib import Path

import pytest

from backend.utils.file_validator import (
    get_file_signature,
    detect_mime_type,
    validate_file_type,
    validate_image_file,
    validate_video_file,
    validate_media_file,
)


class TestGetFileSignature:
    def test_returns_first_bytes(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(b"hello world")
            path = f.name
        try:
            assert get_file_signature(path, 5) == b"hello"
            assert get_file_signature(path, 100) == b"hello world"
        finally:
            os.unlink(path)

    def test_nonexistent_file_returns_empty(self):
        assert get_file_signature("/nonexistent/path/file.bin") == b""

    def test_max_bytes_respected(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(b"abcdefgh")
            path = f.name
        try:
            assert get_file_signature(path, 3) == b"abc"
        finally:
            os.unlink(path)


class TestDetectMimeType:
    def test_nonexistent_returns_none(self):
        assert detect_mime_type("/nonexistent/file.jpg") is None

    def test_jpeg_by_signature(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF")
            path = f.name
        try:
            assert detect_mime_type(path) == "image/jpeg"
        finally:
            os.unlink(path)

    def test_png_by_signature(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
            path = f.name
        try:
            assert detect_mime_type(path) == "image/png"
        finally:
            os.unlink(path)

    def test_extension_fallback(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as f:
            f.write(b"GIF89a\x00\x00\x00")
            path = f.name
        try:
            assert detect_mime_type(path) == "image/gif"
        finally:
            os.unlink(path)


class TestValidateFileType:
    def test_nonexistent_returns_false_and_message(self):
        ok, msg = validate_file_type("/nonexistent/file.jpg", ["image/jpeg"])
        assert ok is False
        assert "не существует" in msg or "exist" in msg.lower()

    def test_allowed_type_returns_true(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"\xff\xd8\xff")
            path = f.name
        try:
            ok, msg = validate_file_type(path, ["image/jpeg"])
            assert ok is True
            assert msg is None
        finally:
            os.unlink(path)

    def test_disallowed_type_returns_false(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"\xff\xd8\xff")
            path = f.name
        try:
            ok, msg = validate_file_type(path, ["image/png"])
            assert ok is False
            assert msg is not None
        finally:
            os.unlink(path)


class TestValidateImageFile:
    def test_valid_jpeg(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"\xff\xd8\xff")
            path = f.name
        try:
            ok, msg = validate_image_file(path)
            assert ok is True
            assert msg is None
        finally:
            os.unlink(path)

    def test_invalid_type_returns_false(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"not an image")
            path = f.name
        try:
            ok, msg = validate_image_file(path)
            assert ok is False
        finally:
            os.unlink(path)


class TestValidateVideoFile:
    def test_mp4_signature(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00")
            path = f.name
        try:
            ok, msg = validate_video_file(path)
            assert ok is True
        finally:
            os.unlink(path)

    def test_nonexistent_returns_false(self):
        ok, msg = validate_video_file("/nonexistent/video.mp4")
        assert ok is False


class TestValidateMediaFile:
    def test_media_type_image_calls_validate_image(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"\xff\xd8\xff")
            path = f.name
        try:
            ok, _ = validate_media_file(path, media_type="image")
            assert ok is True
        finally:
            os.unlink(path)

    def test_media_type_video_calls_validate_video(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"\x00\x00\x00\x20ftypmp42")
            path = f.name
        try:
            ok, _ = validate_media_file(path, media_type="video")
            assert ok is True
        finally:
            os.unlink(path)

    def test_media_type_unknown_returns_false(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"\xff\xd8\xff")
            path = f.name
        try:
            ok, msg = validate_media_file(path, media_type="unknown")
            assert ok is False
            assert msg is not None
        finally:
            os.unlink(path)
