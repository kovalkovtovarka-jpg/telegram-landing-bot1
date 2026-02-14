"""
Валидация типов файлов по MIME типам
"""
import os
import logging
from typing import List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Магические байты (file signatures) для различных типов файлов
FILE_SIGNATURES = {
    # Изображения
    'image/jpeg': [b'\xff\xd8\xff'],
    'image/png': [b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'],
    'image/gif': [b'\x47\x49\x46\x38'],
    'image/webp': [b'RIFF', b'WEBP'],
    'image/bmp': [b'BM'],
    'image/svg+xml': [b'<svg', b'<?xml'],
    
    # Видео
    'video/mp4': [b'\x00\x00\x00\x20ftyp', b'\x00\x00\x00\x18ftyp'],
    'video/quicktime': [b'\x00\x00\x00\x20ftypqt'],
    'video/x-msvideo': [b'RIFF'],
    'video/webm': [b'\x1a\x45\xdf\xa3'],
    
    # Аудио
    'audio/mpeg': [b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'],
    'audio/wav': [b'RIFF', b'WAVE'],
    'audio/ogg': [b'OggS'],
}

# Расширения файлов для различных типов
EXTENSION_TO_MIME = {
    # Изображения
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
    '.svg': 'image/svg+xml',
    
    # Видео
    '.mp4': 'video/mp4',
    '.mov': 'video/quicktime',
    '.avi': 'video/x-msvideo',
    '.webm': 'video/webm',
    '.mkv': 'video/x-matroska',
    
    # Аудио
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
}


def get_file_signature(file_path: str, max_bytes: int = 12) -> bytes:
    """
    Получить первые байты файла (магические байты)
    
    Args:
        file_path: Путь к файлу
        max_bytes: Максимальное количество байт для чтения
        
    Returns:
        Первые байты файла
    """
    try:
        with open(file_path, 'rb') as f:
            return f.read(max_bytes)
    except Exception as e:
        logger.error(f"Ошибка при чтении файла {file_path}: {e}")
        return b''


def detect_mime_type(file_path: str) -> Optional[str]:
    """
    Определить MIME тип файла по магическим байтам
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        MIME тип или None если не удалось определить
    """
    if not os.path.exists(file_path):
        return None
    
    # Сначала проверяем по расширению (быстрее)
    ext = Path(file_path).suffix.lower()
    if ext in EXTENSION_TO_MIME:
        mime_type = EXTENSION_TO_MIME[ext]
    else:
        mime_type = None
    
    # Затем проверяем по магическим байтам (надежнее)
    signature = get_file_signature(file_path)
    
    for mime, signatures in FILE_SIGNATURES.items():
        for sig in signatures:
            if signature.startswith(sig):
                return mime
    
    # Если не нашли по байтам, возвращаем по расширению
    return mime_type


def validate_file_type(file_path: str, allowed_types: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Проверить, соответствует ли тип файла разрешенным типам
    
    Args:
        file_path: Путь к файлу
        allowed_types: Список разрешенных MIME типов
        
    Returns:
        (is_valid, error_message) - кортеж с результатом проверки
    """
    if not os.path.exists(file_path):
        return False, f"Файл не существует: {file_path}"
    
    detected_type = detect_mime_type(file_path)
    
    if not detected_type:
        return False, "Не удалось определить тип файла"
    
    # Проверяем, соответствует ли тип разрешенным
    if detected_type not in allowed_types:
        allowed_str = ', '.join(allowed_types)
        return False, f"Тип файла {detected_type} не разрешен. Разрешенные типы: {allowed_str}"
    
    return True, None


def validate_image_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Проверить, является ли файл изображением
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        (is_valid, error_message)
    """
    allowed_image_types = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/bmp',
        'image/svg+xml'
    ]
    return validate_file_type(file_path, allowed_image_types)


def validate_video_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Проверить, является ли файл видео
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        (is_valid, error_message)
    """
    allowed_video_types = [
        'video/mp4',
        'video/quicktime',
        'video/x-msvideo',
        'video/webm',
        'video/x-matroska'
    ]
    return validate_file_type(file_path, allowed_video_types)


def validate_media_file(file_path: str, media_type: str = 'image') -> Tuple[bool, Optional[str]]:
    """
    Проверить медиа файл (изображение или видео)
    
    Args:
        file_path: Путь к файлу
        media_type: Тип медиа ('image' или 'video')
        
    Returns:
        (is_valid, error_message)
    """
    if media_type == 'image':
        return validate_image_file(file_path)
    elif media_type == 'video':
        return validate_video_file(file_path)
    else:
        return False, f"Неизвестный тип медиа: {media_type}"

