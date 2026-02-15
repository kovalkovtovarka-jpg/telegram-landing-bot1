"""
Webhook версия бота для продакшн
Используется вместо polling для более эффективной работы
"""
import asyncio
import logging
import sys
from aiohttp import web
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

# Глобальная переменная для бота
bot_instance = None

async def handle_webhook(request):
    """Обработчик webhook запросов от Telegram"""
    try:
        data = await request.json()
        
        # Создаем Update объект из данных
        from telegram import Update
        update = Update.de_json(data, bot_instance.app.bot)
        
        # Обрабатываем обновление через Application
        # В python-telegram-bot 20.7 используем process_update
        await bot_instance.app.process_update(update)
        
        return web.Response(text='OK', status=200)
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}", exc_info=True)
        return web.Response(text='Error', status=500)

async def start_webhook():
    """Запуск webhook сервера"""
    global bot_instance
    
    try:
        # Проверка конфигурации
        logger.info("Проверка конфигурации...")
        Config.validate()
        logger.info("✓ Конфигурация валидна")
        
        # Проверка webhook URL
        if not Config.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL не установлен. Установите переменную окружения WEBHOOK_URL")
        
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        init_db()
        logger.info("✓ База данных инициализирована")
        
        # Создание бота
        logger.info("Создание Telegram бота...")
        bot_instance = LandingBot()
        logger.info("✓ Бот создан")
        
        # Инициализация Application
        await bot_instance.app.initialize()
        await bot_instance.app.start()
        logger.info("✓ Application инициализирован")
        
        # Восстанавливаем AI-агентов из БД
        await bot_instance._restore_ai_agents_from_db()
        
        # Настройка webhook
        # Убираем лишние слеши в конце WEBHOOK_URL
        webhook_base = Config.WEBHOOK_URL.rstrip('/')
        webhook_url = f"{webhook_base}/webhook"
        logger.info(f"Настройка webhook: {webhook_url}")
        
        # Устанавливаем webhook через Application
        await bot_instance.app.bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query"]
        )
        logger.info(f"✓ Webhook установлен: {webhook_url}")
        
        # Создание web приложения
        app = web.Application()
        app.router.add_post('/webhook', handle_webhook)
        
        # Health check endpoint
        async def health_check(request):
            from backend.utils.health_check import check_health
            import json
            
            health = await check_health()
            
            if health['status'] == 'healthy':
                status_code = 200
            else:
                status_code = 503  # Service Unavailable
            
            return web.Response(
                text=json.dumps(health, indent=2, ensure_ascii=False),
                status=status_code,
                content_type='application/json'
            )
        
        app.router.add_get('/health', health_check)
        
        # Запуск сервера
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', Config.WEBHOOK_PORT)
        await site.start()
        
        logger.info(f"✓ Webhook сервер запущен на порту {Config.WEBHOOK_PORT}")
        logger.info(f"✓ Health check: http://0.0.0.0:{Config.WEBHOOK_PORT}/health")
        if Config.NOTIFY_ADMINS_ON_STARTUP:
            from datetime import datetime
            await bot_instance.notify_admins(
                f"✅ Бот запущен (webhook)\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
        # Бесконечное ожидание
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки...")
            await runner.cleanup()
            await bot_instance.app.bot.delete_webhook()
            await bot_instance.app.stop()
            await bot_instance.app.shutdown()
            logger.info("✓ Webhook удален")
            logger.info("Бот остановлен")
    
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        logger.error("Проверьте файл .env и установите необходимые переменные")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        if bot_instance is not None:
            try:
                await bot_instance.notify_admins(
                    f"🚨 Критическая ошибка при запуске webhook:\n{str(e)[:500]}"
                )
            except Exception:
                pass
        sys.exit(1)

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════╗
║   Landing Bot - Webhook Mode              ║
║   Версия: 1.0.0                           ║
╚═══════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(start_webhook())
    except KeyboardInterrupt:
        print("\n👋 Работа завершена")

