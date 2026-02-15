"""
Тесты для template_selector (TemplateSelector).
"""
import pytest

from template_selector import TemplateSelector


# Минимальные данные для инициализации без файлов
MIN_TEMPLATES = {
    "templates": {
        "physical_single": {"name": "Один товар"},
        "b2b": {"name": "B2B"},
        "service_consultation": {"name": "Услуга"},
    }
}

MIN_LOGIC = {
    "decision_tree": {
        "step_1_product_type": {
            "question": "Что продаете?",
            "options": [{"id": "physical_product", "label": "Товар"}, {"id": "service", "label": "Услуга"}],
        },
        "template_selection": {
            "rules": [
                {"conditions": {"product_type": "physical_product"}, "template": "physical_single", "reason": "По умолчанию", "priority": 1},
            ]
        },
    },
    "quick_selection": {
        "keywords": {
            "physical_single": ["подушка", "товар", "landing"],
        }
    },
    "compatibility_matrix": {
        "matrix": {
            "physical_single": {"not_compatible_with": []},
        }
    },
}


@pytest.fixture
def selector():
    return TemplateSelector(MIN_TEMPLATES, MIN_LOGIC)


class TestTemplateSelector:
    def test_init_with_dicts(self):
        sel = TemplateSelector(MIN_TEMPLATES, MIN_LOGIC)
        assert sel.templates == MIN_TEMPLATES
        assert sel.logic == MIN_LOGIC
        assert sel.current_step == "step_1_product_type"

    def test_get_next_question_returns_first_step(self, selector):
        result = selector.get_next_question()
        assert result["type"] == "question"
        assert "question" in result
        assert "options" in result
        assert "Что продаете?" in result["question"]

    def test_set_answer_updates_user_data(self, selector):
        selector.set_answer("step_1_product_type", "physical_product")
        assert selector.user_data["step_1_product_type"] == "physical_product"

    def test_evaluate_condition_true(self, selector):
        selector.user_data["step_1_product_type"] = "physical_product"
        assert selector._evaluate_condition("step_1_product_type == 'physical_product'") is True

    def test_evaluate_condition_false(self, selector):
        selector.user_data["step_1_product_type"] = "service"
        assert selector._evaluate_condition("step_1_product_type == 'physical_product'") is False

    def test_select_template_b2b_priority(self, selector):
        selector.user_data["step_4_special_scenarios"] = ["b2b"]
        result = selector.select_template()
        assert result["type"] == "template"
        assert result["template"] == "b2b"
        assert "B2B" in result["reason"]

    def test_select_template_suggested(self, selector):
        selector.user_data["suggested_template"] = "service_consultation"
        result = selector.select_template()
        assert result["template"] == "service_consultation"

    def test_quick_select_found(self, selector):
        # Use ASCII keyword "landing" to avoid encoding issues across platforms
        result = selector.quick_select("I want a landing for my product")
        assert result is not None
        assert result["type"] == "template"
        assert result["template"] == "physical_single"

    def test_quick_select_not_found(self, selector):
        result = selector.quick_select("абвгд несуществующее")
        assert result is None

    def test_get_template_info(self, selector):
        info = selector.get_template_info("physical_single")
        assert info is not None
        assert info["name"] == "Один товар"
        assert selector.get_template_info("nonexistent") is None

    def test_check_compatibility_compatible(self, selector):
        result = selector.check_compatibility("physical_single", [])
        assert result["compatible"] is True
        assert result["warnings"] == []

    def test_get_recommended_modifications_seasonal(self, selector):
        mods = selector.get_recommended_modifications("t1", ["seasonal"])
        assert len(mods) >= 1
        assert any("сезонн" in m["description"].lower() or "цвет" in m["description"].lower() for m in mods)

    def test_reset(self, selector):
        selector.user_data["step_1_product_type"] = "x"
        selector.reset()
        assert selector.user_data == {}
        assert selector.current_step == "step_1_product_type"
