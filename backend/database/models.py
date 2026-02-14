"""
Модели базы данных
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    projects = relationship('Project', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class Project(Base):
    """Модель проекта лендинга"""
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    template_id = Column(String(100), nullable=False)
    template_name = Column(String(200), nullable=False)
    
    # Данные пользователя для генерации
    user_data = Column(JSON, nullable=False)
    
    # Результаты генерации
    files_path = Column(String(500), nullable=True)  # Путь к папке с файлами
    html_file = Column(String(500), nullable=True)
    css_file = Column(String(500), nullable=True)
    js_file = Column(String(500), nullable=True)
    php_file = Column(String(500), nullable=True)
    zip_file = Column(String(500), nullable=True)  # Архивированный файл
    
    # Статус генерации
    status = Column(String(50), default='pending')  # pending, generating, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Метаданные
    generation_time = Column(Integer, nullable=True)  # Время генерации в секундах
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user = relationship('User', back_populates='projects')
    
    def __repr__(self):
        return f"<Project(id={self.id}, template={self.template_id}, status={self.status})>"


class Generation(Base):
    """Модель истории генераций"""
    __tablename__ = 'generations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)  # Для rate limiting
    
    # Детали генерации
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    
    # Метрики
    tokens_used = Column(Integer, nullable=True)
    generation_time = Column(Integer, nullable=True)  # В секундах
    
    # Статус
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Generation(id={self.id}, project_id={self.project_id}, success={self.success})>"


class UserState(Base):
    """Модель для хранения состояния пользователя в БД"""
    __tablename__ = 'user_states'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)
    state = Column(String(50), nullable=True)  # Текущее состояние диалога
    data = Column(JSON, nullable=False, default=dict)  # Все данные пользователя
    conversation_type = Column(String(50), nullable=True)  # 'quick' или 'create'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserState(user_id={self.user_id}, state={self.state})>"
