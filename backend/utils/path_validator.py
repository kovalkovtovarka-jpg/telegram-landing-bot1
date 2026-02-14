"""
Валидация путей файлов для предотвращения directory traversal атак
"""
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def validate_file_path(file_path: str, base_dir: str) -> bool:
    """
    Проверка, что путь находится в разрешенной директории
    
    Args:
        file_path: Путь к файлу для проверки
        base_dir: Базовая директория (разрешенная)
        
    Returns:
        True если путь безопасен, False иначе
    """
    try:
        # Преобразуем в абсолютные пути
        abs_file_path = os.path.abspath(file_path)
        abs_base_dir = os.path.abspath(base_dir)
        
        # Проверяем, что файл находится внутри базовой директории
        # Используем Path для кроссплатформенной совместимости
        file_path_obj = Path(abs_file_path)
        base_path_obj = Path(abs_base_dir)
        
        try:
            # Проверяем, что file_path является подпутем base_dir
            file_path_obj.relative_to(base_path_obj)
            return True
        except ValueError:
            # Если не является подпутем - это directory traversal
            logger.warning(f"Попытка доступа вне разрешенной директории: {file_path} (база: {base_dir})")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при валидации пути {file_path}: {e}")
        return False


def sanitize_path(file_path: str, base_dir: str) -> Optional[str]:
    """
    Санитизация пути файла
    
    Args:
        file_path: Путь к файлу
        base_dir: Базовая директория
        
    Returns:
        Безопасный путь или None если путь невалиден
    """
    if not validate_file_path(file_path, base_dir):
        return None
    
    # Убираем все '..' и нормализуем путь
    normalized = os.path.normpath(file_path)
    
    # Проверяем еще раз после нормализации
    if validate_file_path(normalized, base_dir):
        return normalized
    
    return None


def get_safe_path(filename: str, base_dir: str, subdir: str = '') -> str:
    """
    Получить безопасный путь к файлу
    
    Args:
        filename: Имя файла
        base_dir: Базовая директория
        subdir: Поддиректория (опционально)
        
    Returns:
        Безопасный путь к файлу
    """
    from backend.utils.helpers import sanitize_filename
    
    # Санитизируем имя файла
    safe_filename = sanitize_filename(filename)
    
    # Строим путь
    if subdir:
        # Санитизируем поддиректорию
        safe_subdir = sanitize_filename(subdir)
        full_path = os.path.join(base_dir, safe_subdir, safe_filename)
    else:
        full_path = os.path.join(base_dir, safe_filename)
    
    # Нормализуем путь
    normalized = os.path.normpath(full_path)
    
    # Проверяем валидность
    if validate_file_path(normalized, base_dir):
        return normalized
    
    # Если путь невалиден, возвращаем путь только с базовой директорией и безопасным именем
    logger.warning(f"Путь невалиден, используем только базовую директорию: {normalized}")
    return os.path.join(base_dir, safe_filename)

