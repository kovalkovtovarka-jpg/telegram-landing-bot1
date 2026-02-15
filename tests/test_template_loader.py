"""
Тесты для backend.generator.template_loader
"""
import json
import os
import tempfile

import pytest

from backend.generator.template_loader import TemplateLoader


@pytest.fixture
def templates_json(tmp_path):
    """Временный файл с шаблонами."""
    data = {
        "templates": {
            "single": {
                "name": "Один товар",
                "description": "Лендинг для одного товара",
                "use_case": "single_product",
                "required_fields": {"product_name": "string"},
            },
            "multi": {
                "name": "Несколько товаров",
                "description": "Карусель товаров",
                "use_case": "multi_product",
            },
        }
    }
    path = tmp_path / "landing-templates.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(path)


class TestTemplateLoader:
    def test_load_and_get_template(self, templates_json):
        loader = TemplateLoader(templates_path=templates_json)
        t = loader.get_template("single")
        assert t is not None
        assert t["name"] == "Один товар"
        assert t["use_case"] == "single_product"

    def test_get_template_missing_returns_none(self, templates_json):
        loader = TemplateLoader(templates_path=templates_json)
        assert loader.get_template("nonexistent") is None

    def test_get_all_templates(self, templates_json):
        loader = TemplateLoader(templates_path=templates_json)
        all_t = loader.get_all_templates()
        assert isinstance(all_t, dict)
        assert "single" in all_t
        assert "multi" in all_t
        assert len(all_t) == 2

    def test_get_template_list(self, templates_json):
        loader = TemplateLoader(templates_path=templates_json)
        lst = loader.get_template_list()
        assert isinstance(lst, list)
        assert len(lst) == 2
        ids = [x["id"] for x in lst]
        assert "single" in ids
        assert "multi" in ids
        for item in lst:
            assert "id" in item
            assert "name" in item
            assert "description" in item
            assert "use_case" in item

    def test_file_not_found_raises(self):
        with pytest.raises((FileNotFoundError, Exception)) as exc_info:
            TemplateLoader(templates_path="/nonexistent/templates.json")
        assert "не найден" in str(exc_info.value) or "Ошибка" in str(exc_info.value)

    def test_invalid_json_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not valid json {", encoding="utf-8")
        with pytest.raises(Exception):
            TemplateLoader(templates_path=str(path))
