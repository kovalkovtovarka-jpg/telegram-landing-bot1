"""
Тесты для CodeGenerator (генерация лендинга с моками LLM и сохранения файлов)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.generator.code_generator import CodeGenerator


# Минимальный валидный ответ LLM (чтобы проходила валидация и не срабатывал fallback)
def _minimal_llm_response():
    html = """<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><title>Товар</title><link rel="stylesheet" href="css/style.css"></head>
<body><div class="container"><h1>Товар</h1><p>Описание</p><span class="old-price">150</span><span class="new-price">99</span>
<form action="send.php" method="POST"><input name="name" placeholder="Имя"><input name="phone" placeholder="Телефон"><button type="submit">Заказать</button></form></div></body>
</html>"""
    css = """:root { --primary-color: #4f46e5; --secondary-color: #10b981; --accent-color: #06b6d4; --dark-bg: #0f172a; --darker-bg: #020617; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', sans-serif; color: #fff; background: linear-gradient(135deg, var(--darker-bg) 0%, var(--dark-bg) 100%); min-height: 100vh; }
.container { max-width: 600px; margin: 0 auto; padding: 1rem; }
.old-price { text-decoration: line-through; color: #6b7280; }
.new-price { color: var(--primary-color); font-size: 2rem; font-weight: 900; }
@media (max-width: 768px) { .new-price { font-size: 1.5rem; } }
"""
    # Не менее 300 строк CSS для прохождения проверки - дополняем комментариями
    while css.count('\n') < 300:
        css += "/* placeholder line */\n"
    js = """// Timer countdown for landing
document.addEventListener('DOMContentLoaded', function() {
    var form = document.querySelector('form');
    if (form) form.addEventListener('submit', function(e) { e.preventDefault(); });
});
"""
    return {"html": html, "css": css, "js": js, "tokens_used": 1000}


class TestCodeGenerator:
    """Тесты для CodeGenerator"""

    @pytest.fixture
    def minimal_user_data(self):
        return {
            "landing_type": "single_product",
            "product_name": "Тестовый товар",
            "description_text": "Краткое описание",
            "new_price": "99",
            "old_price": "150",
            "characteristics": [],
            "footer_info": {},
        }

    @pytest.mark.asyncio
    async def test_generate_calls_llm_and_returns_success(self, minimal_user_data):
        """Генератор вызывает LLM и при валидном ответе возвращает success"""
        generator = CodeGenerator()
        generator.llm_client.generate_landing = AsyncMock(return_value=_minimal_llm_response())

        with patch.object(generator, "_save_files", new_callable=AsyncMock) as mock_save:
            mock_save.return_value = {"project_dir": "/tmp/test_project", "zip_file": "/tmp/test.zip"}

            with patch("backend.utils.cache.prompt_cache") as mock_cache:
                mock_cache.get.return_value = None
                mock_cache.set = MagicMock()

            with patch("backend.utils.prompt_compressor.PromptCompressor") as PC:
                PC.compress_user_data.return_value = minimal_user_data
                PC.check_and_compress_prompt.return_value = ("fake prompt", False)

            result = await generator.generate("single_product", minimal_user_data)

        assert result.get("success") is True
        assert "files" in result
        assert result["files"].get("zip_file") == "/tmp/test.zip"
        generator.llm_client.generate_landing.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_propagates_llm_error(self, minimal_user_data):
        """При ошибке LLM генератор возвращает success=False и текст ошибки"""
        generator = CodeGenerator()
        generator.llm_client.generate_landing = AsyncMock(side_effect=Exception("API key invalid"))

        with patch("backend.utils.cache.prompt_cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.set = MagicMock()
        with patch("backend.utils.prompt_compressor.PromptCompressor") as PC:
            PC.compress_user_data.return_value = minimal_user_data
            PC.check_and_compress_prompt.return_value = ("fake prompt", False)

        result = await generator.generate("single_product", minimal_user_data)

        assert result.get("success") is False
        assert "error" in result
        assert "API key" in result["error"] or "invalid" in result["error"]
        assert "generation_time" in result
