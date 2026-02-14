# Тестирование Landing Bot

## Структура тестов

```
tests/
├── conftest.py              # Pytest конфигурация и fixtures
├── fixtures/                # Дополнительные fixtures
│   ├── __init__.py
│   ├── telegram.py
│   ├── database.py
│   └── ai_agent.py
├── mocks/                   # Mock объекты
│   ├── __init__.py
│   └── mock_ai_agent.py     # Mock LandingAIAgent
├── test_conversation_flow.py    # Тесты flow диалога
├── test_database_persistence.py # Тесты персистентности БД
├── test_state_recovery.py       # Тесты восстановления состояния
└── test_ai_agent.py            # Тесты AI-агента
```

## Запуск тестов

### Все тесты
```bash
pytest
```

### Конкретный файл
```bash
pytest tests/test_ai_agent.py
```

### Конкретный тест
```bash
pytest tests/test_ai_agent.py::TestAIAgent::test_agent_initialization
```

### С покрытием кода
```bash
pytest --cov=backend --cov-report=html
```

### Только быстрые тесты
```bash
pytest -m "not slow"
```

### Verbose режим
```bash
pytest -v
```

## Fixtures

### test_db_session
In-memory SQLite база данных для тестов. Автоматически создает все таблицы и очищает после теста.

### mock_user, mock_chat, mock_message
Mock объекты Telegram API для тестирования handlers.

### mock_update, mock_update_with_callback
Mock Telegram Update объекты.

### mock_context
Mock CallbackContext для handlers.

### sample_user_data, sample_ai_agent_state
Примеры данных для тестирования.

## MockLandingAIAgent

`MockLandingAIAgent` - детерминированная замена `LandingAIAgent` для тестирования:

- Принимает user input
- Возвращает предсказуемые ответы
- Хранит состояние
- Поддерживает сериализацию/десериализацию

## Покрытие тестами

- ✅ Conversation flow (ConversationHandler)
- ✅ Database persistence (UserState)
- ✅ State recovery from database
- ✅ LandingAIAgent behavior
- ✅ Data collection and stage transitions

## Примечания

- Все тесты используют in-memory SQLite для изоляции
- Mock объекты не требуют реального Telegram API
- Тесты не изменяют бизнес-логику проекта
- Все async тесты используют pytest-asyncio

