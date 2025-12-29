import pytest
from datetime import datetime, timezone

from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole
from Backend.DomainLayer.Exceptions import ValidationError


class TestUserCreation:
    def test_create_user_with_defaults(self):
        user = User(id="user1", username="testuser")
        assert user.id == "user1"
        assert user.username == "testuser"
        assert user.role == UserRole.SOLVER
        assert user.xp == 0
        assert isinstance(user.created_at, datetime)

    def test_create_user_with_all_fields(self):
        now = datetime.now(timezone.utc)
        user = User(
            id="user2",
            username="creator",
            role=UserRole.CREATOR,
            xp=500,
            created_at=now
        )
        assert user.id == "user2"
        assert user.username == "creator"
        assert user.role == UserRole.CREATOR
        assert user.xp == 500
        assert user.created_at == now

    def test_create_user_missing_id(self):
        with pytest.raises(ValidationError) as exc_info:
            User(id="", username="testuser")
        assert "User.id is required" in str(exc_info.value)

    def test_create_user_missing_username(self):
        with pytest.raises(ValidationError) as exc_info:
            User(id="user1", username="")
        assert "User.username is required" in str(exc_info.value)

    def test_create_user_whitespace_username(self):
        with pytest.raises(ValidationError) as exc_info:
            User(id="user1", username="   ")
        assert "User.username is required" in str(exc_info.value)

    def test_create_user_negative_xp(self):
        with pytest.raises(ValidationError) as exc_info:
            User(id="user1", username="testuser", xp=-10)
        assert "User.xp cannot be negative" in str(exc_info.value)


class TestUserLevel:
    def test_level_calculation(self):
        user = User(id="user1", username="testuser", xp=0)
        assert user.level == 1

        user.xp = 99
        assert user.level == 1

        user.xp = 100
        assert user.level == 2

        user.xp = 500
        assert user.level == 6

    def test_is_experienced(self):
        user = User(id="user1", username="testuser", xp=400)
        assert not user.is_experienced  # level 5 not >= 5

        user.xp = 500
        assert user.is_experienced  # level 6 >= 5


class TestUserXP:
    def test_add_xp_positive(self):
        user = User(id="user1", username="testuser", xp=100)
        user.add_xp(50)
        assert user.xp == 150

    def test_add_xp_zero(self):
        user = User(id="user1", username="testuser", xp=100)
        user.add_xp(0)
        assert user.xp == 100

    def test_add_xp_negative(self):
        user = User(id="user1", username="testuser", xp=100)
        with pytest.raises(ValidationError) as exc_info:
            user.add_xp(-10)
        assert "XP amount must be non-negative" in str(exc_info.value)


class TestUserSetters:
    def test_set_id(self):
        user = User(id="user1", username="testuser")
        user.set_id("user2")
        assert user.get_id() == "user2"

    def test_set_id_empty(self):
        user = User(id="user1", username="testuser")
        with pytest.raises(ValidationError):
            user.set_id("")

    def test_set_username(self):
        user = User(id="user1", username="testuser")
        user.set_username("newuser")
        assert user.get_username() == "newuser"

    def test_set_username_empty(self):
        user = User(id="user1", username="testuser")
        with pytest.raises(ValidationError):
            user.set_username("  ")

    def test_set_role(self):
        user = User(id="user1", username="testuser")
        user.set_role(UserRole.CREATOR)
        assert user.get_role() == UserRole.CREATOR

    def test_set_role_invalid(self):
        user = User(id="user1", username="testuser")
        with pytest.raises(ValidationError):
            user.set_role("invalid")

    def test_set_xp(self):
        user = User(id="user1", username="testuser")
        user.set_xp(500)
        assert user.get_xp() == 500

    def test_set_xp_negative(self):
        user = User(id="user1", username="testuser")
        with pytest.raises(ValidationError):
            user.set_xp(-10)


class TestUserSerialization:
    def test_to_dict(self):
        now = datetime.now(timezone.utc)
        user = User(
            id="user1",
            username="testuser",
            role=UserRole.CREATOR,
            xp=250,
            created_at=now
        )
        d = user.to_dict()
        assert d["id"] == "user1"
        assert d["username"] == "testuser"
        assert d["role"] == "creator"
        assert d["xp"] == 250
        assert d["created_at"] == now.isoformat()

    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        d = {
            "id": "user1",
            "username": "testuser",
            "role": "creator",
            "xp": 250,
            "created_at": now.isoformat()
        }
        user = User.from_dict(d)
        assert user.id == "user1"
        assert user.username == "testuser"
        assert user.role == UserRole.CREATOR
        assert user.xp == 250

    def test_from_dict_partial(self):
        d = {
            "id": "user1",
            "username": "testuser",
        }
        user = User.from_dict(d)
        assert user.id == "user1"
        assert user.username == "testuser"
        assert user.role == UserRole.SOLVER
        assert user.xp == 0

    def test_roundtrip(self):
        original = User(
            id="user1",
            username="testuser",
            role=UserRole.ADMIN,
            xp=1000
        )
        d = original.to_dict()
        restored = User.from_dict(d)
        assert restored.id == original.id
        assert restored.username == original.username
        assert restored.role == original.role
        assert restored.xp == original.xp
