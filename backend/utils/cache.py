"""
Кэширование промптов для похожих товаров
"""
import hashlib
import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from backend.config import Config

logger = logging.getLogger(__name__)


class PromptCache:
    """Кэш для промптов генерации лендингов"""
    
    def __init__(self, cache_dir: str = None, ttl_hours: int = 24):
        """
        Инициализация кэша
        
        Args:
            cache_dir: Директория для кэша (по умолчанию generated_landings/cache)
            ttl_hours: Время жизни кэша в часах
        """
        self.cache_dir = cache_dir or os.path.join(Config.FILES_DIR, 'cache', 'prompts')
        self.ttl_hours = ttl_hours
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _generate_cache_key(self, user_data: Dict[str, Any]) -> str:
        """
        Генерация ключа кэша на основе данных пользователя
        
        Args:
            user_data: Данные пользователя
            
        Returns:
            Хеш-ключ для кэша
        """
        # Создаем упрощенную версию данных для ключа
        key_data = {
            'product_name': user_data.get('product_name', ''),
            'landing_type': user_data.get('landing_type', ''),
            'old_price': user_data.get('old_price', ''),
            'new_price': user_data.get('new_price', ''),
            'characteristics': user_data.get('characteristics_list', []),
            'sizes': user_data.get('sizes', []),
            'colors': user_data.get('colors', []),
        }
        
        # Сортируем списки для консистентности
        if isinstance(key_data['characteristics'], list):
            key_data['characteristics'] = sorted(key_data['characteristics'])
        if isinstance(key_data['sizes'], list):
            key_data['sizes'] = sorted(key_data['sizes'])
        if isinstance(key_data['colors'], list):
            key_data['colors'] = sorted(key_data['colors'])
        
        # Создаем JSON строку и хеш
        key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        cache_key = hashlib.md5(key_string.encode('utf-8')).hexdigest()
        
        return cache_key
    
    def _get_cache_path(self, cache_key: str) -> str:
        """Получить путь к файлу кэша"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def get(self, user_data: Dict[str, Any]) -> Optional[str]:
        """
        Получить промпт из кэша
        
        Args:
            user_data: Данные пользователя
            
        Returns:
            Промпт из кэша или None
        """
        try:
            cache_key = self._generate_cache_key(user_data)
            cache_path = self._get_cache_path(cache_key)
            
            if not os.path.exists(cache_path):
                return None
            
            # Проверяем время жизни
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
            if datetime.now() - file_time > timedelta(hours=self.ttl_hours):
                # Кэш устарел, удаляем
                os.remove(cache_path)
                logger.debug(f"Cache expired for key {cache_key}")
                return None
            
            # Читаем кэш
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            logger.info(f"Cache hit for key {cache_key}")
            return cache_data.get('prompt')
            
        except Exception as e:
            logger.warning(f"Error reading from cache: {e}")
            return None
    
    def set(self, user_data: Dict[str, Any], prompt: str) -> bool:
        """
        Сохранить промпт в кэш
        
        Args:
            user_data: Данные пользователя
            prompt: Промпт для сохранения
            
        Returns:
            True если успешно сохранено
        """
        try:
            cache_key = self._generate_cache_key(user_data)
            cache_path = self._get_cache_path(cache_key)
            
            cache_data = {
                'prompt': prompt,
                'created_at': datetime.now().isoformat(),
                'cache_key': cache_key,
                'user_data_summary': {
                    'product_name': user_data.get('product_name', ''),
                    'landing_type': user_data.get('landing_type', '')
                }
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Cache saved for key {cache_key}")
            return True
            
        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")
            return False
    
    def clear_expired(self) -> int:
        """
        Очистить устаревшие записи кэша
        
        Returns:
            Количество удаленных файлов
        """
        deleted_count = 0
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.ttl_hours)
            
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.json'):
                    continue
                
                file_path = os.path.join(self.cache_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_time < cutoff_time:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Error deleting cache file {filename}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleared {deleted_count} expired cache entries")
            
        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")
        
        return deleted_count
    
    def clear_all(self) -> int:
        """
        Очистить весь кэш
        
        Returns:
            Количество удаленных файлов
        """
        deleted_count = 0
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    try:
                        os.remove(os.path.join(self.cache_dir, filename))
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Error deleting cache file {filename}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleared all cache: {deleted_count} entries")
            
        except Exception as e:
            logger.error(f"Error clearing all cache: {e}")
        
        return deleted_count


# Глобальный экземпляр кэша
prompt_cache = PromptCache(ttl_hours=24)

