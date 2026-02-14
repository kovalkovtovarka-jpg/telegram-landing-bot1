"""
Тесты для проверки персистентности данных в БД
"""
import pytest
from datetime import datetime
from backend.database.models import UserState, User, Project


class TestDatabasePersistence:
    """Тесты для работы с базой данных"""
    
    def test_user_state_creation(self, test_db_session):
        """Тест: создание записи UserState"""
        user_state = UserState(
            user_id="12345",
            state="AI_CONVERSATION",
            data={"test": "data"},
            conversation_type="ai_agent"
        )
        
        test_db_session.add(user_state)
        test_db_session.commit()
        
        # Проверяем, что запись создана
        retrieved = test_db_session.query(UserState).filter(
            UserState.user_id == "12345"
        ).first()
        
        assert retrieved is not None
        assert retrieved.user_id == "12345"
        assert retrieved.state == "AI_CONVERSATION"
        assert retrieved.data == {"test": "data"}
        assert retrieved.conversation_type == "ai_agent"
    
    def test_user_state_update(self, test_db_session):
        """Тест: обновление записи UserState"""
        # Создаем запись
        user_state = UserState(
            user_id="12345",
            state="AI_CONVERSATION",
            data={"old": "data"},
            conversation_type="ai_agent"
        )
        test_db_session.add(user_state)
        test_db_session.commit()
        
        # Обновляем
        user_state.data = {"new": "data"}
        user_state.state = "AI_GENERATING"
        test_db_session.commit()
        
        # Проверяем обновление
        retrieved = test_db_session.query(UserState).filter(
            UserState.user_id == "12345"
        ).first()
        
        assert retrieved.data == {"new": "data"}
        assert retrieved.state == "AI_GENERATING"
    
    def test_user_state_retrieval(self, test_db_session):
        """Тест: получение записи UserState"""
        # Создаем несколько записей
        for i in range(3):
            user_state = UserState(
                user_id=f"1234{i}",
                state="AI_CONVERSATION",
                data={"user": i},
                conversation_type="ai_agent"
            )
            test_db_session.add(user_state)
        test_db_session.commit()
        
        # Получаем конкретную запись
        retrieved = test_db_session.query(UserState).filter(
            UserState.user_id == "12342"
        ).first()
        
        assert retrieved is not None
        assert retrieved.user_id == "12342"
        assert retrieved.data == {"user": 2}
    
    def test_user_state_with_ai_agent_data(self, test_db_session, sample_ai_agent_state):
        """Тест: сохранение данных AI-агента в UserState"""
        user_state = UserState(
            user_id="12345",
            state="AI_CONVERSATION",
            data={
                "ai_agent_state": sample_ai_agent_state,
                "last_activity": 1234567890.0
            },
            conversation_type="ai_agent"
        )
        
        test_db_session.add(user_state)
        test_db_session.commit()
        
        # Проверяем сохранение
        retrieved = test_db_session.query(UserState).filter(
            UserState.user_id == "12345"
        ).first()
        
        assert retrieved is not None
        assert "ai_agent_state" in retrieved.data
        assert retrieved.data["ai_agent_state"]["mode"] == "SINGLE"
        assert retrieved.data["ai_agent_state"]["stage"] == "general_info"
        assert "last_activity" in retrieved.data
    
    def test_user_state_deletion(self, test_db_session):
        """Тест: удаление записи UserState"""
        # Создаем запись
        user_state = UserState(
            user_id="12345",
            state="AI_CONVERSATION",
            data={"test": "data"},
            conversation_type="ai_agent"
        )
        test_db_session.add(user_state)
        test_db_session.commit()
        
        # Удаляем
        test_db_session.delete(user_state)
        test_db_session.commit()
        
        # Проверяем удаление
        retrieved = test_db_session.query(UserState).filter(
            UserState.user_id == "12345"
        ).first()
        
        assert retrieved is None
    
    def test_multiple_user_states(self, test_db_session):
        """Тест: работа с несколькими UserState одновременно"""
        # Создаем несколько записей
        states = []
        for i in range(5):
            state = UserState(
                user_id=f"user_{i}",
                state="AI_CONVERSATION",
                data={"index": i},
                conversation_type="ai_agent"
            )
            states.append(state)
            test_db_session.add(state)
        test_db_session.commit()
        
        # Проверяем количество
        count = test_db_session.query(UserState).count()
        assert count == 5
        
        # Проверяем каждую запись
        for i in range(5):
            retrieved = test_db_session.query(UserState).filter(
                UserState.user_id == f"user_{i}"
            ).first()
            assert retrieved is not None
            assert retrieved.data["index"] == i
    
    def test_user_state_timestamps(self, test_db_session):
        """Тест: автоматическое обновление timestamps"""
        user_state = UserState(
            user_id="12345",
            state="AI_CONVERSATION",
            data={},
            conversation_type="ai_agent"
        )
        test_db_session.add(user_state)
        test_db_session.commit()
        
        created_at = user_state.created_at
        updated_at = user_state.updated_at
        
        # Обновляем запись
        user_state.data = {"updated": True}
        test_db_session.commit()
        
        # Проверяем, что updated_at изменился
        assert user_state.updated_at > updated_at
        assert user_state.created_at == created_at
    
    def test_user_state_json_storage(self, test_db_session):
        """Тест: хранение сложных JSON структур"""
        complex_data = {
            "ai_agent_state": {
                "mode": "SINGLE",
                "stage": "products",
                "collected_data": {
                    "general_info": {
                        "goal": "продажа",
                        "target_audience": "взрослые"
                    },
                    "products": [
                        {
                            "product_name": "Товар 1",
                            "price": 99
                        }
                    ]
                },
                "conversation_history": [
                    {"role": "user", "content": "Привет"},
                    {"role": "assistant", "content": "Привет! Как дела?"}
                ]
            },
            "last_activity": 1234567890.0,
            "metadata": {
                "version": "1.0",
                "source": "test"
            }
        }
        
        user_state = UserState(
            user_id="12345",
            state="AI_CONVERSATION",
            data=complex_data,
            conversation_type="ai_agent"
        )
        
        test_db_session.add(user_state)
        test_db_session.commit()
        
        # Проверяем восстановление
        retrieved = test_db_session.query(UserState).filter(
            UserState.user_id == "12345"
        ).first()
        
        assert retrieved.data == complex_data
        assert retrieved.data["ai_agent_state"]["mode"] == "SINGLE"
        assert len(retrieved.data["ai_agent_state"]["collected_data"]["products"]) == 1

