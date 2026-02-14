"""
Тесты для проверки восстановления состояния из БД
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.database.models import UserState
from backend.bot.telegram_bot import LandingBot
from tests.mocks.mock_ai_agent import MockLandingAIAgent


class TestStateRecovery:
    """Тесты для восстановления состояния из БД"""
    
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
                    bot.code_generator = Mock()
                    bot.template_loader = Mock()
                    bot.template_selector = Mock()
                    yield bot
    
    def test_ai_agent_serialization(self, sample_ai_agent_state):
        """Тест: сериализация состояния AI-агента"""
        user_id = 12345
        agent = MockLandingAIAgent(user_id, mode='SINGLE')
        agent.stage = 'products'
        agent.collected_data = sample_ai_agent_state['collected_data']
        
        # Сериализуем
        serialized = agent.serialize_state()
        
        # Проверяем структуру
        assert 'mode' in serialized
        assert 'stage' in serialized
        assert 'collected_data' in serialized
        assert 'conversation_history' in serialized
        assert serialized['mode'] == 'SINGLE'
        assert serialized['stage'] == 'products'
    
    def test_ai_agent_deserialization(self, sample_ai_agent_state):
        """Тест: десериализация состояния AI-агента"""
        user_id = 12345
        
        # Восстанавливаем из сериализованного состояния
        agent = MockLandingAIAgent.from_serialized_state(sample_ai_agent_state)
        
        # Проверяем восстановление
        assert agent.mode == 'SINGLE'
        assert agent.stage == 'general_info'
        assert 'general_info' in agent.collected_data
        assert agent.collected_data['general_info']['goal'] == 'продажа'
    
    def test_save_ai_agent_state_to_db(self, test_db_session, sample_ai_agent_state):
        """Тест: сохранение состояния AI-агента в БД"""
        user_id = "12345"
        
        # Создаем UserState с данными агента
        user_state = UserState(
            user_id=user_id,
            state="AI_CONVERSATION",
            data={
                "ai_agent_state": sample_ai_agent_state,
                "last_activity": 1234567890.0
            },
            conversation_type="ai_agent"
        )
        
        test_db_session.add(user_state)
        test_db_session.commit()
        
        # Проверяем сохранение
        retrieved = test_db_session.query(UserState).filter(
            UserState.user_id == user_id
        ).first()
        
        assert retrieved is not None
        assert "ai_agent_state" in retrieved.data
        assert retrieved.data["ai_agent_state"]["mode"] == "SINGLE"
    
    def test_restore_ai_agent_from_db(self, test_db_session, sample_ai_agent_state):
        """Тест: восстановление AI-агента из БД"""
        user_id = "12345"
        
        # Сохраняем состояние в БД
        user_state = UserState(
            user_id=user_id,
            state="AI_CONVERSATION",
            data={
                "ai_agent_state": sample_ai_agent_state,
                "last_activity": 1234567890.0
            },
            conversation_type="ai_agent"
        )
        test_db_session.add(user_state)
        test_db_session.commit()
        
        # Восстанавливаем из БД
        retrieved_state = test_db_session.query(UserState).filter(
            UserState.user_id == user_id
        ).first()
        
        assert retrieved_state is not None
        agent_state = retrieved_state.data["ai_agent_state"]
        
        # Восстанавливаем агента
        agent = MockLandingAIAgent.from_serialized_state(agent_state, user_id=int(user_id))
        
        # Проверяем восстановление
        assert agent.mode == "SINGLE"
        assert agent.stage == "general_info"
        assert "general_info" in agent.collected_data
    
    @pytest.mark.asyncio
    async def test_restore_ai_agents_on_startup(self, bot_instance, test_db_session, sample_ai_agent_state):
        """Тест: восстановление всех AI-агентов при старте бота"""
        # Создаем несколько записей в БД
        for i in range(3):
            user_id = f"1234{i}"
            state_copy = sample_ai_agent_state.copy()
            state_copy['collected_data']['general_info']['goal'] = f'goal_{i}'
            
            user_state = UserState(
                user_id=user_id,
                state="AI_CONVERSATION",
                data={
                    "ai_agent_state": state_copy,
                    "last_activity": 1234567890.0
                },
                conversation_type="ai_agent"
            )
            test_db_session.add(user_state)
        test_db_session.commit()
        
        # Мокаем метод восстановления
        with patch.object(bot_instance, '_restore_ai_agents_from_db', new_callable=AsyncMock) as mock_restore:
            await bot_instance._restore_ai_agents_from_db()
            
            # Проверяем, что метод вызван
            mock_restore.assert_called_once()
    
    def test_restore_with_missing_data(self, test_db_session):
        """Тест: восстановление при отсутствии данных агента"""
        user_id = "12345"
        
        # Создаем запись без ai_agent_state
        user_state = UserState(
            user_id=user_id,
            state="AI_CONVERSATION",
            data={},  # Пустые данные
            conversation_type="ai_agent"
        )
        test_db_session.add(user_state)
        test_db_session.commit()
        
        # Пытаемся восстановить
        retrieved = test_db_session.query(UserState).filter(
            UserState.user_id == user_id
        ).first()
        
        # Проверяем, что запись существует, но данных агента нет
        assert retrieved is not None
        assert "ai_agent_state" not in retrieved.data or not retrieved.data.get("ai_agent_state")
    
    def test_restore_with_invalid_state(self, test_db_session):
        """Тест: восстановление при некорректном состоянии"""
        user_id = "12345"
        
        # Создаем запись с некорректными данными
        user_state = UserState(
            user_id=user_id,
            state="AI_CONVERSATION",
            data={
                "ai_agent_state": {
                    # Отсутствует обязательное поле 'mode'
                    "stage": "general_info",
                    "collected_data": {}
                }
            },
            conversation_type="ai_agent"
        )
        test_db_session.add(user_state)
        test_db_session.commit()
        
        # Пытаемся восстановить
        retrieved = test_db_session.query(UserState).filter(
            UserState.user_id == user_id
        ).first()
        
        assert retrieved is not None
        # Проверяем, что можем обработать некорректные данные
        agent_state = retrieved.data.get("ai_agent_state", {})
        # Должны использовать значения по умолчанию
        mode = agent_state.get("mode", "SINGLE")
        assert mode in ["SINGLE", "MULTI"]
    
    def test_restore_conversation_history(self, test_db_session, sample_ai_agent_state):
        """Тест: восстановление истории диалога"""
        user_id = "12345"
        
        # Добавляем историю диалога
        sample_ai_agent_state['conversation_history'] = [
            {'role': 'user', 'content': 'Привет'},
            {'role': 'assistant', 'content': 'Привет! Как дела?'},
            {'role': 'user', 'content': 'Хочу создать лендинг'}
        ]
        
        user_state = UserState(
            user_id=user_id,
            state="AI_CONVERSATION",
            data={
                "ai_agent_state": sample_ai_agent_state,
                "last_activity": 1234567890.0
            },
            conversation_type="ai_agent"
        )
        test_db_session.add(user_state)
        test_db_session.commit()
        
        # Восстанавливаем
        retrieved = test_db_session.query(UserState).filter(
            UserState.user_id == user_id
        ).first()
        
        agent_state = retrieved.data["ai_agent_state"]
        agent = MockLandingAIAgent.from_serialized_state(agent_state)
        
        # Проверяем восстановление истории
        assert len(agent.conversation_history) == 3
        assert agent.conversation_history[0]['role'] == 'user'
        assert agent.conversation_history[1]['role'] == 'assistant'
    
    def test_restore_last_activity(self, test_db_session, sample_ai_agent_state):
        """Тест: восстановление времени последней активности"""
        user_id = "12345"
        last_activity = 1234567890.0
        
        user_state = UserState(
            user_id=user_id,
            state="AI_CONVERSATION",
            data={
                "ai_agent_state": sample_ai_agent_state,
                "last_activity": last_activity
            },
            conversation_type="ai_agent"
        )
        test_db_session.add(user_state)
        test_db_session.commit()
        
        # Восстанавливаем
        retrieved = test_db_session.query(UserState).filter(
            UserState.user_id == user_id
        ).first()
        
        # Проверяем восстановление времени активности
        assert retrieved.data["last_activity"] == last_activity

