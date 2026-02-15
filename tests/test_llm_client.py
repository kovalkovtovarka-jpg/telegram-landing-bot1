"""
Тесты для backend.generator.llm_client (LLMClient).
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.generator.llm_client import LLMClient


@pytest.fixture
def mock_config():
    with patch("backend.generator.llm_client.Config") as cfg:
        cfg.LLM_PROVIDER = "openai"
        cfg.LLM_MODEL = "gpt-4o"
        cfg.LLM_TEMPERATURE = 0.3
        cfg.LLM_MAX_TOKENS = 8000
        cfg.OPENAI_API_KEY = "sk-test"
        cfg.ANTHROPIC_API_KEY = ""
        cfg.GOOGLE_API_KEY = ""
        yield cfg


class TestLLMClientInit:
    def test_init_openai_sets_client(self, mock_config):
        with patch("backend.generator.llm_client.OpenAI") as MockOpenAI:
            client = LLMClient(api_key="sk-key", provider="openai")
            assert client.provider == "openai"
            MockOpenAI.assert_called_once_with(api_key="sk-key")

    def test_init_unknown_provider_raises(self, mock_config):
        with pytest.raises(ValueError) as exc_info:
            LLMClient(provider="unknown")
        assert "Неподдерживаемый" in str(exc_info.value) or "unknown" in str(exc_info.value)


class TestLLMClientParseResponse:
    def test_parse_response_json_block(self, mock_config):
        with patch("backend.generator.llm_client.OpenAI"):
            client = LLMClient(api_key="sk-x", provider="openai")
        response = '{"html": "<p>Hi</p>", "css": "p {}", "js": "console.log(1);"}'
        result = client._parse_response(response)
        assert result["html"] == "<p>Hi</p>"
        assert result["css"] == "p {}"
        assert "console.log" in result["js"]

    def test_parse_response_markdown_blocks(self, mock_config):
        with patch("backend.generator.llm_client.OpenAI"):
            client = LLMClient(api_key="sk-x", provider="openai")
        response = """
```html
<div>Hello</div>
```
```css
body { margin: 0; }
```
```javascript
function init() {}
```
"""
        result = client._parse_response(response)
        assert "Hello" in result["html"]
        assert "margin" in result["css"]
        assert "function init" in result["js"]

    def test_parse_response_returns_defaults_when_empty(self, mock_config):
        with patch("backend.generator.llm_client.OpenAI"):
            client = LLMClient(api_key="sk-x", provider="openai")
        result = client._parse_response("no code here")
        assert "html" in result
        assert "css" in result
        assert "js" in result


class TestLLMClientGenerateLanding:
    async def test_generate_landing_raises_when_client_none(self, mock_config):
        mock_config.OPENAI_API_KEY = ""
        with patch("backend.generator.llm_client.OpenAI"):
            client = LLMClient(provider="openai")
        assert client.client is None
        with pytest.raises(ValueError) as exc_info:
            await client.generate_landing("prompt")
        assert "ключ" in str(exc_info.value).lower() or "client" in str(exc_info.value).lower()


class TestLLMClientTestConnection:
    def test_test_connection_returns_false_when_client_none(self, mock_config):
        with patch("backend.generator.llm_client.OpenAI"):
            client = LLMClient(api_key="sk-x", provider="openai")
        client.client = None
        assert client.test_connection() is False
