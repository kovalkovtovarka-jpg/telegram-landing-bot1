"""
Скрипт для проверки переменных окружения
Можно запустить локально или на сервере
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Список обязательных переменных
REQUIRED_VARS = {
    'TELEGRAM_BOT_TOKEN': 'Токен Telegram бота',
    'LLM_PROVIDER': 'Провайдер LLM (openai/anthropic/google)',
    'LLM_MODEL': 'Модель LLM',
    'LLM_TEMPERATURE': 'Температура',
    'LLM_MAX_TOKENS': 'Максимум токенов',
    'DATABASE_URL': 'URL базы данных',
    'FILES_DIR': 'Директория файлов',
    'MAX_REQUESTS_PER_HOUR': 'Лимит запросов'
}

# Переменные в зависимости от провайдера
PROVIDER_VARS = {
    'openai': ['OPENAI_API_KEY'],
    'anthropic': ['ANTHROPIC_API_KEY'],
    'google': ['GOOGLE_API_KEY']
}

# Опциональные переменные (для webhook)
OPTIONAL_VARS = {
    'WEBHOOK_URL': 'URL для webhook (опционально)',
    'WEBHOOK_PORT': 'Порт для webhook (опционально)',
    'BOT_ADMIN_IDS': 'ID администраторов (опционально)'
}

def check_env():
    """Проверка переменных окружения"""
    print("="*60)
    print("🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    print("="*60 + "\n")
    
    missing = []
    provider = os.getenv('LLM_PROVIDER', 'openai')
    
    # Проверяем обязательные переменные
    print("📋 Обязательные переменные:")
    for var, description in REQUIRED_VARS.items():
        value = os.getenv(var)
        if value:
            # Скрываем чувствительные данные
            if 'TOKEN' in var or 'KEY' in var:
                display_value = value[:10] + '...' if len(value) > 10 else '***'
            else:
                display_value = value
            print(f"  ✅ {var:25} = {display_value}")
        else:
            print(f"  ❌ {var:25} = НЕ УСТАНОВЛЕН ({description})")
            missing.append(var)
    
    # Проверяем переменные провайдера
    print(f"\n📋 Переменные для провайдера '{provider}':")
    if provider in PROVIDER_VARS:
        for var in PROVIDER_VARS[provider]:
            value = os.getenv(var)
            if value:
                display_value = value[:10] + '...' if len(value) > 10 else '***'
                print(f"  ✅ {var:25} = {display_value}")
            else:
                print(f"  ❌ {var:25} = НЕ УСТАНОВЛЕН (требуется для {provider})")
                missing.append(var)
    else:
        print(f"  ⚠️  Неизвестный провайдер: {provider}")
        print(f"     Поддерживаемые: {', '.join(PROVIDER_VARS.keys())}")
    
    # Проверяем опциональные переменные
    print(f"\n📋 Опциональные переменные:")
    for var, description in OPTIONAL_VARS.items():
        value = os.getenv(var)
        if value:
            if 'URL' in var:
                display_value = value[:30] + '...' if len(value) > 30 else value
            else:
                display_value = value
            print(f"  ✅ {var:25} = {display_value}")
        else:
            print(f"  ⚪ {var:25} = не установлен ({description})")
    
    # Итог
    print("\n" + "="*60)
    if missing:
        print(f"❌ Найдено {len(missing)} отсутствующих переменных:")
        for var in missing:
            print(f"   - {var}")
        print("\n⚠️  Установите отсутствующие переменные перед деплоем!")
        print("\n💡 Как установить на Abacus:")
        print("   1. Через веб-интерфейс: Settings → Environment Variables")
        print("   2. Через CLI: abacus env set VARIABLE_NAME=value")
        return False
    else:
        print("✅ Все переменные окружения установлены!")
        print("\n🎉 Готово к деплою!")
        return True

if __name__ == '__main__':
    success = check_env()
    exit(0 if success else 1)

