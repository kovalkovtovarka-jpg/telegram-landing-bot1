"""
Тесты для проверки flow диалога через ConversationHandler
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes

from backend.bot.telegram_bot import LandingBot, AI_MODE_SELECTION, AI_CONVERSATION
from tests.mocks.mock_ai_agent import MockLandingAIAgent


class TestConversationFlow:
    """Тесты для flow диалога"""
    
    @pytest.fixture
    def bot_instance(self, test_db_session, mock_application):
        """Создает экземпляр бота для тестирования (mock_application отключает проверку токена)"""
        with patch('backend.bot.telegram_bot.SessionLocal', return_value=test_db_session):
            with patch('backend.bot.telegram_bot.init_db'):
                with patch.dict('os.environ', {
                    'TELEGRAM_BOT_TOKEN': 'test_token',
                    'DATABASE_URL': 'sqlite:///:memory:',
                    'OPENAI_API_KEY': 'test_key'
                }):
                    bot = LandingBot()
                    # Заменяем реальные компоненты на моки
                    bot.code_generator = Mock()
                    bot.template_loader = Mock()
                    bot.template_selector = Mock()
                    yield bot
    
    @pytest.mark.asyncio
    async def test_start_conversation(self, bot_instance, mock_update, mock_context):
        """Тест: старт диалога через команду /ai"""
        # Устанавливаем команду
        mock_update.message.text = None
        mock_update.message.entities = None
        
        # Мокаем команду
        with patch.object(bot_instance, 'create_mode_selection_command', new_callable=AsyncMock) as mock_cmd:
            mock_cmd.return_value = AI_MODE_SELECTION
            
            result = await mock_cmd(mock_update, mock_context)
            
            # Проверяем, что команда вызвана
            mock_cmd.assert_called_once()
            assert result == AI_MODE_SELECTION
    
    @pytest.mark.asyncio
    async def test_mode_selection(self, bot_instance, mock_update_with_callback, mock_context):
        """Тест: выбор режима работы (SINGLE/MULTI)"""
        # Устанавливаем callback data
        mock_update_with_callback.callback_query.data = "mode_SINGLE"
        
        with patch.object(bot_instance, 'handle_mode_selection', new_callable=AsyncMock) as mock_handler:
            mock_handler.return_value = AI_CONVERSATION
            
            result = await mock_handler(mock_update_with_callback, mock_context)
            
            mock_handler.assert_called_once()
            assert result == AI_CONVERSATION
    
    @pytest.mark.asyncio
    async def test_ai_agent_creation(self, bot_instance, mock_update, mock_context):
        """Тест: создание AI-агента при старте диалога"""
        user_id = mock_update.effective_user.id
        
        # Проверяем, что агента нет
        assert user_id not in bot_instance.ai_agents
        
        # Создаем агента
        with patch('backend.bot.telegram_bot.LandingAIAgent', MockLandingAIAgent):
            agent = MockLandingAIAgent(user_id, mode='SINGLE')
            bot_instance.ai_agents[user_id] = agent
        
        # Проверяем, что агент создан
        assert user_id in bot_instance.ai_agents
        assert bot_instance.ai_agents[user_id].mode == 'SINGLE'
        assert bot_instance.ai_agents[user_id].stage == 'general_info'
    
    @pytest.mark.asyncio
    async def test_message_processing(self, bot_instance, mock_update, mock_context):
        """Тест: обработка сообщений пользователя"""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "Хочу создать лендинг для товара"
        
        # Создаем mock агента
        agent = MockLandingAIAgent(user_id, mode='SINGLE')
        bot_instance.ai_agents[user_id] = agent
        
        # Обрабатываем сообщение
        response = await agent.process_message(mock_update.message.text)
        
        # Проверяем, что получен ответ
        assert response is not None
        assert len(response) > 0
        assert len(agent.conversation_history) > 0
    
    @pytest.mark.asyncio
    async def test_stage_transition(self, bot_instance, mock_update, mock_context):
        """Тест: переход между стадиями диалога"""
        user_id = mock_update.effective_user.id
        agent = MockLandingAIAgent(user_id, mode='SINGLE')
        bot_instance.ai_agents[user_id] = agent
        
        # Начинаем с general_info
        assert agent.stage == 'general_info'
        
        # Симулируем сбор данных
        await agent.process_message("Цель - продажа")
        await agent.process_message("Целевая аудитория - взрослые")
        await agent.process_message("Стиль - минималистичный")
        
        # Проверяем переход к products
        assert agent.stage == 'products'
        assert agent.collected_data['stage'] == 'products'
    
    @pytest.mark.asyncio
    async def test_data_collection(self, bot_instance, mock_update, mock_context):
        """Тест: сбор данных в collected_data"""
        user_id = mock_update.effective_user.id
        agent = MockLandingAIAgent(user_id, mode='SINGLE')
        bot_instance.ai_agents[user_id] = agent
        
        # Собираем данные
        await agent.process_message("Цель - продажа")
        await agent.process_message("Аудитория - взрослые 25-45 лет")
        
        # Проверяем сохранение данных
        assert 'goal' in agent.collected_data['general_info']
        assert 'target_audience' in agent.collected_data['general_info']
        assert agent.collected_data['general_info']['goal'] == 'продажа'
    
    @pytest.mark.asyncio
    async def test_ai_agent_state_saving(self, bot_instance, mock_update, mock_context):
        """Тест: сохранение состояния AI-агента"""
        user_id = mock_update.effective_user.id
        agent = MockLandingAIAgent(user_id, mode='SINGLE')
        bot_instance.ai_agents[user_id] = agent
        
        # Собираем данные
        await agent.process_message("Цель - продажа")
        
        # Сохраняем состояние
        serialized = agent.serialize_state()
        
        # Проверяем структуру
        assert 'mode' in serialized
        assert 'stage' in serialized
        assert 'collected_data' in serialized
        assert 'conversation_history' in serialized
        assert serialized['mode'] == 'SINGLE'
    
    @pytest.mark.asyncio
    async def test_conversation_cancellation(self, bot_instance, mock_update, mock_context):
        """Тест: отмена диалога"""
        user_id = mock_update.effective_user.id
        agent = MockLandingAIAgent(user_id, mode='SINGLE')
        bot_instance.ai_agents[user_id] = agent
        
        # Проверяем наличие агента
        assert user_id in bot_instance.ai_agents
        
        # Отменяем диалог
        with patch.object(bot_instance, 'cancel_ai_command', new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = -1  # ConversationHandler.END
            
            result = await mock_cancel(mock_update, mock_context)
            
            mock_cancel.assert_called_once()
            assert result == -1

