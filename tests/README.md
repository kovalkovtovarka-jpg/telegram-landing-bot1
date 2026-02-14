# Тестирование Landing Bot

## Первый запуск тестов — пошагово

### Вариант А: Запуск на своём компьютере (локально)

**Шаг 1. Откройте терминал в папке проекта**

- В **Cursor / VS Code**: меню **Terminal** → **New Terminal** (или сочетание `` Ctrl+` ``). Убедитесь, что внизу открылась панель с чёрным/синим окном и приглашением вроде `PS D:\Сайты\creativelandingbotfixed>`.
- Либо откройте **PowerShell** или **cmd** из меню Пуск и перейдите в папку проекта:
  ```text
  cd D:\Сайты\creativelandingbotfixed
  ```

**Шаг 2. Установите зависимости для тестов (один раз)**

В терминале введите и нажмите **Enter**:

```bash
pip install -r requirements.txt
```

Затем:

```bash
pip install -r requirements-dev.txt
```

Дождитесь окончания установки (без ошибок).

**Шаг 3. Запустите тесты**

В том же терминале введите и нажмите **Enter**:

```bash
pytest
```

**Шаг 4. Смотрите результат**

- В конце вывода будет строка вида: `X passed in Y.XXs` — значит, все тесты прошли.
- Если есть падения: будет блок `FAILED` с путём к тесту и кратким описанием ошибки.

Чтобы запустить только один файл тестов (например, первый раз — один простой файл):

```bash
pytest tests/test_ai_agent.py
```

---

### Вариант Б: Автоматический запуск на GitHub (CI)

Тесты запускаются сами при каждом **push** в ветку `main` или `master`.

**Шаг 1. Убедитесь, что проект залит на GitHub**

- Репозиторий создан, код загружен (через GitHub Desktop, командную строку или браузер).

**Шаг 2. Сделайте push (если что-то меняли)**

- В **GitHub Desktop**: нажмите **Commit to main**, затем **Push origin**.
- Или в терминале из папки проекта:
  ```bash
  git add .
  git commit -m "Update"
  git push origin main
  ```

**Шаг 3. Откройте вкладку Actions на GitHub**

1. Откройте в браузере ваш репозиторий на **github.com** (например, `https://github.com/ВАШ_ЛОГИН/telegram-landing-bot`).
2. Вверху страницы репозитория нажмите вкладку **Actions** (между **Pull requests** и **Projects**).

**Шаг 4. Запуск и результат**

- Слева в списке workflow выберите **CI**.
- В списке запусков сверху будет последний (например, «Update» или «Initial commit»). Нажмите на него.
- Откроется страница запуска: один шаг (job) — **tests**. Нажмите на **tests**.
- Увидите лог: установка Python, установка зависимостей, затем запуск `pytest` и вывод тестов.
- Зелёная галочка у запуска = все тесты прошли. Красный крестик = есть упавшие тесты; в логе будет видно, какой тест и почему упал.

Дополнительно настраивать ничего не нужно: при каждом новом push тесты запустятся снова автоматически.

---

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
├── test_ai_agent.py             # Тесты AI-агента
├── test_prompt_builder.py       # Тесты NewPromptBuilder (стили, цвета, промпт)
├── test_code_generator.py       # Тесты CodeGenerator (с моками LLM)
└── test_error_messages.py       # Тесты форматирования ошибок для пользователя
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

