"""
Точка входа приложения
Запуск Telegram бота для генерации лендингов
"""
import asyncio
import os
import sys
from backend.config import Config
from backend.bot.telegram_bot import LandingBot
from backend.database.database import init_db

# Настройка улучшенного логирования
from backend.utils.logger import setup_logging, get_logger

# Используем значения по умолчанию, если атрибуты отсутствуют (для обратной совместимости)
log_level = getattr(Config, 'LOG_LEVEL', 'INFO')
log_file = getattr(Config, 'LOG_FILE', 'bot.log')
log_max_bytes = getattr(Config, 'LOG_MAX_BYTES', 10485760)  # 10MB
log_backup_count = getattr(Config, 'LOG_BACKUP_COUNT', 5)

setup_logging(
    log_level=log_level,
    log_file=log_file,
    max_bytes=log_max_bytes,
    backup_count=log_backup_count
)

logger = get_logger(__name__)


async def main():
    """Главная функция запуска бота"""
    bot = None
    try:
        # Проверка конфигурации
        logger.info("Проверка конфигурации...")
        Config.validate()
        logger.info("✓ Конфигурация валидна")

        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        init_db()
        logger.info("✓ База данных инициализирована")

        # Очистка старых файлов
        logger.info("Очистка старых файлов...")
        from backend.utils.helpers import cleanup_old_files

        files_dir = Config.FILES_DIR
        if os.path.exists(files_dir):
            cleanup_old_files(files_dir, days_old=7)
            logger.info("✓ Старые файлы очищены")

        prompts_dir = os.path.join(files_dir, "prompts")
        if os.path.exists(prompts_dir):
            cleanup_old_files(prompts_dir, days_old=3)
            logger.info("✓ Старые промпты очищены")

        # Очищаем устаревший кэш промптов
        from backend.utils.cache import prompt_cache
        deleted_cache = prompt_cache.clear_expired()
        if deleted_cache > 0:
            logger.info(f"✓ Очищено {deleted_cache} устаревших записей кэша")

        # Создание и запуск бота
        logger.info("Создание Telegram бота...")
        bot = LandingBot()
        logger.info("✓ Бот создан")
        logger.info("Запуск бота...")
        await bot.start_polling()

    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки...")
        if bot is not None:
            await bot.stop()
            logger.info("Бот остановлен")

    except ValueError as e:
        logger.error(f"Ошибка конфигурации при старте: {e}")
        logger.error("Установите недостающие переменные и перезапустите бота.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════╗
║   Landing Bot - Генератор лендингов      ║
║   Версия: 1.0.0                           ║
╚═══════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Работа завершена")
