import pytest
from datetime import datetime, timezone

from Backend.DomainLayer.Puzzle import Puzzle
from Backend.DomainLayer.Enums import PuzzleStatus, GateType
from Backend.DomainLayer.Exceptions import ValidationError


class TestPuzzleCreation:
    def test_create_puzzle_minimal(self):
        puzzle = Puzzle(
            id=1,
            name="TestPuzzle",
            creator_user_id=1
        )
        assert puzzle.id == 1
        assert puzzle.name == "TestPuzzle"
        assert puzzle.creator_user_id == 1
        assert puzzle.description == ""
        assert puzzle.status == PuzzleStatus.DRAFT
        assert puzzle.budget == 0
        assert puzzle.time_limit_seconds is None

    def test_create_puzzle_full(self):
        now = datetime.now(timezone.utc)
        puzzle = Puzzle(
            id=1,
            name="ComplexPuzzle",
            creator_user_id=1,
            description="A complex puzzle",
            status=PuzzleStatus.PUBLISHED,
            budget=100,
            time_limit_seconds=300,
            default_gate_set={GateType.AND, GateType.OR},
            rating_count=5,
            avg_difficulty=4.0,
            avg_fun=4.5,
            avg_clearness=3.8,
            created_at=now
        )
        assert puzzle.id == 1
        assert puzzle.name == "ComplexPuzzle"
        assert puzzle.creator_user_id == 1
        assert puzzle.description == "A complex puzzle"
        assert puzzle.status == PuzzleStatus.PUBLISHED
        assert puzzle.budget == 100
        assert puzzle.time_limit_seconds == 300
        assert puzzle.rating_count == 5

    def test_create_puzzle_zero_id(self):
        # ID=0 is valid (ensure_non_negative_int allows 0)
        puzzle = Puzzle(id=0, name="Test", creator_user_id=1)
        assert puzzle.id == 0

    def test_create_puzzle_missing_name(self):
        with pytest.raises(ValidationError) as exc_info:
            Puzzle(id=1, name="", creator_user_id=1)
        assert "Puzzle.name is required" in str(exc_info.value)

    def test_create_puzzle_missing_creator(self):
        with pytest.raises(ValidationError) as exc_info:
            Puzzle(id=1, name="Test", creator_user_id=0)
        assert "Puzzle.creator_user_id is required" in str(exc_info.value)

    def test_create_puzzle_negative_budget(self):
        with pytest.raises(ValidationError) as exc_info:
            Puzzle(id=1, name="Test", creator_user_id=1, budget=-10)
        assert "Puzzle.budget cannot be negative" in str(exc_info.value)

    def test_create_puzzle_invalid_time_limit(self):
        with pytest.raises(ValidationError) as exc_info:
            Puzzle(id=1, name="Test", creator_user_id=1, time_limit_seconds=0)
        assert "Puzzle.time_limit_seconds must be > 0" in str(exc_info.value)

    def test_create_puzzle_negative_time_limit(self):
        with pytest.raises(ValidationError) as exc_info:
            Puzzle(id=1, name="Test", creator_user_id=1, time_limit_seconds=-100)
        assert "Puzzle.time_limit_seconds must be > 0" in str(exc_info.value)


class TestPuzzleBudgetEnforcement:
    def test_enforce_budget_within_limit(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, budget=100)
        puzzle.enforce_budget(50)  # Should not raise
        puzzle.enforce_budget(100)  # Exactly at limit

    def test_enforce_budget_exceeds_limit(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, budget=100)
        with pytest.raises(ValidationError) as exc_info:
            puzzle.enforce_budget(101)
        assert "exceeds puzzle budget" in str(exc_info.value)


class TestPuzzlePublishing:
    def test_publish_draft_puzzle(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1)
        assert puzzle.status == PuzzleStatus.DRAFT
        puzzle.publish()
        assert puzzle.status == PuzzleStatus.PUBLISHED

    def test_publish_already_published(self):
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            status=PuzzleStatus.PUBLISHED
        )
        puzzle.publish()  # Should remain published
        assert puzzle.status == PuzzleStatus.PUBLISHED

    def test_unpublish_published_puzzle(self):
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            status=PuzzleStatus.PUBLISHED
        )
        puzzle.unpublish()
        assert puzzle.status == PuzzleStatus.UNPUBLISHED

    def test_unpublish_draft_puzzle(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1)
        puzzle.unpublish()  # Should remain draft
        assert puzzle.status == PuzzleStatus.DRAFT


class TestPuzzleGateSet:
    def test_default_gate_set_empty(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1)
        assert puzzle.default_gate_set == set()

    def test_default_gate_set_populated(self):
        gates = {GateType.AND, GateType.OR, GateType.NOT}
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            default_gate_set=gates
        )
        assert puzzle.default_gate_set == gates


class TestPuzzleRatings:
    def test_rating_stats_defaults(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1)
        assert puzzle.rating_count == 0
        assert puzzle.avg_difficulty == 0.0
        assert puzzle.avg_fun == 0.0
        assert puzzle.avg_clearness == 0.0

    def test_rating_stats_populated(self):
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            rating_count=10,
            avg_difficulty=4.2,
            avg_fun=4.5,
            avg_clearness=3.8
        )
        assert puzzle.rating_count == 10
        assert puzzle.avg_difficulty == 4.2
        assert puzzle.avg_fun == 4.5
        assert puzzle.avg_clearness == 3.8


