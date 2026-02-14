# Инструкция по тестированию

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Запуск тестов

### Все тесты
```bash
pytest
```

### С подробным выводом
```bash
pytest -v
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

Отчет будет в `htmlcov/index.html`

## Структура тестов

- **test_conversation_flow.py** - Тесты flow диалога через ConversationHandler
- **test_database_persistence.py** - Тесты персистентности данных в БД
- **test_state_recovery.py** - Тесты восстановления состояния из БД
- **test_ai_agent.py** - Тесты поведения AI-агента

## Особенности

- Все тесты используют in-memory SQLite для изоляции
- Mock объекты не требуют реального Telegram API
- Тесты не изменяют бизнес-логику проекта
- Все async тесты используют pytest-asyncio

## Troubleshooting

Если тесты не запускаются:

1. Убедитесь, что установлены все зависимости: `pip install -r requirements.txt`
2. Проверьте, что Python версии 3.11+
3. Убедитесь, что переменные окружения не требуются для тестов (они мокируются)

