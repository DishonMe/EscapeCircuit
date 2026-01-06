import pytest
from datetime import datetime, timezone

from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole
from Backend.DomainLayer.Exceptions import ValidationError


class TestUserCreation:
    def test_create_user_with_defaults(self):
        user = User(id=1, username="testuser")
        assert user.id == 1
        assert user.username == "testuser"
        assert user.role == UserRole.SOLVER
        assert user.xp == 0
        assert isinstance(user.created_at, datetime)

    def test_create_user_with_all_fields(self):
        now = datetime.now(timezone.utc)
        user = User(
            id=2,
            username="creator",
            role=UserRole.CREATOR,
            xp=500,
            created_at=now
        )
        assert user.id == 2
        assert user.username == "creator"
        assert user.role == UserRole.CREATOR
        assert user.xp == 500
        assert user.created_at == now

    def test_create_user_zero_id(self):
        # ID=0 is not valid (ensure_non_negative_int rejects value <= 0)
        with pytest.raises(ValidationError) as exc_info:
            User(id=0, username="testuser")
        assert "cannot be negative" in str(exc_info.value)

    def test_create_user_missing_username(self):
        with pytest.raises(ValidationError) as exc_info:
            User(id=1, username="")
        assert "User.username is required" in str(exc_info.value)

    def test_create_user_whitespace_username(self):
        with pytest.raises(ValidationError) as exc_info:
            User(id=1, username="   ")
        assert "User.username is required" in str(exc_info.value)

    def test_create_user_negative_xp(self):
        with pytest.raises(ValidationError) as exc_info:
            User(id=1, username="testuser", xp=-10)
        assert "User.xp cannot be negative" in str(exc_info.value)


class TestUserLevel:
    def test_level_calculation(self):
        user = User(id=1, username="testuser", xp=0)
        assert user.level == 1

        user.xp = 99
        assert user.level == 1

        user.xp = 100
        assert user.level == 2

        user.xp = 500
        assert user.level == 6

    def test_is_experienced(self):
        user = User(id=1, username="testuser", xp=400)
        # xp=400 -> level = 1 + (400 // 100) = 5, and 5 >= 5 is True
        assert user.is_experienced

        user.xp = 399
        # xp=399 -> level = 1 + (399 // 100) = 4, and 4 >= 5 is False
        assert not user.is_experienced


class TestUserXP:
    def test_add_xp_positive(self):
        user = User(id=1, username="testuser", xp=100)
        user.add_xp(50)
        assert user.xp == 150

    def test_add_xp_zero(self):
        user = User(id=1, username="testuser", xp=100)
        user.add_xp(0)
        assert user.xp == 100

    def test_add_xp_negative(self):
        user = User(id=1, username="testuser", xp=100)
        with pytest.raises(ValidationError) as exc_info:
            user.add_xp(-10)
        assert "XP amount must be non-negative" in str(exc_info.value)


class TestUserSetters:
    def test_set_username(self):
        user = User(id=1, username="testuser")
        user.set_username("newuser")
        assert user.get_username() == "newuser"

    def test_set_username_empty(self):
        user = User(id=1, username="testuser")
        with pytest.raises(ValidationError):
            user.set_username("  ")

    def test_set_role(self):
        user = User(id=1, username="testuser")
        user.set_role(UserRole.CREATOR)
        assert user.get_role() == UserRole.CREATOR

    def test_set_role_invalid(self):
        user = User(id=1, username="testuser")
        with pytest.raises(ValidationError):
            user.set_role("invalid")

    def test_set_xp(self):
        user = User(id=1, username="testuser")
        user.set_xp(500)
        assert user.get_xp() == 500

    def test_set_xp_negative(self):
        user = User(id=1, username="testuser")
        with pytest.raises(ValidationError):
            user.set_xp(-10)


class TestUserSerialization:
    def test_to_dict(self):
        now = datetime.now(timezone.utc)
        user = User(
            id=1,
            username="testuser",
            role=UserRole.CREATOR,
            xp=250,
            created_at=now
        )
        d = user.to_dict()
        assert d["id"] == "1"
        assert d["username"] == "testuser"
        assert d["role"] == "creator"
        assert d["xp"] == 250
        assert d["createdAt"] == int(now.timestamp() * 1000)

    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        d = {
            "id": 1,
            "username": "testuser",
            "role": "creator",
            "xp": 250,
            "created_at": now.isoformat()
        }
        user = User.from_dict(d)
        assert user.id == 1
        assert user.username == "testuser"
        assert user.role == UserRole.CREATOR
        assert user.xp == 250

    def test_from_dict_partial(self):
        d = {
            "id": 1,
            "username": "testuser",
        }
        user = User.from_dict(d)
        assert user.id == 1
        assert user.username == "testuser"
        assert user.role == UserRole.SOLVER
        assert user.xp == 0

    def test_roundtrip(self):
        original = User(
            id=1,
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

class TestUserBranches:
    """Test missing branches in User.py"""
    
    def test_is_experienced_boundary_level_5(self):
        """Test is_experienced when level is exactly 5"""
        # xp=400: level = 1 + (400 // 100) = 5
        user = User(id=1, username="test", xp=400)
        assert user.level == 5
        assert user.is_experienced is True
    
    def test_is_experienced_boundary_level_4(self):
        """Test is_experienced when level is exactly 4"""
        # xp=399: level = 1 + (399 // 100) = 4
        user = User(id=1, username="test", xp=399)
        assert user.level == 4
        assert user.is_experienced is False
    
    def test_add_xp_exactly_zero(self):
        """Test add_xp with exactly zero"""
        user = User(id=1, username="test", xp=100)
        user.add_xp(0)
        assert user.xp == 100
    
    def test_set_role_valid_type_check(self):
        """Test set_role with valid UserRole"""
        user = User(id=1, username="test")
        user.set_role(UserRole.CREATOR)
        assert user.role == UserRole.CREATOR
        assert isinstance(user.role, UserRole)


class TestUserGetters:
    """Test all User getter methods"""
    
    def test_get_id(self):
        user = User(id=42, username="test")
        assert user.get_id() == 42
    
    def test_get_username(self):
        user = User(id=1, username="testuser")
        assert user.get_username() == "testuser"
    
    def test_get_role(self):
        user = User(id=1, username="test", role=UserRole.CREATOR)
        assert user.get_role() == UserRole.CREATOR
    
    def test_get_xp(self):
        user = User(id=1, username="test", xp=500)
        assert user.get_xp() == 500
    
    def test_get_created_at(self):
        now = datetime.now(timezone.utc)
        user = User(id=1, username="test", created_at=now)
        assert user.get_created_at() == now