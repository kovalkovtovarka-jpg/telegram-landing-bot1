"""
Mock implementation of LandingAIAgent for testing
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MockLandingAIAgent:
    """
    Mock класс для LandingAIAgent.
    Предоставляет детерминированные ответы для тестирования.
    """
    
    def __init__(self, mode: str = 'SINGLE', user_id: int = 0):
        """
        Инициализация mock агента
        (для тестов можно передать user_id, но реальный LandingAIAgent принимает только mode)
        
        Args:
            mode: Режим работы ('SINGLE' или 'MULTI')
            user_id: ID пользователя (опционально, для тестирования, не используется в реальном коде)
        """
        self.user_id = user_id
        self.mode = mode
        self.stage = 'general_info'
        self.collected_data = {
            'mode': mode,
            'general_info': {},
            'products': [],
            'current_product_index': 0,
            'stage': 'general_info',
            'files': []
        }
        self.conversation_history = []
        self.max_history_length = 20
        
        logger.info(f"MockLandingAIAgent initialized for user {user_id}, mode: {mode}")
    
    async def process_message(self, message: str) -> str:
        """
        Обрабатывает сообщение пользователя и возвращает детерминированный ответ
        
        Args:
            message: Текст сообщения пользователя
            
        Returns:
            Ответ агента
        """
        message_lower = message.lower()
        
        # Сохраняем в историю
        self.conversation_history.append({'role': 'user', 'content': message})
        
        # Детерминированные ответы в зависимости от стадии
        if self.stage == 'general_info':
            if 'цель' in message_lower or 'продажа' in message_lower:
                self.collected_data['general_info']['goal'] = 'продажа'
                response = "Отлично! Цель - продажа. Какая целевая аудитория?"
            elif 'аудитория' in message_lower or 'целевая' in message_lower:
                self.collected_data['general_info']['target_audience'] = message
                response = "Понял. Какой стиль дизайна предпочитаете?"
            elif 'стиль' in message_lower or 'дизайн' in message_lower:
                self.collected_data['general_info']['style'] = message
                # Переход к следующей стадии
                self.stage = 'products'
                self.collected_data['stage'] = 'products'
                response = "Стиль сохранен. Теперь расскажите о товаре: название, описание, цена."
            else:
                response = "Спасибо за информацию. Продолжаем сбор данных."
        
        elif self.stage == 'products':
            if 'название' in message_lower or 'товар' in message_lower:
                # Простое извлечение названия
                words = message.split()
                if len(words) > 0:
                    self.collected_data['products'] = [{
                        'product_name': words[0] if len(words) == 1 else ' '.join(words[:3]),
                        'product_description': message,
                        'new_price': 99,
                        'old_price': 150
                    }]
                response = "Товар сохранен. Нужна ли дополнительная информация?"
            elif 'цена' in message_lower:
                # Извлечение цены
                import re
                prices = re.findall(r'\d+', message)
                if prices:
                    self.collected_data['products'][0]['new_price'] = int(prices[0])
                    if len(prices) > 1:
                        self.collected_data['products'][0]['old_price'] = int(prices[1])
                response = "Цена сохранена."
            else:
                # Обновляем описание
                if self.collected_data['products']:
                    self.collected_data['products'][0]['product_description'] = message
                response = "Информация сохранена."
        
        elif self.stage == 'verification':
            if 'да' in message_lower or 'верно' in message_lower or 'подтверждаю' in message_lower:
                self.stage = 'generation'
                self.collected_data['stage'] = 'generation'
                response = "Отлично! Все данные собраны. Готов к генерации."
            else:
                response = "Что нужно изменить?"
        
        elif self.stage == 'generation':
            response = "Генерация уже начата."
        
        else:
            response = "Продолжаем диалог."
        
        # Сохраняем ответ в историю
        self.conversation_history.append({'role': 'assistant', 'content': response})
        
        # Ограничиваем длину истории
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
        
        return response
    
    def get_state(self) -> Dict[str, Any]:
        """
        Возвращает текущее состояние агента
        
        Returns:
            Словарь с состоянием
        """
        return {
            'stage': self.stage,
            'collected_data': self.collected_data,
            'mode': self.mode
        }
    
    def set_state(self, state: Dict[str, Any]):
        """
        Устанавливает состояние агента
        
        Args:
            state: Словарь с состоянием
        """
        self.stage = state.get('stage', 'general_info')
        self.collected_data = state.get('collected_data', self.collected_data)
        self.mode = state.get('mode', self.mode)
    
    def generate_prompt(self) -> str:
        """
        Генерирует промпт для генерации лендинга
        
        Returns:
            Строка с промптом
        """
        prompt = f"Генерация лендинга для режима {self.mode}\n\n"
        prompt += f"Стадия: {self.stage}\n"
        prompt += f"Собранные данные: {self.collected_data}\n"
        return prompt
    
    def serialize_state(self) -> Dict[str, Any]:
        """
        Сериализует состояние для сохранения в БД
        
        Returns:
            Словарь с сериализованным состоянием
        """
        return {
            'mode': self.mode,
            'stage': self.stage,
            'collected_data': self.collected_data,
            'conversation_history': self.conversation_history[-self.max_history_length:]
        }
    
    @classmethod
    def from_serialized_state(cls, state: Dict[str, Any]) -> 'MockLandingAIAgent':
        """
        Восстанавливает агента из сериализованного состояния
        (совместимо с реальным LandingAIAgent)
        
        Args:
            state: Словарь с состоянием
            
        Returns:
            Восстановленный экземпляр MockLandingAIAgent
        """
        # user_id не используется в реальном LandingAIAgent
        agent = cls(state.get('mode', 'SINGLE'))
        agent.stage = state.get('stage', 'general_info')
        agent.collected_data = state.get('collected_data', agent.collected_data)
        agent.conversation_history = state.get('conversation_history', [])
        return agent
    
    async def start_conversation(self) -> str:
        """
        Начинает диалог с пользователем
        
        Returns:
            Приветственное сообщение
        """
        greeting = f"Привет! Я помогу создать лендинг в режиме {self.mode}. Давайте начнем!"
        self.conversation_history.append({'role': 'assistant', 'content': greeting})
        return greeting
    
    def _get_stage_info(self) -> str:
        """
        Возвращает информацию о текущей стадии
        
        Returns:
            Описание стадии
        """
        stage_names = {
            'general_info': 'Общая информация',
            'products': 'Сбор данных о товаре',
            'verification': 'Проверка данных',
            'generation': 'Генерация'
        }
        return stage_names.get(self.stage, 'Неизвестная стадия')
    
    def convert_to_user_data(self) -> Dict[str, Any]:
        """
        Преобразует собранные данные агента в формат user_data для генерации
        
        Returns:
            Словарь с данными пользователя
        """
        user_data = {
            'landing_type': 'single_product' if self.mode == 'SINGLE' else 'multi_product',
            'design_style': self.collected_data.get('general_info', {}).get('style', 'современный'),
            'notification_type': self.collected_data.get('general_info', {}).get('notification_type', 'telegram'),
        }
        
        if self.mode == 'SINGLE' and self.collected_data.get('products'):
            product = self.collected_data['products'][0]
            user_data.update({
                'product_name': product.get('product_name', 'Товар'),
                'description_text': product.get('product_description', ''),
                'new_price': product.get('new_price', 99),
                'old_price': product.get('old_price', 150),
                'characteristics': product.get('characteristics', [])
            })
        
        return user_data
    
    def validate_data(self) -> List[str]:
        """
        Валидация собранных данных
        
        Returns:
            Список ошибок валидации (пустой если все ОК)
        """
        errors = []
        
        if self.mode == 'SINGLE':
            if not self.collected_data.get('products'):
                errors.append("Не указан товар")
            else:
                product = self.collected_data['products'][0]
                if not product.get('product_name'):
                    errors.append("Не указано название товара")
                if not product.get('product_description'):
                    errors.append("Не указано описание товара")
        
        return errors

