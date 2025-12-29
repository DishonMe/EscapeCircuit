import pytest
from datetime import datetime, timezone

from Backend.DomainLayer.Puzzle import Puzzle
from Backend.DomainLayer.Enums import PuzzleStatus, GateType
from Backend.DomainLayer.Exceptions import ValidationError


class TestPuzzleCreation:
    def test_create_puzzle_minimal(self):
        puzzle = Puzzle(
            id="puzzle1",
            name="TestPuzzle",
            creator_user_id="user1"
        )
        assert puzzle.id == "puzzle1"
        assert puzzle.name == "TestPuzzle"
        assert puzzle.creator_user_id == "user1"
        assert puzzle.description == ""
        assert puzzle.status == PuzzleStatus.DRAFT
        assert puzzle.budget == 0
        assert puzzle.time_limit_seconds is None

    def test_create_puzzle_full(self):
        now = datetime.now(timezone.utc)
        puzzle = Puzzle(
            id="puzzle1",
            name="ComplexPuzzle",
            creator_user_id="user1",
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
        assert puzzle.id == "puzzle1"
        assert puzzle.name == "ComplexPuzzle"
        assert puzzle.creator_user_id == "user1"
        assert puzzle.description == "A complex puzzle"
        assert puzzle.status == PuzzleStatus.PUBLISHED
        assert puzzle.budget == 100
        assert puzzle.time_limit_seconds == 300
        assert puzzle.rating_count == 5

    def test_create_puzzle_missing_id(self):
        with pytest.raises(ValidationError) as exc_info:
            Puzzle(id="", name="Test", creator_user_id="user1")
        assert "Puzzle.id is required" in str(exc_info.value)

    def test_create_puzzle_missing_name(self):
        with pytest.raises(ValidationError) as exc_info:
            Puzzle(id="puzzle1", name="", creator_user_id="user1")
        assert "Puzzle.name is required" in str(exc_info.value)

    def test_create_puzzle_missing_creator(self):
        with pytest.raises(ValidationError) as exc_info:
            Puzzle(id="puzzle1", name="Test", creator_user_id="")
        assert "Puzzle.creator_user_id is required" in str(exc_info.value)

    def test_create_puzzle_negative_budget(self):
        with pytest.raises(ValidationError) as exc_info:
            Puzzle(id="puzzle1", name="Test", creator_user_id="user1", budget=-10)
        assert "Puzzle.budget cannot be negative" in str(exc_info.value)

    def test_create_puzzle_invalid_time_limit(self):
        with pytest.raises(ValidationError) as exc_info:
            Puzzle(id="puzzle1", name="Test", creator_user_id="user1", time_limit_seconds=0)
        assert "Puzzle.time_limit_seconds must be > 0" in str(exc_info.value)

    def test_create_puzzle_negative_time_limit(self):
        with pytest.raises(ValidationError) as exc_info:
            Puzzle(id="puzzle1", name="Test", creator_user_id="user1", time_limit_seconds=-100)
        assert "Puzzle.time_limit_seconds must be > 0" in str(exc_info.value)


class TestPuzzleBudgetEnforcement:
    def test_enforce_budget_within_limit(self):
        puzzle = Puzzle(id="p1", name="Test", creator_user_id="u1", budget=100)
        puzzle.enforce_budget(50)  # Should not raise
        puzzle.enforce_budget(100)  # Exactly at limit

    def test_enforce_budget_exceeds_limit(self):
        puzzle = Puzzle(id="p1", name="Test", creator_user_id="u1", budget=100)
        with pytest.raises(ValidationError) as exc_info:
            puzzle.enforce_budget(101)
        assert "exceeds puzzle budget" in str(exc_info.value)


class TestPuzzlePublishing:
    def test_publish_draft_puzzle(self):
        puzzle = Puzzle(id="p1", name="Test", creator_user_id="u1")
        assert puzzle.status == PuzzleStatus.DRAFT
        puzzle.publish()
        assert puzzle.status == PuzzleStatus.PUBLISHED

    def test_publish_already_published(self):
        puzzle = Puzzle(
            id="p1",
            name="Test",
            creator_user_id="u1",
            status=PuzzleStatus.PUBLISHED
        )
        puzzle.publish()  # Should remain published
        assert puzzle.status == PuzzleStatus.PUBLISHED

    def test_unpublish_published_puzzle(self):
        puzzle = Puzzle(
            id="p1",
            name="Test",
            creator_user_id="u1",
            status=PuzzleStatus.PUBLISHED
        )
        puzzle.unpublish()
        assert puzzle.status == PuzzleStatus.UNPUBLISHED

    def test_unpublish_draft_puzzle(self):
        puzzle = Puzzle(id="p1", name="Test", creator_user_id="u1")
        puzzle.unpublish()  # Should remain draft
        assert puzzle.status == PuzzleStatus.DRAFT


class TestPuzzleGateSet:
    def test_default_gate_set_empty(self):
        puzzle = Puzzle(id="p1", name="Test", creator_user_id="u1")
        assert puzzle.default_gate_set == set()

    def test_default_gate_set_populated(self):
        gates = {GateType.AND, GateType.OR, GateType.NOT}
        puzzle = Puzzle(
            id="p1",
            name="Test",
            creator_user_id="u1",
            default_gate_set=gates
        )
        assert puzzle.default_gate_set == gates


class TestPuzzleRatings:
    def test_rating_stats_defaults(self):
        puzzle = Puzzle(id="p1", name="Test", creator_user_id="u1")
        assert puzzle.rating_count == 0
        assert puzzle.avg_difficulty == 0.0
        assert puzzle.avg_fun == 0.0
        assert puzzle.avg_clearness == 0.0

    def test_rating_stats_populated(self):
        puzzle = Puzzle(
            id="p1",
            name="Test",
            creator_user_id="u1",
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
            id="p1",
            name="Test",
            creator_user_id="u1",
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
        assert d["id"] == "p1"
        assert d["name"] == "Test"
        assert d["creator_user_id"] == "u1"
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
            "id": "p1",
            "name": "Test",
            "creator_user_id": "u1",
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
        assert puzzle.id == "p1"
        assert puzzle.name == "Test"
        assert puzzle.creator_user_id == "u1"
        assert puzzle.description == "Desc"
        assert puzzle.status == PuzzleStatus.PUBLISHED
        assert puzzle.budget == 100
        assert puzzle.time_limit_seconds == 300

    def test_from_dict_partial(self):
        d = {
            "id": "p1",
            "name": "Test",
            "creator_user_id": "u1",
        }
        puzzle = Puzzle.from_dict(d)
        assert puzzle.id == "p1"
        assert puzzle.name == "Test"
        assert puzzle.description == ""
        assert puzzle.status == PuzzleStatus.DRAFT
        assert puzzle.budget == 0

    def test_roundtrip(self):
        original = Puzzle(
            id="p1",
            name="Complex",
            creator_user_id="u1",
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
