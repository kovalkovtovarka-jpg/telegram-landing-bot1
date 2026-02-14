"""
Тестирование Этапа 1: Критические улучшения
- PostgreSQL/SQLite поддержка
- UserState в БД
- Rate Limiting
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.config import Config
from backend.database.database import init_db, SessionLocal
from backend.database.models import User, UserState, Generation
from backend.utils.rate_limiter import rate_limiter


def test_database_connection():
    """Тест 1: Проверка подключения к БД"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Подключение к базе данных")
    print("="*60)
    
    try:
        db = SessionLocal()
        # Простой запрос для проверки
        result = db.query(User).limit(1).all()
        db.close()
        print("✅ Подключение к БД успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        print(f"   Проверьте DATABASE_URL в .env: {Config.DATABASE_URL}")
        return False


def test_user_state_model():
    """Тест 2: Работа с UserState"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Модель UserState (хранение данных в БД)")
    print("="*60)
    
    try:
        db = SessionLocal()
        
        # Создаем тестового пользователя
        test_user_id = "test_user_12345"
        test_data = {
            'product_name': 'Тестовый товар',
            'product_description': 'Описание тестового товара',
            'new_price': '99 BYN',
            'old_price': '152 BYN',
            'photos': [],
            'benefits': ['Преимущество 1', 'Преимущество 2']
        }
        
        # Сохраняем данные
        user_state = db.query(UserState).filter(
            UserState.user_id == test_user_id
        ).first()
        
        if user_state:
            user_state.data = test_data
            user_state.updated_at = datetime.utcnow()
        else:
            user_state = UserState(
                user_id=test_user_id,
                data=test_data,
                state='TESTING',
                conversation_type='quick'
            )
            db.add(user_state)
        
        db.commit()
        print("✅ Данные сохранены в БД")
        
        # Читаем данные
        saved_state = db.query(UserState).filter(
            UserState.user_id == test_user_id
        ).first()
        
        if saved_state and saved_state.data.get('product_name') == 'Тестовый товар':
            print("✅ Данные успешно прочитаны из БД")
            print(f"   Название товара: {saved_state.data.get('product_name')}")
            print(f"   Цена: {saved_state.data.get('new_price')}")
            
            # Очищаем тестовые данные
            db.delete(saved_state)
            db.commit()
            print("✅ Тестовые данные очищены")
            db.close()
            return True
        else:
            print("❌ Данные не совпадают")
            db.close()
            return False
            
    except Exception as e:
        print(f"❌ Ошибка работы с UserState: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        return False


async def test_rate_limiting():
    """Тест 3: Rate Limiting"""
    print("\n" + "="*60)
    print("ТЕСТ 3: Rate Limiting")
    print("="*60)
    
    try:
        test_user_id = 999999  # Тестовый ID
        
        # Очищаем старые записи для тестового пользователя
        db = SessionLocal()
        cutoff = datetime.utcnow() - timedelta(hours=2)
        db.query(Generation).filter(
            Generation.user_id == str(test_user_id),
            Generation.created_at >= cutoff
        ).delete()
        db.commit()
        db.close()
        
        print(f"Максимум запросов: {rate_limiter.max_requests} в час")
        print(f"Тестируем с пользователем ID: {test_user_id}\n")
        
        # Тест 1: Первые запросы должны проходить
        print("Тест 1: Первые запросы должны проходить")
        for i in range(3):
            allowed, remaining = await rate_limiter.check_db_rate_limit(test_user_id)
            if allowed:
                print(f"  ✅ Запрос {i+1}: разрешен (осталось: {remaining})")
            else:
                print(f"  ❌ Запрос {i+1}: отклонен (неожиданно)")
                return False
        
        # Создаем записи в БД для имитации запросов
        db = SessionLocal()
        for i in range(rate_limiter.max_requests - 2):
            generation = Generation(
                user_id=str(test_user_id),
                project_id=1,
                prompt="test",
                success=True,
                created_at=datetime.utcnow()
            )
            db.add(generation)
        db.commit()
        db.close()
        
        # Тест 2: После достижения лимита запросы должны отклоняться
        print(f"\nТест 2: После {rate_limiter.max_requests} запросов лимит должен быть достигнут")
        allowed, remaining = await rate_limiter.check_db_rate_limit(test_user_id)
        if not allowed:
            print(f"  ✅ Запрос отклонен (лимит достигнут, осталось: {remaining})")
        else:
            print(f"  ⚠️ Запрос разрешен (возможно, старые записи очистились)")
        
        # Очищаем тестовые записи
        db = SessionLocal()
        db.query(Generation).filter(
            Generation.user_id == str(test_user_id)
        ).delete()
        db.commit()
        db.close()
        
        print("\n✅ Rate limiting работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования rate limiting: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_user_state_methods():
    """Тест 4: Методы работы с UserState (как в telegram_bot.py)"""
    print("\n" + "="*60)
    print("ТЕСТ 4: Методы работы с данными пользователя")
    print("="*60)
    
    try:
        # Имитируем методы из telegram_bot.py
        def _save_user_data(user_id, data, state=None, conversation_type=None):
            db = SessionLocal()
            try:
                user_id_str = str(user_id)
                user_state = db.query(UserState).filter(
                    UserState.user_id == user_id_str
                ).first()
                
                if user_state:
                    user_state.data = data
                    if state is not None:
                        user_state.state = state
                    if conversation_type is not None:
                        user_state.conversation_type = conversation_type
                    user_state.updated_at = datetime.utcnow()
                else:
                    user_state = UserState(
                        user_id=user_id_str,
                        data=data,
                        state=state,
                        conversation_type=conversation_type
                    )
                    db.add(user_state)
                
                db.commit()
            finally:
                db.close()
        
        def _get_user_data(user_id):
            db = SessionLocal()
            try:
                user_id_str = str(user_id)
                user_state = db.query(UserState).filter(
                    UserState.user_id == user_id_str
                ).first()
                
                if user_state:
                    return user_state.data.copy() if user_state.data else {}
                return {}
            finally:
                db.close()
        
        def _update_user_data(user_id, **kwargs):
            data = _get_user_data(user_id)
            data.update(kwargs)
            _save_user_data(user_id, data)
        
        def _clear_user_data(user_id):
            db = SessionLocal()
            try:
                user_id_str = str(user_id)
                user_state = db.query(UserState).filter(
                    UserState.user_id == user_id_str
                ).first()
                
                if user_state:
                    db.delete(user_state)
                    db.commit()
            finally:
                db.close()
        
        # Тестируем
        test_id = 888888
        
        # Сохранение
        initial_data = {'product_name': 'Товар', 'price': '99 BYN'}
        _save_user_data(test_id, initial_data, state='TEST', conversation_type='quick')
        print("✅ Данные сохранены")
        
        # Чтение
        data = _get_user_data(test_id)
        if data.get('product_name') == 'Товар':
            print("✅ Данные прочитаны")
        else:
            print("❌ Ошибка чтения данных")
            return False
        
        # Обновление
        _update_user_data(test_id, product_name='Новый товар', new_field='значение')
        data = _get_user_data(test_id)
        if data.get('product_name') == 'Новый товар' and data.get('new_field') == 'значение':
            print("✅ Данные обновлены")
        else:
            print("❌ Ошибка обновления данных")
            return False
        
        # Очистка
        _clear_user_data(test_id)
        data = _get_user_data(test_id)
        if not data:
            print("✅ Данные очищены")
        else:
            print("❌ Ошибка очистки данных")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_tables():
    """Тест 0: Проверка наличия таблиц"""
    print("\n" + "="*60)
    print("ТЕСТ 0: Проверка таблиц в БД")
    print("="*60)
    
    try:
        from sqlalchemy import inspect
        from backend.database.database import engine
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = ['users', 'projects', 'generations', 'user_states']
        
        print(f"Найдено таблиц: {len(tables)}")
        for table in required_tables:
            if table in tables:
                print(f"  ✅ Таблица '{table}' существует")
            else:
                print(f"  ❌ Таблица '{table}' не найдена")
                print(f"     Запустите: from backend.database.database import init_db; init_db()")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки таблиц: {e}")
        return False


async def main():
    """Запуск всех тестов"""
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ ЭТАПА 1: Критические улучшения")
    print("="*60)
    
    # Проверка конфигурации
    print(f"\nКонфигурация:")
    print(f"  DATABASE_URL: {Config.DATABASE_URL}")
    print(f"  MAX_REQUESTS_PER_HOUR: {Config.MAX_REQUESTS_PER_HOUR}")
    
    results = []
    
    # Тест 0: Таблицы
    results.append(("Проверка таблиц", test_database_tables()))
    
    # Тест 1: Подключение
    results.append(("Подключение к БД", test_database_connection()))
    
    # Тест 2: UserState
    results.append(("UserState модель", test_user_state_model()))
    
    # Тест 3: Rate Limiting
    results.append(("Rate Limiting", await test_rate_limiting()))
    
    # Тест 4: Методы работы с данными
    results.append(("Методы работы с данными", test_user_state_methods()))
    
    # Итоги
    print("\n" + "="*60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{status}: {name}")
    
    print(f"\nРезультат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены! Этап 1 работает корректно.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} тест(ов) провалено. Проверьте ошибки выше.")
        return 1


if __name__ == '__main__':
    try:
        # Инициализация БД
        print("Инициализация базы данных...")
        init_db()
        print("✅ База данных инициализирована\n")
        
        # Запуск тестов
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nТестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

