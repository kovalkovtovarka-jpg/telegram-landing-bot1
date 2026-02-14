"""
Модуль для проверки здоровья системы (health check)
"""
import logging
from typing import Dict, Any
from backend.database.database import SessionLocal, engine
from backend.database.models import User
from backend.config import Config
from backend.generator.llm_client import LLMClient

logger = logging.getLogger(__name__)


async def check_database() -> Dict[str, Any]:
    """
    Проверка подключения к базе данных
    
    Returns:
        Словарь с результатом проверки
    """
    try:
        db = SessionLocal()
        try:
            # Простой запрос для проверки соединения
            db.query(User).limit(1).all()
            return {
                'status': 'healthy',
                'message': 'Database connection OK'
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': f'Database error: {str(e)}'
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Database health check exception: {e}")
        return {
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}'
        }


async def check_llm() -> Dict[str, Any]:
    """
    Проверка доступности LLM API
    
    Returns:
        Словарь с результатом проверки
    """
    try:
        # Создаем клиент для проверки
        llm_client = LLMClient()
        
        if not llm_client.client:
            return {
                'status': 'unhealthy',
                'message': f'{Config.LLM_PROVIDER.upper()} API key not configured'
            }
        
        # Для OpenAI можно проверить через простой запрос
        # Для других провайдеров просто проверяем наличие клиента
        if Config.LLM_PROVIDER == 'openai':
            # OpenAI клиент уже инициализирован, если есть ключ
            return {
                'status': 'healthy',
                'message': f'{Config.LLM_PROVIDER.upper()} client initialized'
            }
        elif Config.LLM_PROVIDER == 'anthropic':
            return {
                'status': 'healthy',
                'message': f'{Config.LLM_PROVIDER.upper()} client initialized'
            }
        elif Config.LLM_PROVIDER == 'google':
            return {
                'status': 'healthy',
                'message': f'{Config.LLM_PROVIDER.upper()} client initialized'
            }
        else:
            return {
                'status': 'unhealthy',
                'message': f'Unknown LLM provider: {Config.LLM_PROVIDER}'
            }
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return {
            'status': 'unhealthy',
            'message': f'LLM check error: {str(e)}'
        }


async def check_health() -> Dict[str, Any]:
    """
    Полная проверка здоровья системы
    
    Returns:
        Словарь с результатами всех проверок
    """
    db_check = await check_database()
    llm_check = await check_llm()
    
    overall_status = 'healthy' if (
        db_check['status'] == 'healthy' and 
        llm_check['status'] == 'healthy'
    ) else 'unhealthy'
    
    return {
        'status': overall_status,
        'checks': {
            'database': db_check,
            'llm': llm_check
        }
    }

