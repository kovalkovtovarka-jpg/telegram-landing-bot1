"""
Вспомогательные функции
"""
import os
import shutil
from typing import Optional

def ensure_dir(directory: str):
    """Создать директорию если не существует"""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def cleanup_old_files(directory: str, days_old: int = 7):
    """Удалить старые файлы (старше N дней)"""
    import time
    current_time = time.time()
    days_in_seconds = days_old * 24 * 60 * 60
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.getctime(file_path) < (current_time - days_in_seconds):
                try:
                    os.remove(file_path)
                except OSError as e:
                    # Логируем ошибки, но не прерываем процесс
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Не удалось удалить файл {file_path}: {e}")
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Неожиданная ошибка при удалении файла {file_path}: {e}")

def format_file_size(size_bytes: int) -> str:
    """Форматирование размера файла"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def sanitize_filename(filename: str) -> str:
    """Очистка имени файла от недопустимых символов"""
    import re
    # Удаляем недопустимые символы
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Ограничиваем длину
    if len(filename) > 200:
        filename = filename[:200]
    return filename
