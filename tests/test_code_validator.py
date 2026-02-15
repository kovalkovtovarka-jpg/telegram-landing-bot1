"""
Тесты для backend.generator.code_validator (CodeValidator)
"""
import pytest

from backend.generator.code_validator import CodeValidator


# Минимальный валидный HTML/CSS/JS по правилам валидатора
VALID_HTML = """<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><title>Товар</title>
<link rel="stylesheet" href="css/style.css"></head>
<body>
<div class="container"><h1>Товар</h1><p>Описание</p>
<span class="old-price">150</span><span class="new-price">99</span>
<form action="send.php" method="POST">
<input name="name" placeholder="Имя"><input name="phone" placeholder="Телефон">
<button type="submit">Заказать</button></form></div>
<script src="script.js"></script></body>
</html>"""

VALID_CSS = "body { margin: 0; } " + "/* x */\n" * 50  # минимум 100 символов и структура
VALID_JS = "// Timer countdown for landing\nfunction init() { var x = 1; }"  # countdown/timer + скобки


class TestCodeValidatorValidate:
    """Тесты основного метода validate()"""

    def test_valid_code_passes(self):
        validator = CodeValidator()
        code = {
            "html": VALID_HTML,
            "css": VALID_CSS,
            "js": VALID_JS,
        }
        result = validator.validate(code)
        assert result["valid"] is True
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)

    def test_empty_html_fails(self):
        validator = CodeValidator()
        result = validator.validate({"html": "", "css": "x", "js": "x"})
        assert result["valid"] is False
        assert any("HTML" in e for e in result["errors"])

    def test_missing_html_tag_fails(self):
        validator = CodeValidator()
        result = validator.validate({
            "html": "<div>no html/head/body</div>",
            "css": "a{}",
            "js": "var x = 1;",
        })
        assert result["valid"] is False
        assert any("html" in e.lower() or "body" in e.lower() for e in result["errors"])

    def test_css_brace_mismatch_fails(self):
        validator = CodeValidator()
        code = {
            "html": VALID_HTML,
            "css": "body { margin: 0; ",  # нет закрывающей }
            "js": VALID_JS,
        }
        result = validator.validate(code)
        assert result["valid"] is False
        assert any("скобок" in e or "CSS" in e for e in result["errors"])

    def test_js_brace_mismatch_fails(self):
        validator = CodeValidator()
        code = {
            "html": VALID_HTML,
            "css": VALID_CSS,
            "js": "function x( { return 1; }",  # лишняя (
        }
        result = validator.validate(code)
        assert result["valid"] is False
        assert any("скобок" in e or "JS" in e for e in result["errors"])

    def test_required_form_and_timer_fail(self):
        """Короткий HTML без формы и без таймера в JS даёт ошибки"""
        validator = CodeValidator()
        code = {
            "html": "<!DOCTYPE html><html><head><title>x</title></head><body><p>text</p></body></html>",
            "css": "a { b: 1; }\n" * 10,
            "js": "var x = 1;",
        }
        result = validator.validate(code)
        assert result["valid"] is False
        errors_text = " ".join(result["errors"]).lower()
        assert "send.php" in errors_text or "форм" in errors_text or "timer" in errors_text or "countdown" in errors_text


class TestCodeValidatorRequiredElements:
    """Тесты проверки обязательных элементов через validate()"""

    def test_html_too_short_fails(self):
        validator = CodeValidator()
        result = validator.validate({
            "html": "<html><body><p>x</p></body></html>",
            "css": "x" * 100,
            "js": "x" * 50,
        })
        assert result["valid"] is False
        assert any("коротк" in e.lower() for e in result["errors"])

    def test_css_too_short_fails(self):
        validator = CodeValidator()
        result = validator.validate({
            "html": VALID_HTML,
            "css": "x",
            "js": VALID_JS,
        })
        assert result["valid"] is False
        assert any("CSS" in e and "коротк" in e for e in result["errors"])
