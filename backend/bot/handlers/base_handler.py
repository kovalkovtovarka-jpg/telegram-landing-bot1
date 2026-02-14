"""
Базовый класс для всех обработчиков этапов сбора данных
"""
from abc import ABC
from typing import Dict, Any, Tuple, Optional
from telegram import Update
from telegram.ext import ContextTypes
import logging
from backend.config import Config

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """Базовый класс для всех обработчиков этапов"""
    
    def __init__(self, bot_instance):
        """
        Инициализация обработчика
        
        Args:
            bot_instance: Экземпляр основного бота (LandingBot)
        """
        self.bot = bot_instance
    
    # ==================== Утилиты для работы с данными пользователя ====================
    
    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Получить данные пользователя из БД
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Словарь с данными пользователя
        """
        return self.bot._get_user_data(user_id)
    
    def update_user_data(self, user_id: int, **kwargs):
        """
        Обновить данные пользователя
        
        Args:
            user_id: ID пользователя
            **kwargs: Поля для обновления
        """
        self.bot._update_user_data(user_id, **kwargs)
    
    def save_state(self, user_id: int, state: str, data: Dict[str, Any] = None, conversation_type: str = 'create'):
        """
        Сохранить состояние пользователя в БД
        
        Args:
            user_id: ID пользователя
            state: Название состояния
            data: Данные для сохранения (если None, берется из get_user_data)
            conversation_type: Тип диалога ('create' или 'quick')
        """
        if data is None:
            data = self.get_user_data(user_id)
        self.bot._save_user_data(user_id, data, state=state, conversation_type=conversation_type)
    
    def clear_user_data(self, user_id: int):
        """
        Очистить данные пользователя
        
        Args:
            user_id: ID пользователя
        """
        self.bot._clear_user_data(user_id)
    
    # ==================== Утилиты для логирования ====================
    
    def log(self, level: str, message: str, user_id: int = None):
        """
        Логирование с контекстом пользователя
        
        Args:
            level: Уровень логирования ('info', 'error', 'warning', 'debug')
            message: Сообщение для логирования
            user_id: ID пользователя (опционально)
        """
        log_message = message
        if user_id:
            log_message = f"User {user_id}: {message}"
        
        if level == 'info':
            logger.info(log_message)
        elif level == 'error':
            logger.error(log_message)
        elif level == 'warning':
            logger.warning(log_message)
        elif level == 'debug':
            logger.debug(log_message)
    
    def check_file_size(self, file_size: int, file_type: str = 'файл') -> tuple[bool, str]:
        """
        Проверка размера файла
        
        Args:
            file_size: Размер файла в байтах
            file_type: Тип файла для сообщения об ошибке
            
        Returns:
            (is_valid, error_message) - кортеж с результатом проверки
        """
        if file_size and file_size > Config.MAX_FILE_SIZE:
            max_size_mb = Config.MAX_FILE_SIZE / (1024 * 1024)
            file_size_mb = file_size / (1024 * 1024)
            error_msg = (
                f"❌ **{file_type.capitalize()} слишком большой!**\n\n"
                f"Максимальный размер: {max_size_mb:.1f} MB\n"
                f"Размер вашего файла: {file_size_mb:.1f} MB\n\n"
                f"Пожалуйста, отправьте файл меньшего размера."
            )
            return False, error_msg
        return True, ""
    
    def validate_uploaded_file(self, file_path: str, expected_type: str = 'image') -> Tuple[bool, Optional[str]]:
        """
        Проверка типа загруженного файла
        
        Args:
            file_path: Путь к загруженному файлу
            expected_type: Ожидаемый тип ('image' или 'video')
            
        Returns:
            (is_valid, error_message)
        """
        from backend.utils.file_validator import validate_media_file
        
        is_valid, error_msg = validate_media_file(file_path, expected_type)
        if not is_valid:
            logger.warning(f"Invalid file type for {file_path}: {error_msg}")
        return is_valid, error_msg

