# Руководство по миграциям базы данных

Этот проект использует Alembic для управления миграциями базы данных.

## Установка

Alembic уже включен в `requirements.txt`. Установите зависимости:

```bash
pip install -r requirements.txt
```

## Первоначальная настройка

Если это первый запуск, создайте начальную миграцию на основе текущих моделей:

```bash
alembic revision --autogenerate -m "Initial migration"
```

Это создаст файл миграции в `alembic/versions/`.

## Применение миграций

### Применить все миграции до последней версии:

```bash
alembic upgrade head
```

### Применить конкретную миграцию:

```bash
alembic upgrade <revision_id>
```

### Откатить последнюю миграцию:

```bash
alembic downgrade -1
```

### Откатить до конкретной версии:

```bash
alembic downgrade <revision_id>
```

## Создание новых миграций

### Автоматическое создание на основе изменений моделей:

```bash
alembic revision --autogenerate -m "Описание изменений"
```

### Создание пустой миграции (для ручных изменений):

```bash
alembic revision -m "Описание изменений"
```

## Просмотр информации

### Текущая версия БД:

```bash
alembic current
```

### История миграций:

```bash
alembic history
```

### Детальная информация о миграции:

```bash
alembic history -v
```

## Важные замечания

1. **Всегда проверяйте сгенерированные миграции** перед применением
2. **Делайте бэкап БД** перед применением миграций в продакшн
3. **Тестируйте миграции** на тестовой БД перед продакшн
4. **Не редактируйте примененные миграции** - создавайте новые

## Примеры

### Добавление нового поля в модель:

1. Измените модель в `backend/database/models.py`
2. Создайте миграцию:
   ```bash
   alembic revision --autogenerate -m "Add new field to User model"
   ```
3. Проверьте созданный файл миграции в `alembic/versions/`
4. Примените миграцию:
   ```bash
   alembic upgrade head
   ```

### Создание индекса:

1. Создайте пустую миграцию:
   ```bash
   alembic revision -m "Add index to users table"
   ```
2. Отредактируйте файл миграции, добавив код создания индекса
3. Примените миграцию:
   ```bash
   alembic upgrade head
   ```

## Структура файлов

```
alembic/
├── versions/          # Файлы миграций
├── env.py            # Конфигурация Alembic
├── script.py.mako    # Шаблон для миграций
└── README            # Документация
alembic.ini           # Основной конфигурационный файл
```

## Переменные окружения

Alembic автоматически использует `DATABASE_URL` из `backend/config.py`, который читается из переменной окружения `DATABASE_URL` или `.env` файла.

## Troubleshooting

### Ошибка "Target database is not up to date"

Это означает, что в БД есть миграции, которых нет в коде. Решения:
- Применить все миграции: `alembic upgrade head`
- Или пометить текущую версию: `alembic stamp head`

### Ошибка "Can't locate revision identified by"

Это означает, что история миграций не совпадает. Решения:
- Проверьте историю: `alembic history`
- Синхронизируйте версию: `alembic stamp head`
