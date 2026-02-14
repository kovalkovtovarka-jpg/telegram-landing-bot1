"""
Тесты для LandingAIAgent (используя MockLandingAIAgent)
"""
import pytest
from tests.mocks.mock_ai_agent import MockLandingAIAgent


class TestAIAgent:
    """Тесты для AI-агента"""
    
    def test_agent_initialization(self):
        """Тест: инициализация агента"""
        user_id = 12345
        agent = MockLandingAIAgent(user_id, mode='SINGLE')
        
        assert agent.user_id == user_id
        assert agent.mode == 'SINGLE'
        assert agent.stage == 'general_info'
        assert agent.collected_data['mode'] == 'SINGLE'
        assert len(agent.conversation_history) == 0
    
    def test_agent_initialization_multi_mode(self):
        """Тест: инициализация агента в режиме MULTI"""
        user_id = 12345
        agent = MockLandingAIAgent(user_id, mode='MULTI')
        
        assert agent.mode == 'MULTI'
        assert agent.collected_data['mode'] == 'MULTI'
    
    @pytest.mark.asyncio
    async def test_start_conversation(self):
        """Тест: начало диалога"""
        agent = MockLandingAIAgent(12345, mode='SINGLE')
        
        greeting = await agent.start_conversation()
        
        assert greeting is not None
        assert len(greeting) > 0
        assert 'SINGLE' in greeting or 'лендинг' in greeting.lower()
        assert len(agent.conversation_history) == 1
        assert agent.conversation_history[0]['role'] == 'assistant'
    
    @pytest.mark.asyncio
    async def test_process_message_general_info(self):
        """Тест: обработка сообщений на стадии general_info"""
        agent = MockLandingAIAgent(12345, mode='SINGLE')
        
        # Обрабатываем сообщения
        response1 = await agent.process_message("Цель - продажа")
        response2 = await agent.process_message("Целевая аудитория - взрослые")
        response3 = await agent.process_message("Стиль - минималистичный")
        
        # Проверяем ответы
        assert response1 is not None
        assert response2 is not None
        assert response3 is not None
        
        # Проверяем переход к следующей стадии
        assert agent.stage == 'products'
        assert agent.collected_data['stage'] == 'products'
        
        # Проверяем сохранение данных
        assert 'goal' in agent.collected_data['general_info']
        assert 'target_audience' in agent.collected_data['general_info']
        assert 'style' in agent.collected_data['general_info']
    
    @pytest.mark.asyncio
    async def test_process_message_products(self):
        """Тест: обработка сообщений на стадии products"""
        agent = MockLandingAIAgent(12345, mode='SINGLE')
        agent.stage = 'products'
        agent.collected_data['stage'] = 'products'
        
        response = await agent.process_message("Товар Ортопедическая подушка")
        
        assert response is not None
        assert len(agent.collected_data['products']) > 0
        assert agent.collected_data['products'][0]['product_name'] is not None
    
    @pytest.mark.asyncio
    async def test_process_message_verification(self):
        """Тест: обработка сообщений на стадии verification"""
        agent = MockLandingAIAgent(12345, mode='SINGLE')
        agent.stage = 'verification'
        agent.collected_data['stage'] = 'verification'
        
        response = await agent.process_message("Да, все верно")
        
        assert response is not None
        assert agent.stage == 'generation'
        assert agent.collected_data['stage'] == 'generation'
    
    def test_get_state(self):
        """Тест: получение состояния агента"""
        agent = MockLandingAIAgent(12345, mode='SINGLE')
        agent.stage = 'products'
        
        state = agent.get_state()
        
        assert 'stage' in state
        assert 'collected_data' in state
        assert 'mode' in state
        assert state['stage'] == 'products'
        assert state['mode'] == 'SINGLE'
    
    def test_set_state(self):
        """Тест: установка состояния агента"""
        agent = MockLandingAIAgent(12345, mode='SINGLE')
        
        new_state = {
            'stage': 'products',
            'collected_data': {
                'mode': 'SINGLE',
                'general_info': {'goal': 'продажа'},
                'products': [],
                'current_product_index': 0,
                'stage': 'products',
                'files': []
            },
            'mode': 'SINGLE'
        }
        
        agent.set_state(new_state)
        
        assert agent.stage == 'products'
        assert agent.collected_data['general_info']['goal'] == 'продажа'
    
    def test_generate_prompt(self):
        """Тест: генерация промпта"""
        agent = MockLandingAIAgent(12345, mode='SINGLE')
        agent.stage = 'products'
        agent.collected_data['general_info'] = {'goal': 'продажа'}
        
        prompt = agent.generate_prompt()
        
        assert prompt is not None
        assert 'SINGLE' in prompt
        assert 'products' in prompt
        assert 'продажа' in prompt or 'collected_data' in prompt
    
    def test_serialize_state(self):
        """Тест: сериализация состояния"""
        agent = MockLandingAIAgent(12345, mode='SINGLE')
        agent.stage = 'products'
        agent.collected_data['general_info'] = {'goal': 'продажа'}
        agent.conversation_history = [
            {'role': 'user', 'content': 'Привет'},
            {'role': 'assistant', 'content': 'Привет!'}
        ]
        
        serialized = agent.serialize_state()
        
        assert 'mode' in serialized
        assert 'stage' in serialized
        assert 'collected_data' in serialized
        assert 'conversation_history' in serialized
        assert serialized['mode'] == 'SINGLE'
        assert serialized['stage'] == 'products'
        assert len(serialized['conversation_history']) == 2
    
    def test_from_serialized_state(self):
        """Тест: восстановление из сериализованного состояния"""
        user_id = 12345
        serialized = {
            'user_id': user_id,
            'mode': 'SINGLE',
            'stage': 'products',
            'collected_data': {
                'mode': 'SINGLE',
                'general_info': {'goal': 'продажа'},
                'products': [],
                'current_product_index': 0,
                'stage': 'products',
                'files': []
            },
            'conversation_history': [
                {'role': 'user', 'content': 'Привет'},
                {'role': 'assistant', 'content': 'Привет!'}
            ]
        }
        
        agent = MockLandingAIAgent.from_serialized_state(serialized)
        
        assert agent.user_id == user_id
        assert agent.mode == 'SINGLE'
        assert agent.stage == 'products'
        assert agent.collected_data['general_info']['goal'] == 'продажа'
        assert len(agent.conversation_history) == 2
    
    @pytest.mark.asyncio
    async def test_conversation_history_limit(self):
        """Тест: ограничение длины истории диалога"""
        agent = MockLandingAIAgent(12345, mode='SINGLE')
        agent.max_history_length = 5
        
        # Добавляем больше сообщений, чем лимит
        for i in range(10):
            await agent.process_message(f"Сообщение {i}")
        
        # Проверяем, что история ограничена
        assert len(agent.conversation_history) <= agent.max_history_length * 2  # user + assistant
        
        # Проверяем, что последние сообщения сохранены
        assert len(agent.conversation_history) > 0
    
    def test_get_stage_info(self):
        """Тест: получение информации о стадии"""
        agent = MockLandingAIAgent(12345, mode='SINGLE')
        
        # Проверяем для разных стадий
        agent.stage = 'general_info'
        info1 = agent._get_stage_info()
        assert 'информация' in info1.lower() or 'general' in info1.lower()
        
        agent.stage = 'products'
        info2 = agent._get_stage_info()
        assert 'товар' in info2.lower() or 'product' in info2.lower()
        
        agent.stage = 'verification'
        info3 = agent._get_stage_info()
        assert 'проверка' in info3.lower() or 'verification' in info3.lower()
        
        agent.stage = 'generation'
        info4 = agent._get_stage_info()
        assert 'генерация' in info4.lower() or 'generation' in info4.lower()
    
    @pytest.mark.asyncio
    async def test_data_persistence_through_messages(self):
        """Тест: сохранение данных через несколько сообщений"""
        agent = MockLandingAIAgent(12345, mode='SINGLE')
        
        # Собираем данные
        await agent.process_message("Цель - продажа")
        await agent.process_message("Аудитория - взрослые")
        await agent.process_message("Стиль - минималистичный")
        
        # Проверяем сохранение
        assert 'goal' in agent.collected_data['general_info']
        assert 'target_audience' in agent.collected_data['general_info']
        assert 'style' in agent.collected_data['general_info']
        
        # Проверяем историю
        assert len(agent.conversation_history) >= 6  # 3 user + 3 assistant

