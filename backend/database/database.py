"""
Управление базой данных
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from backend.database.models import Base
from backend.config import Config

# Создание движка БД
# Оптимизация для PostgreSQL (из DEPLOYMENT_INSTRUCTIONS.md)
if "postgresql" in Config.DATABASE_URL or "postgres" in Config.DATABASE_URL:
    engine = create_engine(
        Config.DATABASE_URL,
        echo=False,  # Включить для отладки SQL запросов
        pool_pre_ping=True,  # Проверка соединения перед использованием
        pool_size=10,  # Количество соединений
        max_overflow=20,  # Максимум дополнительных соединений
        pool_recycle=3600,  # Переподключение каждый час
    )
else:
    # Для SQLite
    engine = create_engine(
        Config.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False}
    )

# Создание сессии
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def init_db():
    """Инициализация базы данных (создание таблиц)"""
    Base.metadata.create_all(bind=engine)
    print("База данных инициализирована")

def get_db():
    """Получить сессию БД (для использования в контексте)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def close_db():
    """Закрыть все соединения с БД"""
    SessionLocal.remove()
