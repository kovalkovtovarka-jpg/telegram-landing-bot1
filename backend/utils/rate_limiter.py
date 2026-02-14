"""
Rate Limiter для контроля запросов пользователей
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple
from collections import defaultdict
from backend.database.database import SessionLocal
from backend.database.models import Generation
from backend.config import Config

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter для контроля запросов пользователей"""
    
    def __init__(self, max_requests: int = None, per_seconds: int = 3600):
        """
        Инициализация rate limiter
        
        Args:
            max_requests: Максимальное количество запросов
            per_seconds: Период времени в секундах
        """
        self.max_requests = max_requests or Config.MAX_REQUESTS_PER_HOUR
        self.per_seconds = per_seconds
        # In-memory кэш для быстрой проверки (для одного инстанса)
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def check_rate_limit(self, user_id: int) -> Tuple[bool, int]:
        """
        Проверка rate limit для пользователя (in-memory версия)
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            (allowed, remaining_requests)
        """
        async with self.lock:
            user_id_str = str(user_id)
            now = datetime.utcnow()
            cutoff = now - timedelta(seconds=self.per_seconds)
            
            # Очищаем старые запросы
            self.requests[user_id_str] = [
                req_time for req_time in self.requests[user_id_str]
                if req_time > cutoff
            ]
            
            # Проверяем лимит
            if len(self.requests[user_id_str]) >= self.max_requests:
                remaining = 0
                return False, remaining
            
            # Добавляем текущий запрос
            self.requests[user_id_str].append(now)
            remaining = self.max_requests - len(self.requests[user_id_str])
            
            return True, remaining
    
    async def check_db_rate_limit(self, user_id: int) -> Tuple[bool, int]:
        """
        Проверка rate limit через БД (для нескольких инстансов)
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            (allowed, remaining_requests)
        """
        db = SessionLocal()
        try:
            user_id_str = str(user_id)
            cutoff = datetime.utcnow() - timedelta(seconds=self.per_seconds)
            
            # Считаем запросы за последний период
            count = db.query(Generation).filter(
                Generation.user_id == user_id_str,
                Generation.created_at >= cutoff
            ).count()
            
            if count >= self.max_requests:
                return False, 0
            
            remaining = self.max_requests - count
            return True, remaining
        except Exception as e:
            logger.error(f"Error checking rate limit in DB: {e}")
            # В случае ошибки разрешаем запрос (fail-open)
            return True, self.max_requests
        finally:
            db.close()
    
    async def record_request(self, user_id: int):
        """
        Записать запрос пользователя (для in-memory версии)
        
        Args:
            user_id: ID пользователя
        """
        async with self.lock:
            user_id_str = str(user_id)
            self.requests[user_id_str].append(datetime.utcnow())
    
    def get_user_stats(self, user_id: int) -> Dict:
        """
        Получить статистику пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой
        """
        user_id_str = str(user_id)
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.per_seconds)
        
        requests_in_period = [
            req_time for req_time in self.requests.get(user_id_str, [])
            if req_time > cutoff
        ]
        
        return {
            'requests_count': len(requests_in_period),
            'max_requests': self.max_requests,
            'remaining': max(0, self.max_requests - len(requests_in_period)),
            'period_seconds': self.per_seconds
        }


# Глобальный экземпляр rate limiter
rate_limiter = RateLimiter(
    max_requests=Config.MAX_REQUESTS_PER_HOUR,
    per_seconds=3600  # 1 час
)

