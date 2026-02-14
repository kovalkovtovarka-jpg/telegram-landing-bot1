"""
Сбор данных от пользователя для генерации лендинга
"""
from typing import Dict, Any, List, Optional
try:
    from template_selector import TemplateSelector
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from template_selector import TemplateSelector
from backend.generator.template_loader import TemplateLoader

class DataCollector:
    """Класс для сбора данных от пользователя"""
    
    def __init__(self, template_selector: TemplateSelector, template_loader: TemplateLoader):
        """
        Инициализация сборщика данных
        
        Args:
            template_selector: Селектор шаблонов
            template_loader: Загрузчик шаблонов
        """
        self.template_selector = template_selector
        self.template_loader = template_loader
    
    def get_required_fields(self, template_id: str) -> Dict[str, str]:
        """
        Получить список обязательных полей для шаблона
        
        Args:
            template_id: ID шаблона
            
        Returns:
            Словарь с описанием обязательных полей
        """
        template_info = self.template_loader.get_template(template_id)
        if not template_info:
            return {}
        
        return template_info.get('required_fields', {})
    
    def get_next_field(self, template_id: str, collected_data: Dict[str, Any]) -> Optional[str]:
        """
        Получить следующее поле для заполнения
        
        Args:
            template_id: ID шаблона
            collected_data: Уже собранные данные
            
        Returns:
            ID следующего поля или None если все заполнено
        """
        required_fields = self.get_required_fields(template_id)
        
        for field_id, field_type in required_fields.items():
            if field_id not in collected_data:
                return field_id
        
        return None
    
    def get_field_question(self, field_id: str, template_id: str) -> str:
        """
        Получить вопрос для поля
        
        Args:
            field_id: ID поля
            template_id: ID шаблона
            
        Returns:
            Текст вопроса
        """
        questions = {
            'product_name': '📦 Как называется товар?',
            'product_description': '📝 Опиши товар подробно. Какие его главные преимущества?',
            'old_price': '💰 Какая была цена до скидки? (например: 152 BYN)',
            'new_price': '💵 Какая цена со скидкой? (например: 99 BYN)',
            'discount_percent': '🎯 Сколько процентов скидка? (например: 35)',
            'product_images': '📸 Пришли фотографии товара (минимум 4 фото). Можно прислать несколько сообщений.',
            'features': '✨ Какие ключевые особенности товара? (напиши по одному на строку)',
            'benefits': '🌟 Какие преимущества товара? (например: Эффект памяти, Анатомическая форма)',
            'reviews': '⭐ Есть ли отзывы? (пришли фото отзывов или напиши текст)',
            'delivery_info': '🚚 Информация о доставке? (например: "Доставка по всей Беларуси")',
            'payment_info': '💳 Информация об оплате? (например: "Оплата при получении")',
            'warranty_info': '🛡️ Гарантия? (например: "30 дней гарантия возврата")'
        }
        
        return questions.get(field_id, f'Введите данные для поля: {field_id}')
    
    def validate_field(self, field_id: str, value: Any, template_id: str) -> tuple[bool, str]:
        """
        Валидация значения поля
        
        Args:
            field_id: ID поля
            value: Значение
            template_id: ID шаблона
            
        Returns:
            (валидно, сообщение об ошибке)
        """
        required_fields = self.get_required_fields(template_id)
        field_type = required_fields.get(field_id, 'string')
        
        # Проверка на пустое значение
        if not value or (isinstance(value, str) and not value.strip()):
            return False, f'Поле {field_id} не может быть пустым'
        
        # Валидация по типу
        if field_type == 'number':
            try:
                float(str(value).replace('BYN', '').strip())
            except:
                return False, f'Поле {field_id} должно быть числом'
        
        if field_id == 'phone' and isinstance(value, str):
            if not value.startswith('+375'):
                return False, 'Телефон должен начинаться с +375'
        
        if field_id == 'price' or field_id in ['old_price', 'new_price']:
            if isinstance(value, str):
                # Более гибкая проверка цены
                if not any(curr in value.upper() for curr in ['BYN', 'BYR', 'RUB', 'USD', 'EUR']):
                    pass  # Не обязательно указывать валюту
        
        return True, ''
    
    def format_collected_data(self, collected_data: Dict[str, Any], template_id: str) -> Dict[str, Any]:
        """
        Форматирование собранных данных для генерации
        
        Args:
            collected_data: Собранные данные
            template_id: ID шаблона
            
        Returns:
            Отформатированные данные
        """
        formatted = collected_data.copy()
        
        # Преобразование цен
        for price_key in ['old_price', 'new_price', 'price']:
            if price_key in formatted and isinstance(formatted[price_key], str):
                # Извлекаем число из строки "152 BYN" -> "152 BYN"
                formatted[price_key] = formatted[price_key].strip()
        
        # Преобразование скидки в процент
        if 'old_price' in formatted and 'new_price' in formatted:
            try:
                old = float(str(formatted['old_price']).replace('BYN', '').strip())
                new = float(str(formatted['new_price']).replace('BYN', '').strip())
                discount = int(((old - new) / old) * 100)
                formatted['discount_percent'] = discount
            except:
                pass
        
        # Преобразование списков (features, benefits)
        for list_key in ['features', 'benefits']:
            if list_key in formatted and isinstance(formatted[list_key], str):
                formatted[list_key] = [
                    item.strip() 
                    for item in formatted[list_key].split('\n') 
                    if item.strip()
                ]
        
        # Добавление TikTok Pixel ID (пока дефолтный)
        formatted['tiktok_pixel_id'] = 'D5L7UCBC77U0IF4JE7J0'
        
        return formatted
