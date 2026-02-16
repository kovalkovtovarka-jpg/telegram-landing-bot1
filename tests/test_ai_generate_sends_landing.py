"""
Тесты сценария «Да, генерировать»: проверка, что бот при успешной генерации
отправляет пользователю архив с лендингом (send_document вызывается с zip).
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from backend.bot.telegram_bot import LandingBot, AI_CONVERSATION, ConversationHandler
from tests.mocks.mock_ai_agent import MockLandingAIAgent


@pytest.fixture
async def bot_with_mock_app(test_db_session, mock_application):
    """Бот с замоканным Application (app.bot.send_document = AsyncMock)."""
    with patch("backend.bot.telegram_bot.SessionLocal", return_value=test_db_session):
        with patch("backend.bot.telegram_bot.init_db"):
            with patch.dict("os.environ", {
                "TELEGRAM_BOT_TOKEN": "test_token",
                "DATABASE_URL": "sqlite:///:memory:",
                "OPENAI_API_KEY": "test_key",
            }):
                bot = LandingBot()
                bot.code_generator = MagicMock()
                bot.template_loader = MagicMock()
                bot.template_selector = MagicMock()
                yield bot


@pytest.fixture
def update_with_ai_generate_callback(mock_user, mock_chat, mock_callback_query):
    """Update с нажатием кнопки «Да, генерировать» (callback_data=ai_generate)."""
    mock_callback_query.data = "ai_generate"
    mock_callback_query.message.chat.id = 99999
    from telegram import Update
    update = Mock(spec=Update)
    update.update_id = 1
    update.message = None
    update.callback_query = mock_callback_query
    update.effective_user = mock_user
    update.effective_chat = mock_chat
    return update


@pytest.fixture
def agent_ready_for_generation(mock_user):
    """Агент с собранными данными: товар + хотя бы одно фото (чтобы прошла проверка has_photo)."""
    agent = MockLandingAIAgent(mock_user.id, mode="SINGLE")
    agent.stage = "generation"
    agent.collected_data["stage"] = "generation"
    agent.collected_data["products"] = [
        {
            "product_name": "Тестовый товар",
            "product_description": "Описание для лендинга.",
        }
    ]
    agent.collected_data["files"] = [
        {"path": "/tmp/test_hero.jpg", "type": "photo", "block": "hero", "original_name": "hero.jpg"}
    ]
    return agent


@pytest.mark.asyncio
async def test_handle_ai_generate_sends_document_when_generation_succeeds(
    bot_with_mock_app,
    update_with_ai_generate_callback,
    agent_ready_for_generation,
    mock_context,
    tmp_path,
):
    """
    При успешной генерации бот вызывает send_document с zip-файлом лендинга.
    """
    bot = bot_with_mock_app
    user_id = update_with_ai_generate_callback.effective_user.id
    chat_id = update_with_ai_generate_callback.callback_query.message.chat.id

    # Файл zip должен существовать (в коде проверяется os.path.exists(zip_file))
    zip_path = tmp_path / "project_abc12345.zip"
    zip_path.write_bytes(b"PK\x03\x04")  # минимальный zip-заголовок

    bot.ai_agents[user_id] = agent_ready_for_generation
    bot.ai_agents_last_activity[user_id] = 0
    bot.code_generator.generate = AsyncMock(return_value={
        "success": True,
        "files": {"zip_file": str(zip_path), "project_dir": str(tmp_path)},
        "generation_time": 5,
    })

    with patch("backend.bot.telegram_bot.rate_limiter") as mock_rate_limiter:
        mock_rate_limiter.check_db_rate_limit = AsyncMock(return_value=(True, 5))

        result = await bot.handle_ai_generate(update_with_ai_generate_callback, mock_context)

    assert result == ConversationHandler.END
    send_document = bot.app.bot.send_document
    send_document.assert_called_once()
    call_kw = send_document.call_args.kwargs
    assert call_kw.get("chat_id") == chat_id
    assert "document" in call_kw
    assert call_kw.get("caption", "").strip().startswith("✅")


@pytest.mark.asyncio
async def test_handle_ai_generate_does_not_send_document_when_generation_fails(
    bot_with_mock_app,
    update_with_ai_generate_callback,
    agent_ready_for_generation,
    mock_context,
):
    """
    При неуспешной генерации (success=False) бот не вызывает send_document.
    """
    bot = bot_with_mock_app
    user_id = update_with_ai_generate_callback.effective_user.id

    bot.ai_agents[user_id] = agent_ready_for_generation
    bot.ai_agents_last_activity[user_id] = 0
    bot.code_generator.generate = AsyncMock(return_value={
        "success": False,
        "error": "LLM API error",
        "generation_time": 1,
    })

    with patch("backend.bot.telegram_bot.rate_limiter") as mock_rate_limiter:
        mock_rate_limiter.check_db_rate_limit = AsyncMock(return_value=(True, 5))

        result = await bot.handle_ai_generate(update_with_ai_generate_callback, mock_context)

    assert result == AI_CONVERSATION
    bot.app.bot.send_document.assert_not_called()
    update_with_ai_generate_callback.callback_query.edit_message_text.assert_called()
    # Последний вызов edit_message_text — сообщение об ошибке пользователю
    last_call = update_with_ai_generate_callback.callback_query.edit_message_text.call_args
    text_sent = (last_call[0][0] if last_call[0] else last_call[1].get("text", ""))
    assert "Ошибка" in text_sent or "ошибка" in text_sent.lower()