class TestPuzzleSerialization:
    def test_to_dict(self):
        now = datetime.now(timezone.utc)
        gates = {GateType.AND, GateType.OR}
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            description="Desc",
            status=PuzzleStatus.PUBLISHED,
            budget=100,
            time_limit_seconds=300,
            default_gate_set=gates,
            rating_count=5,
            avg_difficulty=4.0,
            avg_fun=4.5,
            avg_clearness=3.8,
            created_at=now
        )
        d = puzzle.to_dict()
        assert d["id"] == 1
        assert d["name"] == "Test"
        assert d["creator_user_id"] == 1
        assert d["description"] == "Desc"
        assert d["status"] == "published"
        assert d["budget"] == 100
        assert d["time_limit_seconds"] == 300
        assert d["rating_count"] == 5
        assert d["created_at"] == now.isoformat()
        assert set(d["default_gate_set"]) == {"AND", "OR"}

    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        d = {
            "id": 1,
            "name": "Test",
            "creator_user_id": 1,
            "description": "Desc",
            "status": "published",
            "budget": 100,
            "time_limit_seconds": 300,
            "default_gate_set": ["AND", "OR"],
            "rating_count": 5,
            "avg_difficulty": 4.0,
            "avg_fun": 4.5,
            "avg_clearness": 3.8,
            "created_at": now.isoformat()
        }
        puzzle = Puzzle.from_dict(d)
        assert puzzle.id == 1
        assert puzzle.name == "Test"
        assert puzzle.creator_user_id == 1
        assert puzzle.description == "Desc"
        assert puzzle.status == PuzzleStatus.PUBLISHED
        assert puzzle.budget == 100
        assert puzzle.time_limit_seconds == 300

    def test_from_dict_partial(self):
        d = {
            "id": 1,
            "name": "Test",
            "creator_user_id": 1,
        }
        puzzle = Puzzle.from_dict(d)
        assert puzzle.id == 1
        assert puzzle.name == "Test"
        assert puzzle.description == ""
        assert puzzle.status == PuzzleStatus.DRAFT
        assert puzzle.budget == 0

    def test_roundtrip(self):
        original = Puzzle(
            id=1,
            name="Complex",
            creator_user_id=1,
            description="Detailed description",
            status=PuzzleStatus.PUBLISHED,
            budget=250,
            time_limit_seconds=600,
            default_gate_set={GateType.AND, GateType.OR, GateType.NOT},
            rating_count=15,
            avg_difficulty=4.3,
            avg_fun=4.6,
            avg_clearness=4.1
        )
        d = original.to_dict()
        restored = Puzzle.from_dict(d)
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.creator_user_id == original.creator_user_id
        assert restored.budget == original.budget
        assert restored.status == original.status
        assert restored.rating_count == original.rating_count

class TestPuzzleBranches:
    """Test missing branches in Puzzle.py"""
    
    def test_unpublish_when_not_published(self):
        """Test unpublish on a draft puzzle (status != PUBLISHED)"""
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, status=PuzzleStatus.DRAFT)
        puzzle.unpublish()
        # Should remain DRAFT since condition is False
        assert puzzle.status == PuzzleStatus.DRAFT
    
    def test_unpublish_when_published(self):
        """Test unpublish on a published puzzle (status == PUBLISHED)"""
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, status=PuzzleStatus.PUBLISHED)
        puzzle.unpublish()
        # Should change to UNPUBLISHED
        assert puzzle.status == PuzzleStatus.UNPUBLISHED
    
    def test_enforce_budget_equal_to_limit(self):
        """Test enforce_budget when cost equals budget exactly"""
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, budget=100)
        puzzle.enforce_budget(100)  # Should not raise
    
    def test_enforce_budget_less_than_limit(self):
        """Test enforce_budget when cost is less than budget"""
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, budget=100)
        puzzle.enforce_budget(50)  # Should not raise
    
    def test_enforce_budget_exceeds_limit(self):
        """Test enforce_budget when cost exceeds budget"""
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, budget=100)
        with pytest.raises(ValidationError):
            puzzle.enforce_budget(101)  # Should raise
    
    def test_set_status_valid_type(self):
        """Test set_status with valid PuzzleStatus"""
        puzzle = Puzzle(id=1, name="test", creator_user_id=1)
        puzzle.set_status(PuzzleStatus.PUBLISHED)
        assert puzzle.status == PuzzleStatus.PUBLISHED
    
    def test_set_status_invalid_type(self):
        """Test set_status with invalid type"""
        puzzle = Puzzle(id=1, name="test", creator_user_id=1)
        with pytest.raises(ValidationError):
            puzzle.set_status("PUBLISHED")  # String instead of enum
    
    def test_time_limit_none_is_valid(self):
        """Test that None time_limit_seconds is valid"""
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, time_limit_seconds=None)
        assert puzzle.time_limit_seconds is None
    
    def test_time_limit_positive_is_valid(self):
        """Test that positive time_limit_seconds is valid"""
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, time_limit_seconds=60)
        assert puzzle.time_limit_seconds == 60


