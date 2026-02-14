"""
Утилита для обработки текста с Wildberries
"""
import re
from typing import Optional

class TextProcessor:
    """Класс для обработки текста с маркетплейсов"""
    
    @staticmethod
    def is_wildberries_text(text: str) -> bool:
        """
        Проверка, является ли текст с Wildberries
        
        Args:
            text: Текст для проверки
            
        Returns:
            True если текст похож на описание с Wildberries
        """
        if not text:
            return False
        
        # Признаки текста с Wildberries
        wildberries_indicators = [
            'артикул',
            'арт.',
            'арт ',
            'артикул продавца',
            'бренд:',
            'страна производства',
            'страна бренда',
            'wb',
            'wildberries',
            'продавец:',
            'категория:',
            'подкатегория:',
            'состав:',
            'материал:',
            'размеры:',
            'характеристики:',
            'описание товара',
            'товар сертифицирован',
            'соответствует требованиям',
            'гарантия качества',
            'доставка',
            'возврат',
            'обмен',
            'отзывы',
            'рейтинг',
            'оценка',
            'штрихкод',
            'ean',
            'gtin'
        ]
        
        text_lower = text.lower()
        matches = sum(1 for indicator in wildberries_indicators if indicator in text_lower)
        
        # Если найдено 3+ признака - вероятно текст с Wildberries
        return matches >= 3
    
    @staticmethod
    def clean_wildberries_text(text: str) -> str:
        """
        Очистка текста от специфичных для Wildberries элементов
        
        Args:
            text: Текст с Wildberries
            
        Returns:
            Очищенный текст
        """
        if not text:
            return text
        
        # Удаляем артикулы и коды
        text = re.sub(r'артикул[:\s]*[a-z0-9\-]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'арт[.\s]*[a-z0-9\-]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'штрихкод[:\s]*[0-9]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'ean[:\s]*[0-9]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'gtin[:\s]*[0-9]+', '', text, flags=re.IGNORECASE)
        
        # Удаляем информацию о продавце и бренде (если не нужна)
        text = re.sub(r'продавец[:\s]*[^\n]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'бренд[:\s]*[^\n]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'страна производства[:\s]*[^\n]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'страна бренда[:\s]*[^\n]+', '', text, flags=re.IGNORECASE)
        
        # Удаляем категории
        text = re.sub(r'категория[:\s]*[^\n]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'подкатегория[:\s]*[^\n]+', '', text, flags=re.IGNORECASE)
        
        # Удаляем информацию о доставке/возврате (обычно в конце)
        text = re.sub(r'доставка[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'возврат[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'обмен[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'гарантия[^\n]*', '', text, flags=re.IGNORECASE)
        
        # Удаляем рейтинги и отзывы
        text = re.sub(r'рейтинг[:\s]*[0-9.]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'оценка[:\s]*[0-9.]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'отзыв[ов]*[:\s]*[0-9]+', '', text, flags=re.IGNORECASE)
        
        # Удаляем упоминания Wildberries
        text = re.sub(r'wildberries', '', text, flags=re.IGNORECASE)
        text = re.sub(r'wb\s*\.ru', '', text, flags=re.IGNORECASE)
        
        # Удаляем лишние пустые строки
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Удаляем лишние пробелы
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    @staticmethod
    def process_description(text: str, is_wildberries: Optional[bool] = None) -> tuple[str, bool]:
        """
        Обработка описания товара
        
        Args:
            text: Текст описания
            is_wildberries: Явно указано, что текст с Wildberries (если None - определяется автоматически)
            
        Returns:
            Кортеж (обработанный_текст, был_ли_это_wildberries)
        """
        if not text:
            return text, False
        
        # Определяем, если не указано явно
        if is_wildberries is None:
            is_wildberries = TextProcessor.is_wildberries_text(text)
        
        if is_wildberries:
            # Очищаем от лишнего
            cleaned = TextProcessor.clean_wildberries_text(text)
            return cleaned, True
        
        return text, False

