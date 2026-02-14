"""
Конфигурация приложения
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Конфигурация приложения"""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # LLM API
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openai')  # openai, anthropic, google
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o')  # gpt-4o, gpt-4-turbo, claude-3-5-sonnet-20241022, gemini-1.5-pro
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.3'))  # Снижено для более точных результатов
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '8000'))  # Увеличено для полного кода
    
    # LLM Timeouts and Retry
    LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '120'))  # Таймаут для LLM запросов в секундах (по умолчанию 2 минуты)
    LLM_MAX_RETRIES = int(os.getenv('LLM_MAX_RETRIES', '3'))  # Максимальное количество попыток
    LLM_RETRY_DELAY = float(os.getenv('LLM_RETRY_DELAY', '2.0'))  # Начальная задержка между попытками в секундах
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///landing_bot.db')
    
    # File Storage
    FILES_DIR = os.getenv('FILES_DIR', 'generated_landings')
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB
    
    # Bot Settings
    BOT_ADMIN_IDS = os.getenv('BOT_ADMIN_IDS', '').split(',') if os.getenv('BOT_ADMIN_IDS') else []
    
    # Rate Limiting
    MAX_REQUESTS_PER_HOUR = int(os.getenv('MAX_REQUESTS_PER_HOUR', '10'))
    
    # Webhook (опционально)
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    # Порт для webhook (использует PORT из окружения для Railway/Render, иначе WEBHOOK_PORT)
    WEBHOOK_PORT = int(os.getenv('PORT', os.getenv('WEBHOOK_PORT', '8443')))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE = os.getenv('LOG_FILE', 'bot.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # Prompt Optimization
    MAX_PROMPT_LENGTH = int(os.getenv('MAX_PROMPT_LENGTH', '15000'))  # Максимальная длина промпта
    
    # AI Agent Settings
    AI_AGENT_TIMEOUT = int(os.getenv('AI_AGENT_TIMEOUT', '1800'))  # Таймаут для AI-агента в секундах (30 минут)
    AI_AGENT_INACTIVITY_TIMEOUT = int(os.getenv('AI_AGENT_INACTIVITY_TIMEOUT', '3600'))  # Таймаут неактивности AI-агента в секундах (1 час)
    
    @classmethod
    def validate(cls):
        """Проверка обязательных параметров"""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append('TELEGRAM_BOT_TOKEN не установлен')
        
        # Проверяем ключ в зависимости от провайдера
        if cls.LLM_PROVIDER == 'openai' and not cls.OPENAI_API_KEY:
            errors.append('OPENAI_API_KEY не установлен')
        elif cls.LLM_PROVIDER == 'anthropic' and not cls.ANTHROPIC_API_KEY:
            errors.append('ANTHROPIC_API_KEY не установлен')
        elif cls.LLM_PROVIDER == 'google' and not cls.GOOGLE_API_KEY:
            errors.append('GOOGLE_API_KEY не установлен')
        
        # Проверка для AI-режима (требуется LLM для диалога)
        if not cls.OPENAI_API_KEY and not cls.ANTHROPIC_API_KEY and not cls.GOOGLE_API_KEY:
            errors.append('Не установлен ни один API ключ для LLM (требуется для AI-режима)')
        
        if errors:
            raise ValueError(f"Ошибки конфигурации: {', '.join(errors)}")
        
        return True
