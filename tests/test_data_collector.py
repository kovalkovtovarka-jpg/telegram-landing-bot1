"""
Тесты для backend.bot.data_collector
"""
import pytest
from unittest.mock import MagicMock

from backend.bot.data_collector import DataCollector


@pytest.fixture
def mock_template_loader():
    loader = MagicMock()
    loader.get_template.return_value = {
        "required_fields": {
            "product_name": "string",
            "old_price": "number",
            "new_price": "number",
            "product_description": "string",
        }
    }
    return loader


@pytest.fixture
def mock_template_selector():
    return MagicMock()


@pytest.fixture
def collector(mock_template_selector, mock_template_loader):
    return DataCollector(mock_template_selector, mock_template_loader)


class TestDataCollector:
    def test_get_required_fields_returns_from_loader(self, collector, mock_template_loader):
        mock_template_loader.get_template.return_value = {
            "required_fields": {"product_name": "string", "price": "number"}
        }
        fields = collector.get_required_fields("template_1")
        assert fields == {"product_name": "string", "price": "number"}
        mock_template_loader.get_template.assert_called_once_with("template_1")

    def test_get_required_fields_empty_when_no_template(self, collector, mock_template_loader):
        mock_template_loader.get_template.return_value = None
        assert collector.get_required_fields("missing") == {}

    def test_get_required_fields_empty_when_no_required_fields_key(self, collector, mock_template_loader):
        mock_template_loader.get_template.return_value = {}
        assert collector.get_required_fields("t") == {}

    def test_get_next_field_returns_first_missing(self, collector, mock_template_loader):
        mock_template_loader.get_template.return_value = {
            "required_fields": {"product_name": "string", "old_price": "number"}
        }
        next_id = collector.get_next_field("t", {})
        assert next_id == "product_name"
        next_id = collector.get_next_field("t", {"product_name": "Товар"})
        assert next_id == "old_price"

    def test_get_next_field_returns_none_when_all_filled(self, collector, mock_template_loader):
        mock_template_loader.get_template.return_value = {
            "required_fields": {"product_name": "string"}
        }
        next_id = collector.get_next_field("t", {"product_name": "Товар"})
        assert next_id is None

    def test_get_field_question_known_field(self, collector):
        q = collector.get_field_question("product_name", "t")
        assert "товар" in q.lower() or "название" in q.lower()

    def test_get_field_question_unknown_field(self, collector):
        q = collector.get_field_question("unknown_field", "t")
        assert "unknown_field" in q

    def test_validate_field_empty_fails(self, collector, mock_template_loader):
        mock_template_loader.get_template.return_value = {"required_fields": {"x": "string"}}
        ok, msg = collector.validate_field("x", "", "t")
        assert ok is False
        assert "пуст" in msg or "empty" in msg.lower()

    def test_validate_field_number_valid(self, collector, mock_template_loader):
        mock_template_loader.get_template.return_value = {"required_fields": {"price": "number"}}
        ok, msg = collector.validate_field("price", "100 BYN", "t")
        assert ok is True
        assert msg == ""

    def test_validate_field_number_invalid(self, collector, mock_template_loader):
        mock_template_loader.get_template.return_value = {"required_fields": {"price": "number"}}
        ok, msg = collector.validate_field("price", "not a number", "t")
        assert ok is False
        assert "числ" in msg or "number" in msg.lower()

    def test_validate_field_phone_must_start_with_375(self, collector, mock_template_loader):
        mock_template_loader.get_template.return_value = {"required_fields": {"phone": "string"}}
        ok, msg = collector.validate_field("phone", "1234567890", "t")
        assert ok is False
        assert "+375" in msg or "375" in msg
        ok, msg = collector.validate_field("phone", "+375291234567", "t")
        assert ok is True

    def test_format_collected_data_strips_prices(self, collector, mock_template_loader):
        data = {"product_name": "X", "old_price": " 100 BYN ", "new_price": " 80 BYN "}
        out = collector.format_collected_data(data, "t")
        assert out["old_price"] == "100 BYN"
        assert out["new_price"] == "80 BYN"

    def test_format_collected_data_computes_discount_percent(self, collector, mock_template_loader):
        data = {"old_price": "100 BYN", "new_price": "70 BYN"}
        out = collector.format_collected_data(data, "t")
        assert out["discount_percent"] == 30

    def test_format_collected_data_splits_features_benefits(self, collector, mock_template_loader):
        data = {"features": "a\nb\nc", "benefits": "x\ny"}
        out = collector.format_collected_data(data, "t")
        assert out["features"] == ["a", "b", "c"]
        assert out["benefits"] == ["x", "y"]

    def test_format_collected_data_adds_tiktok_pixel(self, collector, mock_template_loader):
        data = {}
        out = collector.format_collected_data(data, "t")
        assert "tiktok_pixel_id" in out
        assert out["tiktok_pixel_id"] == "D5L7UCBC77U0IF4JE7J0"
