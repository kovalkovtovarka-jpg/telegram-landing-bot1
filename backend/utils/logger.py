"""
Улучшенная система логирования с контекстом
"""
import logging
import re
import sys
import os
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
from contextvars import ContextVar
from datetime import datetime

# Паттерн для маскировки токена бота в URL (api.telegram.org/bot123:secret/...)
_BOT_TOKEN_PATTERN = re.compile(r'(bot\d+[:%][A-Za-z0-9_-]+)', re.IGNORECASE)


def _redact_string(s: str) -> str:
    return _BOT_TOKEN_PATTERN.sub(r'bot***', s)


class SecretRedactionFilter(logging.Filter):
    """Убирает токен бота из текста логов (msg и args)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact_string(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: _redact_string(v) if isinstance(v, str) else v for k, v in record.args.items()}
            else:
                record.args = tuple(_redact_string(a) if isinstance(a, str) else a for a in record.args)
        return True


# Контекстные переменные для хранения информации о запросе
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[int]] = ContextVar('user_id', default=None)


class ContextualFormatter(logging.Formatter):
    """Форматтер с поддержкой контекста"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Добавляем контекстную информацию
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        
        if request_id:
            record.request_id = request_id
        else:
            record.request_id = 'N/A'
        
        if user_id:
            record.user_id = user_id
        else:
            record.user_id = 'N/A'
        
        return super().format(record)


def setup_logging(
    log_level: str = 'INFO',
    log_file: str = 'bot.log',
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_json: bool = False
) -> None:
    """
    Настройка логирования с ротацией и контекстом
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу логов
        max_bytes: Максимальный размер файла перед ротацией
        backup_count: Количество резервных файлов
        enable_json: Использовать JSON формат (для продакшн)
    """
    # Преобразуем строку уровня в константу
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Очищаем существующие обработчики
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.setLevel(numeric_level)
    
    # Формат логирования
    if enable_json:
        # JSON формат для продакшн (можно добавить позже)
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    else:
        # Расширенный формат с контекстом
        log_format = (
            '%(asctime)s | %(levelname)-8s | %(name)-20s | '
            'User: %(user_id)s | Request: %(request_id)s | %(message)s'
        )
    
    formatter = ContextualFormatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
    
    # Обработчик для файла с ротацией
    redaction_filter = SecretRedactionFilter()
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redaction_filter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SecretRedactionFilter())
    root_logger.addHandler(console_handler)

    # Настройка логирования для внешних библиотек
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('anthropic').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер с именем модуля
    
    Args:
        name: Имя модуля (обычно __name__)
        
    Returns:
        Настроенный логгер
    """
    return logging.getLogger(name)


def set_request_context(request_id: Optional[str] = None, user_id: Optional[int] = None) -> None:
    """
    Установить контекст для текущего запроса
    
    Args:
        request_id: Уникальный ID запроса
        user_id: ID пользователя
    """
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context() -> None:
    """Очистить контекст запроса"""
    request_id_var.set(None)
    user_id_var.set(None)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    user_id: Optional[int] = None,
    request_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Логирование с контекстом
    
    Args:
        logger: Логгер
        level: Уровень логирования
        message: Сообщение
        user_id: ID пользователя
        request_id: ID запроса
        extra: Дополнительные данные
    """
    # Временно устанавливаем контекст
    old_request_id = request_id_var.get()
    old_user_id = user_id_var.get()
    
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    
    try:
        log_method = getattr(logger, level.lower())
        if extra:
            log_method(message, extra=extra)
        else:
            log_method(message)
    finally:
        # Восстанавливаем старый контекст
        request_id_var.set(old_request_id)
        user_id_var.set(old_user_id)

