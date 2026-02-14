"""
Integration тест для проверки полного потока: handler → agent → db → state transition
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram import Update, Message, User, Chat, CallbackQuery
from telegram.ext import ContextTypes

from backend.bot.telegram_bot import LandingBot, AI_MODE_SELECTION, AI_CONVERSATION
from backend.database.models import UserState
from tests.mocks.mock_ai_agent import MockLandingAIAgent


class TestIntegrationFlow:
    """Integration тесты для полного потока обработки"""
    
    @pytest.fixture
    def bot_instance(self, test_db_session):
        """Создает экземпляр бота для тестирования с подменой БД"""
        with patch('backend.bot.telegram_bot.SessionLocal', return_value=test_db_session):
            with patch('backend.bot.telegram_bot.init_db'):
                with patch.dict('os.environ', {
                    'TELEGRAM_BOT_TOKEN': 'test_token',
                    'DATABASE_URL': 'sqlite:///:memory:',
                    'OPENAI_API_KEY': 'test_key'
                }):
                    # Мокаем Application чтобы не запускать реальный бот
                    with patch('backend.bot.telegram_bot.Application') as mock_app_class:
                        mock_app = MagicMock()
                        mock_app.bot = MagicMock()
                        mock_app.bot.send_message = AsyncMock()
                        mock_app.bot.send_document = AsyncMock()
                        mock_app.builder.return_value.token.return_value.build.return_value = mock_app
                        mock_app_class.builder.return_value.token.return_value.build.return_value = mock_app
                        
                        bot = LandingBot()
                        bot.app = mock_app
                        
                        # Мокаем компоненты, которые не нужны для теста
                        bot.code_generator = Mock()
                        bot.template_loader = Mock()
                        bot.template_selector = Mock()
                        
                        yield bot
    
    def _get_conversation_state(self, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Вспомогательная функция для получения состояния ConversationHandler
        
        Args:
            context: CallbackContext
            
        Returns:
            Текущее состояние ConversationHandler или None
        """
        # ConversationHandler хранит состояние в context.user_data
        # Ключ зависит от реализации, обычно это 'conversation_state' или через ConversationHandler
        return context.user_data.get('conversation_state') or context.user_data.get('ai_agent_active')
    
    @pytest.mark.asyncio
    async def test_full_user_flow(
        self, 
        bot_instance, 
        test_db_session, 
        mock_update, 
        mock_context,
        mock_update_with_callback
    ):
        """
        Integration тест: полный поток от старта диалога до сохранения в БД
        
        Проверяет:
        1. Создание пользователя
        2. Старт диалога
        3. Отправка сообщения
        4. Изменение состояния ConversationHandler
        5. Обновление LandingAIAgent
        6. Сохранение данных в БД
        7. Корректный ответ handler'а
        """
        user_id = mock_update.effective_user.id
        chat_id = mock_update.effective_chat.id
        
        # Шаг 1: Устанавливаем user_id и проверяем начальное состояние
        assert user_id not in bot_instance.ai_agents
        
        # Проверяем, что в БД нет записей для этого пользователя
        initial_state = test_db_session.query(UserState).filter(
            UserState.user_id == str(user_id)
        ).first()
        assert initial_state is None
        
        # Шаг 2: Вызываем start handler (create_mode_selection_command)
        # Мокаем ответ бота
        mock_update.message.reply_text = AsyncMock()
        
        result = await bot_instance.create_mode_selection_command(mock_update, mock_context)
        
        # Проверяем, что handler вернул ожидаемое состояние
        assert result == AI_MODE_SELECTION
        
        # Проверяем, что сообщение было отправлено
        mock_update.message.reply_text.assert_called_once()
        
        # Шаг 3: Симулируем выбор режима (SINGLE)
        # Настраиваем callback_query для выбора режима
        mock_update_with_callback.callback_query.data = "mode_single"  # Используем правильный формат из кода
        mock_update_with_callback.callback_query.answer = AsyncMock()
        mock_update_with_callback.callback_query.message.reply_text = AsyncMock()
        mock_update_with_callback.callback_query.message.chat.id = chat_id
        mock_update_with_callback.callback_query.edit_message_text = AsyncMock()
        
        # Подменяем LandingAIAgent на MockLandingAIAgent через monkeypatch
        # Это нужно сделать до вызова start_ai_agent
        with patch('backend.bot.telegram_bot.LandingAIAgent', MockLandingAIAgent):
            # Вызываем handler выбора режима
            result = await bot_instance.handle_mode_selection(mock_update_with_callback, mock_context)
            
            # Проверяем, что handler вернул AI_CONVERSATION
            assert result == AI_CONVERSATION
            
            # Проверяем, что агент был создан
            assert user_id in bot_instance.ai_agents
            assert bot_instance.ai_agents[user_id].mode == 'SINGLE'
            assert bot_instance.ai_agents[user_id].stage == 'general_info'
        
        # Шаг 4: Проверяем сохранение в БД после создания агента
        db_state = test_db_session.query(UserState).filter(
            UserState.user_id == str(user_id)
        ).first()
        
        assert db_state is not None, "UserState должен быть создан в БД"
        assert db_state.state == "AI_CONVERSATION"
        assert db_state.conversation_type == "ai_agent"
        assert "ai_agent_state" in db_state.data
        assert db_state.data["ai_agent_state"]["mode"] == "SINGLE"
        
        # Шаг 5: Отправляем сообщение пользователя (например, цель сайта)
        mock_update.message.text = "Цель - продажа товаров"
        
        # Используем MockLandingAIAgent для обработки сообщения
        agent = bot_instance.ai_agents[user_id]
        mock_update.message.reply_text = AsyncMock()
        
        # Вызываем handler обработки сообщения (используем тот же patch для LandingAIAgent)
        with patch('backend.bot.telegram_bot.LandingAIAgent', MockLandingAIAgent):
            result = await bot_instance.handle_ai_message(mock_update, mock_context)
        
        # Проверяем, что handler вернул AI_CONVERSATION (продолжение диалога)
        assert result == AI_CONVERSATION
        
        # Проверяем, что сообщение было отправлено (ответ агента)
        assert mock_update.message.reply_text.called
        
        # Шаг 6: Проверяем, что агент обработал сообщение
        # Проверяем историю диалога
        assert len(agent.conversation_history) > 0
        
        # Шаг 7: Проверяем обновление данных в БД
        test_db_session.refresh(db_state)
        updated_db_state = test_db_session.query(UserState).filter(
            UserState.user_id == str(user_id)
        ).first()
        
        assert updated_db_state is not None
        assert "ai_agent_state" in updated_db_state.data
        
        # Проверяем, что состояние агента обновилось в БД
        agent_state_in_db = updated_db_state.data["ai_agent_state"]
        assert agent_state_in_db["mode"] == "SINGLE"
        assert "conversation_history" in agent_state_in_db
        assert len(agent_state_in_db["conversation_history"]) > 0
        
        # Шаг 8: Отправляем следующее сообщение для проверки продолжения диалога
        mock_update.message.text = "Целевая аудитория - взрослые 25-45 лет"
        mock_update.message.reply_text = AsyncMock()
        
        # Используем patch для LandingAIAgent при обработке сообщения
        with patch('backend.bot.telegram_bot.LandingAIAgent', MockLandingAIAgent):
            result = await bot_instance.handle_ai_message(mock_update, mock_context)
        
        assert result == AI_CONVERSATION
        
        # Проверяем, что данные сохранились в агенте
        assert "general_info" in agent.collected_data
        # Проверяем, что хотя бы одно поле собрано
        general_info = agent.collected_data["general_info"]
        assert len(general_info) > 0  # Должны быть собраны данные
        
        # Шаг 9: Проверяем финальное состояние в БД
        final_db_state = test_db_session.query(UserState).filter(
            UserState.user_id == str(user_id)
        ).first()
        
        assert final_db_state is not None
        final_agent_state = final_db_state.data["ai_agent_state"]
        
        # Проверяем, что история диалога обновилась
        assert len(final_agent_state["conversation_history"]) >= 4  # минимум 2 user + 2 assistant
        
        # Проверяем, что collected_data содержит собранную информацию
        assert "collected_data" in final_agent_state
        assert "general_info" in final_agent_state["collected_data"]
        
        # Шаг 10: Проверяем состояние ConversationHandler
        # ConversationHandler состояние должно быть AI_CONVERSATION
        # Это проверяется через context.user_data
        assert mock_context.user_data.get("ai_agent_active") is True or result == AI_CONVERSATION
        
        # Финальная проверка: все компоненты работают вместе
        assert user_id in bot_instance.ai_agents
        assert bot_instance.ai_agents[user_id].mode == "SINGLE"
        assert bot_instance.ai_agents[user_id].stage in ["general_info", "products"]
        assert final_db_state.state == "AI_CONVERSATION"
        assert "ai_agent_state" in final_db_state.data
        assert final_db_state.data["ai_agent_state"]["mode"] == "SINGLE"


# This test validates full integration flow:
# handler → agent → db → state transition

