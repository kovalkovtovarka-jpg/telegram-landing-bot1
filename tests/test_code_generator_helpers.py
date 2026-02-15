"""
Тесты для вспомогательных методов CodeGenerator (без вызова LLM).
"""
import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from backend.generator.code_generator import CodeGenerator


@pytest.fixture
def templates_path(tmp_path):
    path = tmp_path / "landing-templates.json"
    path.write_text(json.dumps({"templates": {"t1": {"name": "Test"}}}), encoding="utf-8")
    return str(path)


@pytest.fixture
def generator(templates_path):
    with patch("backend.generator.code_generator.LLMClient"), \
         patch("backend.generator.code_generator.PromptBuilder"), \
         patch("backend.generator.code_generator.TemplateLoader"), \
         patch("backend.generator.code_generator.Config") as cfg:
        cfg.FILES_DIR = tempfile.gettempdir()
        gen = CodeGenerator(templates_path=templates_path)
    return gen


class TestCodeGeneratorBaseJs:
    def test_create_base_js_returns_string(self, generator):
        result = generator._create_base_js()
        assert isinstance(result, str)
        assert len(result) > 100

    def test_create_base_js_contains_countdown(self, generator):
        result = generator._create_base_js()
        assert "countdown" in result.lower() or "Countdown" in result
        assert "timer" in result.lower() or "Timer" in result

    def test_create_base_js_contains_phone_format(self, generator):
        result = generator._create_base_js()
        assert "phone" in result.lower() or "375" in result


class TestCodeGeneratorBaseCssWithColors:
    def test_create_base_css_with_colors_returns_string(self, generator):
        colors = {
            "primary": "#4f46e5",
            "secondary": "#10b981",
            "accent": "#06b6d4",
            "bg_dark": "#0f172a",
            "bg_darker": "#020617",
        }
        fonts = ("Inter", "Roboto")
        result = generator._create_base_css_with_colors(colors, fonts)
        assert isinstance(result, str)
        assert ":root" in result
        assert "--primary-color" in result
        assert "#4f46e5" in result
        assert "Inter" in result
        assert "Roboto" in result

    def test_create_base_css_with_colors_escapes_font_spaces(self, generator):
        colors = {
            "primary": "#000",
            "secondary": "#111",
            "accent": "#222",
            "bg_dark": "#333",
            "bg_darker": "#444",
        }
        fonts = ("Open Sans", "Source Sans 3")
        result = generator._create_base_css_with_colors(colors, fonts)
        assert "Open+Sans" in result or "Open Sans" in result
        assert "Source" in result
