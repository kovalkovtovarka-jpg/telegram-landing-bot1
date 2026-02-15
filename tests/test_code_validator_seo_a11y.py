"""
Тесты для SEO и accessibility проверок CodeValidator.
"""
import pytest

from backend.generator.code_validator import CodeValidator


class TestCodeValidatorSeo:
    """Тесты _validate_seo."""

    def test_missing_title_error(self):
        v = CodeValidator()
        html = "<html><body><h1>Test</h1></body></html>"
        errors, warnings = v._validate_seo(html)
        assert any("title" in e.lower() for e in errors)

    def test_short_title_warning(self):
        v = CodeValidator()
        html = "<html><head><title>Короткий</title></head><body></body></html>"
        errors, warnings = v._validate_seo(html)
        assert any("короткий" in w.lower() or "short" in w.lower() for w in warnings)

    def test_long_title_warning(self):
        v = CodeValidator()
        long_title = "A" * 80
        html = f"<html><head><title>{long_title}</title></head><body></body></html>"
        errors, warnings = v._validate_seo(html)
        assert any("длинный" in w.lower() or "long" in w.lower() for w in warnings)

    def test_missing_meta_description_warning(self):
        v = CodeValidator()
        html = "<html><head><title>Нормальный заголовок страницы</title></head><body></body></html>"
        errors, warnings = v._validate_seo(html)
        assert any("description" in w.lower() for w in warnings)

    def test_missing_lang_warning(self):
        v = CodeValidator()
        html = "<html><head><title>Test</title></head><body><h1>X</h1></body></html>"
        errors, warnings = v._validate_seo(html)
        assert any("lang" in w.lower() for w in warnings)

    def test_no_h1_warning(self):
        v = CodeValidator()
        html = "<html lang='ru'><head><title>Test</title></head><body><p>No H1</p></body></html>"
        errors, warnings = v._validate_seo(html)
        assert any("h1" in w.lower() for w in warnings)


class TestCodeValidatorAccessibility:
    """Тесты _validate_accessibility."""

    def test_image_without_alt_error(self):
        v = CodeValidator()
        html = "<html><body><img src='x.jpg'></body></html>"
        errors, warnings = v._validate_accessibility(html)
        assert any("alt" in e.lower() for e in errors)

    def test_image_with_alt_no_error(self):
        v = CodeValidator()
        html = "<html><body><img src='x.jpg' alt='Описание'></body></html>"
        errors, _ = v._validate_accessibility(html)
        assert not any("alt" in e.lower() for e in errors)

    def test_few_semantic_tags_warning(self):
        v = CodeValidator()
        html = "<html><body><div>Only one semantic tag</div></body></html>"
        errors, warnings = v._validate_accessibility(html)
        assert any("семантич" in w.lower() or "semantic" in w.lower() or "тегов" in w for w in warnings)
