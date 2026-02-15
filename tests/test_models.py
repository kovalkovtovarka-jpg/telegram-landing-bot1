"""
Тесты для backend.database.models
"""
import pytest

from backend.database.models import User, Project, Generation, UserState


class TestUser:
    def test_repr(self):
        u = User(telegram_id="123", username="test")
        r = repr(u)
        assert "123" in r
        assert "test" in r

    def test_defaults(self, test_db_session):
        u = User(telegram_id="456")
        test_db_session.add(u)
        test_db_session.flush()
        assert u.is_active is True
        assert u.username is None

    def test_persist_and_retrieve(self, test_db_session):
        u = User(telegram_id="789", username="persist_test")
        test_db_session.add(u)
        test_db_session.commit()
        loaded = test_db_session.query(User).filter(User.telegram_id == "789").first()
        assert loaded is not None
        assert loaded.username == "persist_test"


class TestProject:
    def test_repr(self):
        p = Project(id=1, template_id="t1", template_name="Template", user_id=1, user_data={})
        r = repr(p)
        assert "t1" in r
        assert "pending" in r or "status" in r

    def test_default_status(self, test_db_session):
        user = User(telegram_id="owner", username="u")
        test_db_session.add(user)
        test_db_session.flush()
        p = Project(template_id="t", template_name="T", user_id=user.id, user_data={})
        test_db_session.add(p)
        test_db_session.flush()
        assert p.status == "pending"


class TestGeneration:
    def test_repr(self):
        g = Generation(project_id=1, user_id="u1", prompt="p", success=True)
        r = repr(g)
        assert "1" in r
        assert "True" in r or "success" in r

    def test_default_success(self, test_db_session):
        user = User(telegram_id="gen_user", username="u")
        test_db_session.add(user)
        test_db_session.flush()
        proj = Project(template_id="t", template_name="T", user_id=user.id, user_data={})
        test_db_session.add(proj)
        test_db_session.flush()
        g = Generation(project_id=proj.id, user_id="u1", prompt="p")
        test_db_session.add(g)
        test_db_session.flush()
        assert g.success is False


class TestUserState:
    def test_repr(self):
        s = UserState(user_id="111", state="COLLECTING", data={})
        r = repr(s)
        assert "111" in r
        assert "COLLECTING" in r

    def test_default_data(self):
        s = UserState(user_id="222", state="S", data={})
        assert s.data == {}

    def test_persist_and_retrieve(self, test_db_session):
        s = UserState(user_id="333", state="AI_CONVERSATION", data={"key": "value"})
        test_db_session.add(s)
        test_db_session.commit()
        loaded = test_db_session.query(UserState).filter(UserState.user_id == "333").first()
        assert loaded is not None
        assert loaded.data == {"key": "value"}
