"""
Сжатие больших промптов для оптимизации запросов к LLM
"""
import re
import logging
from typing import Dict, Any
from backend.config import Config

logger = logging.getLogger(__name__)


class PromptCompressor:
    """Класс для сжатия промптов"""
    
    MAX_PROMPT_LENGTH = int(getattr(Config, 'MAX_PROMPT_LENGTH', 15000))  # Максимальная длина промпта
    MAX_DESCRIPTION_LENGTH = 500  # Максимальная длина описания в промпте
    
    @staticmethod
    def compress_description(description: str, max_length: int = None) -> str:
        """
        Сжатие длинного описания товара
        
        Args:
            description: Полное описание
            max_length: Максимальная длина (по умолчанию MAX_DESCRIPTION_LENGTH)
            
        Returns:
            Сжатое описание
        """
        if not description:
            return description
        
        max_len = max_length or PromptCompressor.MAX_DESCRIPTION_LENGTH
        
        if len(description) <= max_len:
            return description
        
        # Обрезаем до максимальной длины, стараясь не обрезать в середине предложения
        truncated = description[:max_len]
        
        # Ищем последнюю точку, восклицательный или вопросительный знак
        last_sentence_end = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        
        if last_sentence_end > max_len * 0.7:  # Если нашли в последних 30%
            truncated = truncated[:last_sentence_end + 1]
        else:
            # Если не нашли, просто обрезаем и добавляем многоточие
            truncated = truncated.rstrip() + '...'
        
        logger.info(f"Compressed description from {len(description)} to {len(truncated)} characters")
        return truncated
    
    @staticmethod
    def compress_reviews(reviews: list, max_reviews: int = 5, max_length_per_review: int = 200) -> list:
        """
        Сжатие списка отзывов
        
        Args:
            reviews: Список отзывов
            max_reviews: Максимальное количество отзывов
            max_length_per_review: Максимальная длина одного отзыва
            
        Returns:
            Сжатый список отзывов
        """
        if not reviews:
            return reviews
        
        # Ограничиваем количество
        compressed = reviews[:max_reviews]
        
        # Сжимаем каждый отзыв
        result = []
        for review in compressed:
            if isinstance(review, dict):
                text = review.get('text', '')
                if text and len(text) > max_length_per_review:
                    text = PromptCompressor.compress_description(text, max_length_per_review)
                    review = review.copy()
                    review['text'] = text
                result.append(review)
            elif isinstance(review, str):
                if len(review) > max_length_per_review:
                    review = PromptCompressor.compress_description(review, max_length_per_review)
                result.append(review)
            else:
                result.append(review)
        
        if len(reviews) > max_reviews:
            logger.info(f"Compressed reviews from {len(reviews)} to {len(result)}")
        
        return result
    
    @staticmethod
    def compress_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сжатие данных пользователя для уменьшения размера промпта
        
        Args:
            user_data: Данные пользователя
            
        Returns:
            Сжатые данные пользователя
        """
        compressed = user_data.copy()
        
        # Сжимаем описание
        if 'description' in compressed and compressed['description']:
            compressed['description'] = PromptCompressor.compress_description(
                compressed['description']
            )
        
        # Сжимаем отзывы
        if 'reviews' in compressed and compressed['reviews']:
            compressed['reviews'] = PromptCompressor.compress_reviews(
                compressed['reviews']
            )
        
        # Сжимаем характеристики (если слишком много)
        if 'characteristics_list' in compressed:
            chars = compressed['characteristics_list']
            if isinstance(chars, list) and len(chars) > 10:
                compressed['characteristics_list'] = chars[:10]
                logger.info(f"Compressed characteristics from {len(chars)} to 10")
        
        return compressed
    
    @staticmethod
    def check_and_compress_prompt(prompt: str) -> tuple[str, bool]:
        """
        Проверка размера промпта и сжатие при необходимости
        
        Args:
            prompt: Промпт для проверки
            
        Returns:
            (compressed_prompt, was_compressed) - кортеж со сжатым промптом и флагом сжатия
        """
        if len(prompt) <= PromptCompressor.MAX_PROMPT_LENGTH:
            return prompt, False
        
        logger.warning(f"Prompt too long ({len(prompt)} chars), attempting compression...")
        
        # Пытаемся найти и сжать описание в промпте
        # Ищем блок описания
        description_pattern = r'(ПУНКТ\s+\d+[:\s]*ОПИСАНИЕ[^\n]*\n[^\n]*\n)([^\n]+(?:\n[^\n]+)*?)(?=\n\n|ПУНКТ|\Z)'
        match = re.search(description_pattern, prompt, re.IGNORECASE | re.MULTILINE)
        
        if match:
            description_section = match.group(2)
            if len(description_section) > PromptCompressor.MAX_DESCRIPTION_LENGTH:
                compressed_desc = PromptCompressor.compress_description(description_section)
                prompt = prompt.replace(description_section, compressed_desc, 1)
                logger.info(f"Compressed description section in prompt")
        
        # Если все еще слишком длинный, обрезаем в конце (но сохраняем структуру)
        if len(prompt) > PromptCompressor.MAX_PROMPT_LENGTH:
            # Находим последний полный пункт
            last_point_match = re.search(r'(ПУНКТ\s+\d+[^\n]*)', prompt, re.IGNORECASE)
            if last_point_match:
                # Обрезаем после последнего пункта, но сохраняем заключение
                cutoff_pos = last_point_match.end()
                # Ищем заключительную часть
                conclusion_pattern = r'(╔═══════════════════════════════════════════════════════════════╗[^\n]*ЧЕКЛИСТ[^\n]*╚═══════════════════════════════════════════════════════════════╝.*)'
                conclusion_match = re.search(conclusion_pattern, prompt, re.DOTALL)
                if conclusion_match:
                    # Сохраняем начало и заключение
                    prompt = prompt[:cutoff_pos] + '\n\n' + conclusion_match.group(1)
                    logger.warning(f"Prompt truncated to {len(prompt)} characters (preserved structure)")
        
        return prompt, True

