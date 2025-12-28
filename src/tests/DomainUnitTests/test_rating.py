import pytest
from datetime import datetime, timezone

from Backend.DomainLayer.Rating import Rating
from Backend.DomainLayer.Exceptions import ValidationError


class TestRatingCreation:
    def test_create_rating_basic(self):
        rating = Rating(
            id="rating1",
            puzzle_id="puzzle1",
            user_id="user1",
            difficulty=3,
            fun=4,
            clearness=3
        )
        assert rating.id == "rating1"
        assert rating.puzzle_id == "puzzle1"
        assert rating.user_id == "user1"
        assert rating.difficulty == 3
        assert rating.fun == 4
        assert rating.clearness == 3
        assert rating.user_level_at_rating is None

    def test_create_rating_with_level(self):
        now = datetime.now(timezone.utc)
        rating = Rating(
            id="rating1",
            puzzle_id="puzzle1",
            user_id="user1",
            difficulty=5,
            fun=5,
            clearness=5,
            created_at=now,
            user_level_at_rating=10
        )
        assert rating.user_level_at_rating == 10

    def test_create_rating_missing_id(self):
        with pytest.raises(ValidationError) as exc_info:
            Rating(id="", puzzle_id="puzzle1", user_id="user1", difficulty=3, fun=3, clearness=3)
        assert "Rating.id is required" in str(exc_info.value)

    def test_create_rating_missing_puzzle_id(self):
        with pytest.raises(ValidationError) as exc_info:
            Rating(id="rating1", puzzle_id="", user_id="user1", difficulty=3, fun=3, clearness=3)
        assert "Rating.puzzle_id is required" in str(exc_info.value)

    def test_create_rating_missing_user_id(self):
        with pytest.raises(ValidationError) as exc_info:
            Rating(id="rating1", puzzle_id="puzzle1", user_id="", difficulty=3, fun=3, clearness=3)
        assert "Rating.user_id is required" in str(exc_info.value)


class TestRatingValidation:
    def test_rating_difficulty_clamped_min(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=0,  # Should clamp to 1
            fun=3,
            clearness=3
        )
        assert rating.difficulty == 1

    def test_rating_difficulty_clamped_max(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=10,  # Should clamp to 5
            fun=3,
            clearness=3
        )
        assert rating.difficulty == 5

    def test_rating_fun_clamped_min(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=3,
            fun=-5,  # Should clamp to 1
            clearness=3
        )
        assert rating.fun == 1

    def test_rating_fun_clamped_max(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=3,
            fun=100,  # Should clamp to 5
            clearness=3
        )
        assert rating.fun == 5

    def test_rating_clearness_clamped_min(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=3,
            fun=3,
            clearness=0  # Should clamp to 1
        )
        assert rating.clearness == 1

    def test_rating_clearness_clamped_max(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=3,
            fun=3,
            clearness=10  # Should clamp to 5
        )
        assert rating.clearness == 5

    def test_rating_all_fields_valid_range(self):
        for val in [1, 2, 3, 4, 5]:
            rating = Rating(
                id="r1",
                puzzle_id="p1",
                user_id="u1",
                difficulty=val,
                fun=val,
                clearness=val
            )
            assert rating.difficulty == val
            assert rating.fun == val
            assert rating.clearness == val


class TestRatingExperienced:
    def test_is_experienced_with_high_level(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=3,
            fun=3,
            clearness=3,
            user_level_at_rating=5
        )
        assert rating.is_experienced

    def test_is_experienced_with_very_high_level(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=3,
            fun=3,
            clearness=3,
            user_level_at_rating=10
        )
        assert rating.is_experienced

    def test_is_experienced_with_low_level(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=3,
            fun=3,
            clearness=3,
            user_level_at_rating=2
        )
        assert not rating.is_experienced

    def test_is_experienced_no_level(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=3,
            fun=3,
            clearness=3
        )
        assert not rating.is_experienced

    def test_is_experienced_level_exactly_5(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=3,
            fun=3,
            clearness=3,
            user_level_at_rating=5
        )
        assert rating.is_experienced


class TestRatingSerialization:
    def test_to_dict(self):
        now = datetime.now(timezone.utc)
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=4,
            fun=5,
            clearness=3,
            created_at=now,
            user_level_at_rating=6
        )
        d = rating.to_dict()
        assert d["id"] == "r1"
        assert d["puzzle_id"] == "p1"
        assert d["user_id"] == "u1"
        assert d["difficulty"] == 4
        assert d["fun"] == 5
        assert d["clearness"] == 3
        assert d["created_at"] == now.isoformat()
        assert d["user_level_at_rating"] == 6

    def test_to_dict_no_level(self):
        rating = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=3,
            fun=3,
            clearness=3
        )
        d = rating.to_dict()
        assert d["user_level_at_rating"] is None

    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        d = {
            "id": "r1",
            "puzzle_id": "p1",
            "user_id": "u1",
            "difficulty": 4,
            "fun": 5,
            "clearness": 3,
            "created_at": now.isoformat(),
            "user_level_at_rating": 7
        }
        rating = Rating.from_dict(d)
        assert rating.id == "r1"
        assert rating.puzzle_id == "p1"
        assert rating.user_id == "u1"
        assert rating.difficulty == 4
        assert rating.fun == 5
        assert rating.clearness == 3
        assert rating.user_level_at_rating == 7

    def test_from_dict_partial(self):
        d = {
            "id": "r1",
            "puzzle_id": "p1",
            "user_id": "u1",
            "difficulty": 2,
            "fun": 3,
            "clearness": 2
        }
        rating = Rating.from_dict(d)
        assert rating.id == "r1"
        assert rating.difficulty == 2
        assert rating.user_level_at_rating is None

    def test_roundtrip(self):
        original = Rating(
            id="r1",
            puzzle_id="p1",
            user_id="u1",
            difficulty=5,
            fun=5,
            clearness=4,
            user_level_at_rating=8
        )
        d = original.to_dict()
        restored = Rating.from_dict(d)
        assert restored.id == original.id
        assert restored.puzzle_id == original.puzzle_id
        assert restored.user_id == original.user_id
        assert restored.difficulty == original.difficulty
        assert restored.fun == original.fun
        assert restored.clearness == original.clearness
        assert restored.user_level_at_rating == original.user_level_at_rating
