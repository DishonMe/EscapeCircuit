import pytest
from datetime import datetime, timezone

from Backend.DomainLayer.Rating import Rating
from Backend.DomainLayer.Exceptions import ValidationError


class TestRatingCreation:
    def test_create_rating_basic(self):
        rating = Rating(
            id=1,
            puzzle_id=1,
            user_id=1,
            difficulty=3,
            fun=4,
            clearness=3
        )
        assert rating.id == 1
        assert rating.puzzle_id == 1
        assert rating.user_id == 1
        assert rating.difficulty == 3
        assert rating.fun == 4
        assert rating.clearness == 3
        assert rating.is_experienced_at_rating == False

    def test_create_rating_with_level(self):
        now = datetime.now(timezone.utc)
        rating = Rating(
            id=1,
            puzzle_id=1,
            user_id=1,
            difficulty=5,
            fun=5,
            clearness=5,
            created_at=now,
            is_experienced_at_rating=True
        )
        assert rating.is_experienced_at_rating == True

    def test_create_rating_zero_id(self):
        # ID=0 is valid (non-negative includes zero)
        rating = Rating(id=0, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        assert rating.id == 0

    def test_create_rating_missing_puzzle_id(self):
        with pytest.raises(TypeError):
            Rating(id=1, user_id=1, difficulty=3, fun=3, clearness=3)

    def test_create_rating_missing_user_id(self):
        with pytest.raises(TypeError):
            Rating(id=1, puzzle_id=1, difficulty=3, fun=3, clearness=3)


class TestRatingValidation:
    def test_rating_difficulty_invalid_min(self):
        with pytest.raises(ValidationError) as exc_info:
            Rating(
                id=1,
                puzzle_id=1,
                user_id=1,
                difficulty=0,  # Out of range
                fun=3,
                clearness=3
            )
        assert "difficulty must be in [1, 5]" in str(exc_info.value)

    def test_rating_difficulty_invalid_max(self):
        with pytest.raises(ValidationError) as exc_info:
            Rating(
                id=1,
                puzzle_id=1,
                user_id=1,
                difficulty=10,  # Out of range
                fun=3,
                clearness=3
            )
        assert "difficulty must be in [1, 5]" in str(exc_info.value)

    def test_rating_fun_invalid_min(self):
        with pytest.raises(ValidationError) as exc_info:
            Rating(
                id=1,
                puzzle_id=1,
                user_id=1,
                difficulty=3,
                fun=-5,  # Out of range
                clearness=3
            )
        assert "fun must be in [1, 5]" in str(exc_info.value)

    def test_rating_fun_invalid_max(self):
        with pytest.raises(ValidationError) as exc_info:
            Rating(
                id=1,
                puzzle_id=1,
                user_id=1,
                difficulty=3,
                fun=100,  # Out of range
                clearness=3
            )
        assert "fun must be in [1, 5]" in str(exc_info.value)

    def test_rating_clearness_invalid_min(self):
        with pytest.raises(ValidationError) as exc_info:
            Rating(
                id=1,
                puzzle_id=1,
                user_id=1,
                difficulty=3,
                fun=3,
                clearness=0  # Out of range
            )
        assert "clearness must be in [1, 5]" in str(exc_info.value)

    def test_rating_clearness_invalid_max(self):
        with pytest.raises(ValidationError) as exc_info:
            Rating(
                id=1,
                puzzle_id=1,
                user_id=1,
                difficulty=3,
                fun=3,
                clearness=10  # Out of range
            )
        assert "clearness must be in [1, 5]" in str(exc_info.value)

    def test_rating_all_fields_valid_range(self):
        for val in [1, 2, 3, 4, 5]:
            rating = Rating(
                id=1,
                puzzle_id=1,
                user_id=1,
                difficulty=val,
                fun=val,
                clearness=val
            )
            assert rating.difficulty == val
            assert rating.fun == val
            assert rating.clearness == val

    def test_rating_is_experienced_at_rating_invalid_type(self):
        """Test that invalid is_experienced_at_rating type raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3, is_experienced_at_rating="yes")
        assert "Rating.is_experienced_at_rating must be bool" in str(exc_info.value)


class TestRatingExperienced:
    def test_is_experienced_true(self):
        rating = Rating(
            id=1,
            puzzle_id=1,
            user_id=1,
            difficulty=3,
            fun=3,
            clearness=3,
            is_experienced_at_rating=True
        )
        assert rating.is_experienced

    def test_is_experienced_false(self):
        rating = Rating(
            id=1,
            puzzle_id=1,
            user_id=1,
            difficulty=3,
            fun=3,
            clearness=3,
            is_experienced_at_rating=False
        )
        assert not rating.is_experienced

    def test_is_experienced_default_false(self):
        rating = Rating(
            id=1,
            puzzle_id=1,
            user_id=1,
            difficulty=3,
            fun=3,
            clearness=3
        )
        assert not rating.is_experienced


class TestRatingSerialization:
    def test_to_dict(self):
        now = datetime.now(timezone.utc)
        rating = Rating(
            id=1,
            puzzle_id=1,
            user_id=1,
            difficulty=4,
            fun=5,
            clearness=3,
            created_at=now,
            is_experienced_at_rating=True
        )
        d = rating.to_dict()
        assert d["id"] == 1
        assert d["puzzle_id"] == 1
        assert d["user_id"] == 1
        assert d["difficulty"] == 4
        assert d["fun"] == 5
        assert d["clearness"] == 3
        assert d["created_at"] == now.isoformat()
        assert d["is_experienced_at_rating"] == True

    def test_to_dict_not_experienced(self):
        rating = Rating(
            id=1,
            puzzle_id=1,
            user_id=1,
            difficulty=3,
            fun=3,
            clearness=3
        )
        d = rating.to_dict()
        assert d["is_experienced_at_rating"] == False

    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        d = {
            "id": 1,
            "puzzle_id": 1,
            "user_id": 1,
            "difficulty": 4,
            "fun": 5,
            "clearness": 3,
            "created_at": now.isoformat(),
            "is_experienced_at_rating": True
        }
        rating = Rating.from_dict(d)
        assert rating.id == 1
        assert rating.puzzle_id == 1
        assert rating.user_id == 1
        assert rating.difficulty == 4
        assert rating.fun == 5
        assert rating.clearness == 3
        assert rating.is_experienced_at_rating == True

    def test_from_dict_partial(self):
        d = {
            "id": 1,
            "puzzle_id": 1,
            "user_id": 1,
            "difficulty": 2,
            "fun": 3,
            "clearness": 2
        }
        rating = Rating.from_dict(d)
        assert rating.id == 1
        assert rating.difficulty == 2
        assert rating.is_experienced_at_rating == False

    def test_roundtrip(self):
        original = Rating(
            id=1,
            puzzle_id=1,
            user_id=1,
            difficulty=5,
            fun=5,
            clearness=4,
            is_experienced_at_rating=True
        )
        d = original.to_dict()
        restored = Rating.from_dict(d)
        assert restored.id == original.id
        assert restored.puzzle_id == original.puzzle_id
        assert restored.user_id == original.user_id
        assert restored.difficulty == original.difficulty
        assert restored.fun == original.fun
        assert restored.clearness == original.clearness
        assert restored.is_experienced_at_rating == original.is_experienced_at_rating

class TestRatingBranches:
    """Test missing branches in Rating.py"""
    
    def test_clamp_int_below_min(self):
        """Test clamp_int when value < lo"""
        with pytest.raises(ValidationError) as exc_info:
            Rating(id=1, puzzle_id=1, user_id=1, difficulty=0, fun=3, clearness=3)
        assert "difficulty must be in [1, 5]" in str(exc_info.value)
    
    def test_clamp_int_above_max(self):
        """Test clamp_int when value > hi"""
        with pytest.raises(ValidationError) as exc_info:
            Rating(id=1, puzzle_id=1, user_id=1, difficulty=6, fun=3, clearness=3)
        assert "difficulty must be in [1, 5]" in str(exc_info.value)
    
    def test_clamp_int_at_min_boundary(self):
        """Test clamp_int at minimum boundary"""
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=1, fun=1, clearness=1)
        assert rating.difficulty == 1
        assert rating.fun == 1
        assert rating.clearness == 1
    
    def test_clamp_int_at_max_boundary(self):
        """Test clamp_int at maximum boundary"""
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=5, fun=5, clearness=5)
        assert rating.difficulty == 5
        assert rating.fun == 5
        assert rating.clearness == 5
    
    def test_clamp_int_in_middle(self):
        """Test clamp_int with value in middle of range"""
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        assert rating.difficulty == 3
        assert rating.fun == 3
        assert rating.clearness == 3
    
    def test_is_experienced_property(self):
        """Test is_experienced property getter"""
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3, is_experienced_at_rating=True)
        assert rating.is_experienced is True
    
    def test_is_experienced_property_false(self):
        """Test is_experienced property when False"""
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3, is_experienced_at_rating=False)
        assert rating.is_experienced is False


class TestRatingGetters:
    """Test all Rating getter methods"""
    
    def test_get_id(self):
        rating = Rating(id=88, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        assert rating.get_id() == 88
    
    def test_get_puzzle_id(self):
        rating = Rating(id=1, puzzle_id=555, user_id=1, difficulty=3, fun=3, clearness=3)
        assert rating.get_puzzle_id() == 555
    
    def test_get_user_id(self):
        rating = Rating(id=1, puzzle_id=1, user_id=444, difficulty=3, fun=3, clearness=3)
        assert rating.get_user_id() == 444
    
    def test_get_difficulty(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=5, fun=3, clearness=3)
        assert rating.get_difficulty() == 5
    
    def test_get_fun(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=2, clearness=3)
        assert rating.get_fun() == 2
    
    def test_get_clearness(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=4)
        assert rating.get_clearness() == 4
    
    def test_get_created_at(self):
        now = datetime.now(timezone.utc)
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3, created_at=now)
        assert rating.get_created_at() == now
    
    def test_get_is_experienced_at_rating_true(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3, is_experienced_at_rating=True)
        assert rating.get_is_experienced_at_rating() is True
    
    def test_get_is_experienced_at_rating_false(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3, is_experienced_at_rating=False)
        assert rating.get_is_experienced_at_rating() is False


class TestRatingSetters:
    """Comprehensive tests for all Rating setter methods"""

    def test_set_user_id(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        rating.set_user_id(2)
        assert rating.user_id == 2

    def test_set_user_id_empty(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        with pytest.raises(ValidationError):
            rating.set_user_id("")

    def test_set_difficulty_valid(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        rating.set_difficulty(5)
        assert rating.difficulty == 5

    def test_set_difficulty_out_of_range(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        with pytest.raises(ValidationError):
            rating.set_difficulty(10)

    def test_set_fun_valid(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        rating.set_fun(4)
        assert rating.fun == 4

    def test_set_fun_out_of_range(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        with pytest.raises(ValidationError):
            rating.set_fun(-1)

    def test_set_clearness_valid(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        rating.set_clearness(2)
        assert rating.clearness == 2

    def test_set_clearness_out_of_range(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        with pytest.raises(ValidationError):
            rating.set_clearness(6)

    def test_set_is_experienced_at_rating_true(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        rating.set_is_experienced_at_rating(True)
        assert rating.is_experienced_at_rating is True

    def test_set_is_experienced_at_rating_false(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        rating.set_is_experienced_at_rating(False)
        assert rating.is_experienced_at_rating is False

    def test_set_is_experienced_at_rating_invalid(self):
        rating = Rating(id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3)
        with pytest.raises(ValidationError):
            rating.set_is_experienced_at_rating("yes")
