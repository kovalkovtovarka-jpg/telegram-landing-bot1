"""
Pytest configuration and shared fixtures
"""
import pytest
import os
from unittest.mock import Mock, MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from telegram import Update, Message, User, Chat, CallbackQuery
from telegram.ext import ContextTypes

# Импорты из проекта
from backend.database.models import Base, UserState
from backend.bot.telegram_bot import LandingBot, AI_MODE_SELECTION, AI_CONVERSATION, AI_GENERATING


@pytest.fixture(scope="function")
def test_db_session():
    """
    Создает in-memory SQLite базу данных для тестов.
    Автоматически создает все таблицы и очищает после теста.
    """
    # Используем SQLite in-memory для тестов
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    
    # Создаем сессию
    SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    
    # Возвращаем сессию
    db = SessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        SessionLocal.remove()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_user():
    """Создает mock Telegram User"""
    user = Mock(spec=User)
    user.id = 12345
    user.username = "test_user"
    user.first_name = "Test"
    user.last_name = "User"
    user.is_bot = False
    return user


@pytest.fixture
def mock_chat():
    """Создает mock Telegram Chat"""
    chat = Mock(spec=Chat)
    chat.id = 12345
    chat.type = "private"
    return chat


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Создает mock Telegram Message"""
    message = Mock(spec=Message)
    message.message_id = 1
    message.from_user = mock_user
    message.chat = mock_chat
    message.text = "Test message"
    message.date = None
    message.edit_text = AsyncMock(return_value=message)
    message.reply_text = AsyncMock(return_value=message)
    return message


@pytest.fixture
def mock_callback_query(mock_user, mock_chat, mock_message):
    """Создает mock Telegram CallbackQuery"""
    query = Mock(spec=CallbackQuery)
    query.id = "test_query_id"
    query.from_user = mock_user
    query.data = "test_data"
    query.message = mock_message
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


@pytest.fixture
def mock_update(mock_message, mock_callback_query):
    """Создает mock Telegram Update"""
    update = Mock(spec=Update)
    update.update_id = 1
    update.message = mock_message
    update.callback_query = None
    update.effective_user = mock_message.from_user
    update.effective_chat = mock_message.chat
    return update


@pytest.fixture
def mock_update_with_callback(mock_message, mock_callback_query):
    """Создает mock Telegram Update с callback_query"""
    update = Mock(spec=Update)
    update.update_id = 1
    update.message = None
    update.callback_query = mock_callback_query
    update.effective_user = mock_callback_query.from_user
    update.effective_chat = mock_message.chat
    return update


@pytest.fixture
def mock_context():
    """Создает mock CallbackContext"""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = Mock()
    context.bot.send_message = AsyncMock()
    context.bot.edit_message_text = AsyncMock()
    context.bot.send_document = AsyncMock()
    context.user_data = {}
    context.chat_data = {}
    context.bot_data = {}
    return context


@pytest.fixture
def mock_bot():
    """Создает mock LandingBot для тестирования"""
    # Устанавливаем минимальные переменные окружения для инициализации
    os.environ.setdefault('TELEGRAM_BOT_TOKEN', 'test_token')
    os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
    os.environ.setdefault('OPENAI_API_KEY', 'test_key')
    
    bot = Mock(spec=LandingBot)
    bot.ai_agents = {}
    bot.ai_agents_last_activity = {}
    bot._save_user_data = Mock()
    bot._get_user_data = Mock(return_value={})
    bot._clear_user_data = Mock()
    bot._save_ai_agent_state = Mock()
    return bot


@pytest.fixture
def sample_user_data():
    """Возвращает пример данных пользователя"""
    return {
        'mode': 'SINGLE',
        'general_info': {
            'goal': 'продажа',
            'target_audience': 'взрослые',
            'style': 'минималистичный'
        },
        'products': [{
            'product_name': 'Тестовый товар',
            'product_description': 'Описание товара',
            'new_price': 99,
            'old_price': 150
        }],
        'current_product_index': 0,
        'stage': 'general_info',
        'files': []
    }


@pytest.fixture
def sample_ai_agent_state():
    """Возвращает пример сериализованного состояния AI-агента"""
    return {
        'mode': 'SINGLE',
        'stage': 'general_info',
        'collected_data': {
            'mode': 'SINGLE',
            'general_info': {
                'goal': 'продажа',
                'target_audience': 'взрослые',
                'style': 'минималистичный'
            },
            'products': [],
            'current_product_index': 0,
            'stage': 'general_info',
            'files': []
        },
        'conversation_history': [
            {'role': 'assistant', 'content': 'Привет! Давайте создадим лендинг.'},
            {'role': 'user', 'content': 'Хочу создать лендинг для товара'}
        ]
    }