class TestPuzzleGetters:
    """Test all Puzzle getter methods"""
    
    def test_get_id(self):
        puzzle = Puzzle(id=99, name="test", creator_user_id=1)
        assert puzzle.get_id() == 99
    
    def test_get_name(self):
        puzzle = Puzzle(id=1, name="Test Puzzle", creator_user_id=1)
        assert puzzle.get_name() == "Test Puzzle"
    
    def test_get_creator_user_id(self):
        puzzle = Puzzle(id=1, name="test", creator_user_id=777)
        assert puzzle.get_creator_user_id() == 777
    
    def test_get_description(self):
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, description="A puzzle")
        assert puzzle.get_description() == "A puzzle"
    
    def test_get_status(self):
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, status=PuzzleStatus.PUBLISHED)
        assert puzzle.get_status() == PuzzleStatus.PUBLISHED
    
    def test_get_budget(self):
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, budget=500)
        assert puzzle.get_budget() == 500
    
    def test_get_time_limit_seconds(self):
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, time_limit_seconds=300)
        assert puzzle.get_time_limit_seconds() == 300
    
    def test_get_time_limit_seconds_none(self):
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, time_limit_seconds=None)
        assert puzzle.get_time_limit_seconds() is None
    
    def test_get_default_gate_set(self):
        gates = {GateType.AND, GateType.OR}
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, default_gate_set=gates)
        assert puzzle.get_default_gate_set() == gates
    
    def test_get_rating_count(self):
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, rating_count=25)
        assert puzzle.get_rating_count() == 25
    
    def test_get_avg_difficulty(self):
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, avg_difficulty=3.7)
        assert puzzle.get_avg_difficulty() == 3.7
    
    def test_get_avg_fun(self):
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, avg_fun=4.2)
        assert puzzle.get_avg_fun() == 4.2
    
    def test_get_avg_clearness(self):
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, avg_clearness=3.5)
        assert puzzle.get_avg_clearness() == 3.5
    
    def test_get_created_at(self):
        now = datetime.now(timezone.utc)
        puzzle = Puzzle(id=1, name="test", creator_user_id=1, created_at=now)
        assert puzzle.get_created_at() == now


class TestPuzzleSetters:
    """Comprehensive tests for all Puzzle setter methods"""

    def test_set_name(self):
        puzzle = Puzzle(id=1, name="Original", creator_user_id="u1")
        puzzle.set_name("NewName")
        assert puzzle.name == "NewName"

    def test_set_name_empty(self):
        puzzle = Puzzle(id=1, name="Original", creator_user_id="u1")
        with pytest.raises(ValidationError):
            puzzle.set_name("")

    def test_set_creator_user_id(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_creator_user_id("u2")
        assert puzzle.creator_user_id == "u2"

    def test_set_creator_user_id_empty(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        with pytest.raises(ValidationError):
            puzzle.set_creator_user_id("")

    def test_set_description(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_description("New description")
        assert puzzle.description == "New description"

    def test_set_description_empty(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_description("")
        assert puzzle.description == ""

    def test_set_status_published(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_status(PuzzleStatus.PUBLISHED)
        assert puzzle.status == PuzzleStatus.PUBLISHED

    def test_set_status_unpublished(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_status(PuzzleStatus.UNPUBLISHED)
        assert puzzle.status == PuzzleStatus.UNPUBLISHED

    def test_set_status_invalid(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        with pytest.raises(ValidationError):
            puzzle.set_status("invalid")

    def test_set_budget(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_budget(250)
        assert puzzle.budget == 250

    def test_set_budget_negative(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        with pytest.raises(ValidationError):
            puzzle.set_budget(-10)

    def test_set_time_limit_seconds(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_time_limit_seconds(300)
        assert puzzle.time_limit_seconds == 300

    def test_set_time_limit_seconds_none(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_time_limit_seconds(None)
        assert puzzle.time_limit_seconds is None

    def test_set_time_limit_seconds_zero(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        with pytest.raises(ValidationError):
            puzzle.set_time_limit_seconds(0)

    def test_set_default_gate_set(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        gates = {GateType.AND, GateType.OR}
        puzzle.set_default_gate_set(gates)
        assert puzzle.default_gate_set == gates

    def test_set_rating_count(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_rating_count(20)
        assert puzzle.rating_count == 20

    def test_set_rating_count_negative(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        with pytest.raises(ValidationError):
            puzzle.set_rating_count(-5)

    def test_set_avg_difficulty(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_avg_difficulty(4.5)
        assert puzzle.avg_difficulty == 4.5

    def test_set_avg_fun(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_avg_fun(3.8)
        assert puzzle.avg_fun == 3.8

    def test_set_avg_clearness(self):
        puzzle = Puzzle(id=1, name="Test", creator_user_id="u1")
        puzzle.set_avg_clearness(4.2)
        assert puzzle.avg_clearness == 4.2
