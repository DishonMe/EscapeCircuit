import pytest
from datetime import datetime, timezone, timedelta

from Backend.DomainLayer.SolveAttempt import SolveAttempt
from Backend.DomainLayer.Exceptions import ValidationError


class TestSolveAttemptCreation:
    def test_create_solve_attempt_basic(self):
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1
        )
        assert attempt.id == 1
        assert attempt.puzzle_id == 1
        assert attempt.user_id == 1
        assert attempt.circuit_id is None
        assert attempt.started_at is not None
        assert attempt.submitted_at is None
        assert attempt.passed is None
        assert attempt.fail_reason is None

    def test_create_solve_attempt_with_circuit(self):
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            circuit_id=1
        )
        assert attempt.circuit_id == 1

    def test_create_solve_attempt_zero_id(self):
        # ID=0 is valid (ensure_non_negative_int allows 0)
        attempt = SolveAttempt(id=0, puzzle_id=1, user_id=1)
        assert attempt.id == 0

    def test_create_solve_attempt_missing_puzzle_id(self):
        with pytest.raises(ValidationError) as exc_info:
            SolveAttempt(id=1, puzzle_id=0, user_id=1)
        assert "SolveAttempt.puzzle_id is required" in str(exc_info.value)

    def test_create_solve_attempt_missing_user_id(self):
        with pytest.raises(ValidationError) as exc_info:
            SolveAttempt(id=1, puzzle_id=1, user_id=0)
        assert "SolveAttempt.user_id is required" in str(exc_info.value)


class TestSolveAttemptSubmission:
    def test_mark_submitted_pass(self):
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1
        )
        assert attempt.passed is None
        attempt.mark_submitted(passed=True, circuit_id=1)
        assert attempt.passed is True
        assert attempt.submitted_at is not None
        assert attempt.circuit_id == 1
        assert attempt.fail_reason is None

    def test_mark_submitted_fail_with_reason(self):
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1
        )
        attempt.mark_submitted(passed=False, fail_reason="Budget exceeded")
        assert attempt.passed is False
        assert attempt.fail_reason == "Budget exceeded"

    def test_mark_submitted_fail_without_reason(self):
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1
        )
        attempt.mark_submitted(passed=False)
        assert attempt.passed is False
        assert attempt.fail_reason == "unknown"

    def test_mark_submitted_pass_clears_fail_reason(self):
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1
        )
        attempt.mark_submitted(passed=False, fail_reason="Initial failure")
        attempt.mark_submitted(passed=True, circuit_id=2)
        assert attempt.passed is True
        assert attempt.fail_reason is None

    def test_mark_submitted_updates_circuit(self):
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            circuit_id=1
        )
        attempt.mark_submitted(passed=True, circuit_id=2)
        assert attempt.circuit_id == 2

    def test_mark_submitted_preserves_circuit_if_none(self):
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            circuit_id=1
        )
        attempt.mark_submitted(passed=True)
        assert attempt.circuit_id == 1


class TestSolveAttemptElapsedTime:
    def test_elapsed_seconds_not_submitted(self):
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1
        )
        assert attempt.elapsed_seconds is None

    def test_elapsed_seconds_after_submission(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            started_at=now - timedelta(seconds=30)
        )
        attempt.submitted_at = now
        elapsed = attempt.elapsed_seconds
        assert elapsed is not None
        assert 29 <= elapsed <= 31  # Allow some tolerance

    def test_elapsed_seconds_zero(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            started_at=now
        )
        attempt.submitted_at = now
        assert attempt.elapsed_seconds == 0

    def test_elapsed_seconds_negative_becomes_zero(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            started_at=now
        )
        attempt.submitted_at = now - timedelta(seconds=10)  # Submitted before started
        assert attempt.elapsed_seconds == 0


class TestSolveAttemptAttemptedMinutes:
    def test_attempted_minutes_not_submitted(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            started_at=now - timedelta(minutes=5)
        )
        minutes = attempt.attempted_minutes()
        assert 4.9 <= minutes <= 5.1

    def test_attempted_minutes_submitted(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            started_at=now - timedelta(minutes=10)
        )
        attempt.submitted_at = now
        minutes = attempt.attempted_minutes()
        assert 9.9 <= minutes <= 10.1

    def test_attempted_minutes_zero(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            started_at=now
        )
        attempt.submitted_at = now
        assert attempt.attempted_minutes() >= 0

    def test_attempted_minutes_negative_becomes_zero(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            started_at=now
        )
        attempt.submitted_at = now - timedelta(minutes=5)
        assert attempt.attempted_minutes() >= 0


class TestSolveAttemptSerialization:
    def test_to_dict_not_submitted(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            started_at=now
        )
        d = attempt.to_dict()
        assert d["id"] == 1
        assert d["puzzle_id"] == 1
        assert d["user_id"] == 1
        assert d["circuit_id"] is None
        assert d["started_at"] == now.isoformat()
        assert d["submitted_at"] is None
        assert d["passed"] is None
        assert d["fail_reason"] is None

    def test_to_dict_submitted_pass(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            circuit_id=1,
            started_at=now
        )
        attempt.submitted_at = now
        attempt.passed = True
        d = attempt.to_dict()
        assert d["circuit_id"] == 1
        assert d["passed"] is True
        assert d["fail_reason"] is None

    def test_to_dict_submitted_fail(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            started_at=now
        )
        attempt.submitted_at = now
        attempt.passed = False
        attempt.fail_reason = "Invalid circuit"
        d = attempt.to_dict()
        assert d["passed"] is False
        assert d["fail_reason"] == "Invalid circuit"

    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        d = {
            "id": 1,
            "puzzle_id": 1,
            "user_id": 1,
            "circuit_id": 1,
            "started_at": now.isoformat(),
            "submitted_at": now.isoformat(),
            "passed": True,
            "fail_reason": None
        }
        attempt = SolveAttempt.from_dict(d)
        assert attempt.id == 1
        assert attempt.puzzle_id == 1
        assert attempt.user_id == 1
        assert attempt.circuit_id == 1
        assert attempt.passed is True

    def test_from_dict_partial(self):
        d = {
            "id": 1,
            "puzzle_id": 1,
            "user_id": 1
        }
        attempt = SolveAttempt.from_dict(d)
        assert attempt.id == 1
        assert attempt.puzzle_id == 1
        assert attempt.user_id == 1
        assert attempt.circuit_id is None
        assert attempt.passed is None

    def test_roundtrip(self):
        original = SolveAttempt(
            id=1,
            puzzle_id=1,
            user_id=1,
            circuit_id=1
        )
        original.mark_submitted(passed=True, circuit_id=2)
        d = original.to_dict()
        restored = SolveAttempt.from_dict(d)
        assert restored.id == original.id
        assert restored.puzzle_id == original.puzzle_id
        assert restored.user_id == original.user_id
        assert restored.circuit_id == original.circuit_id
        assert restored.passed == original.passed

class TestSolveAttemptBranches:
    """Test missing branches in SolveAttempt.py"""
    
    def test_elapsed_seconds_none_when_not_submitted(self):
        """Test elapsed_seconds returns None when not submitted"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        assert attempt.submitted_at is None
        assert attempt.elapsed_seconds is None
    
    def test_elapsed_seconds_positive(self):
        """Test elapsed_seconds calculates correctly when submitted"""
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", started_at=now)
        # Set submitted_at to 10 seconds later
        future = datetime.fromtimestamp(now.timestamp() + 10, tz=timezone.utc)
        attempt.submitted_at = future
        assert attempt.elapsed_seconds >= 10
    
    def test_elapsed_seconds_zero(self):
        """Test elapsed_seconds when submitted immediately"""
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", started_at=now)
        attempt.submitted_at = now
        assert attempt.elapsed_seconds == 0
    
    def test_mark_submitted_passed_true(self):
        """Test mark_submitted with passed=True"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.mark_submitted(True, circuit_id="c1", fail_reason="some_reason")
        assert attempt.passed is True
        assert attempt.circuit_id == "c1"
        assert attempt.fail_reason is None  # Should be cleared
        assert attempt.submitted_at is not None
    
    def test_mark_submitted_passed_false(self):
        """Test mark_submitted with passed=False"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.mark_submitted(False, circuit_id="c1", fail_reason="timeout")
        assert attempt.passed is False
        assert attempt.circuit_id == "c1"
        assert attempt.fail_reason == "timeout"
        assert attempt.submitted_at is not None
    
    def test_mark_submitted_passed_false_no_fail_reason(self):
        """Test mark_submitted with passed=False but no fail_reason"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.mark_submitted(False)
        assert attempt.passed is False
        assert attempt.fail_reason == "unknown"  # Default reason
    
    def test_mark_submitted_no_circuit_id(self):
        """Test mark_submitted without circuit_id"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.mark_submitted(True)
        assert attempt.circuit_id is None  # Should remain None
    
    def test_mark_submitted_preserves_circuit_id(self):
        """Test mark_submitted preserves existing circuit_id if None passed"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", circuit_id="c1")
        attempt.mark_submitted(True, circuit_id=None)
        assert attempt.circuit_id == "c1"  # Should preserve
    
    def test_attempted_minutes_zero(self):
        """Test attempted_minutes when submitted immediately"""
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", started_at=now)
        attempt.submitted_at = now
        assert attempt.attempted_minutes() >= 0.0
    
    def test_attempted_minutes_not_submitted(self):
        """Test attempted_minutes when not submitted (uses current time)"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        # Should use utcnow() as end time
        minutes = attempt.attempted_minutes()
        assert minutes >= 0.0
    
    def test_set_passed_bool(self):
        """Test set_passed with boolean value"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.set_passed(True)
        assert attempt.passed is True
    
    def test_set_passed_none(self):
        """Test set_passed with None value"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", passed=True)
        attempt.set_passed(None)
        assert attempt.passed is None
    
    def test_set_passed_invalid_type(self):
        """Test set_passed with invalid type"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        with pytest.raises(ValidationError):
            attempt.set_passed("yes")
    
    def test_set_fail_reason_string(self):
        """Test set_fail_reason with string value"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.set_fail_reason("timeout")
        assert attempt.fail_reason == "timeout"
    
    def test_set_fail_reason_none(self):
        """Test set_fail_reason with None value"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", fail_reason="timeout")
        attempt.set_fail_reason(None)
        assert attempt.fail_reason is None
    
    def test_set_fail_reason_invalid_type(self):
        """Test set_fail_reason with invalid type"""
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        with pytest.raises(ValidationError):
            attempt.set_fail_reason(123)


class TestSolveAttemptGetters:
    """Test all SolveAttempt getter methods"""
    
    def test_get_id(self):
        attempt = SolveAttempt(id=77, puzzle_id="p1", user_id="u1")
        assert attempt.get_id() == 77
    
    def test_get_puzzle_id(self):
        attempt = SolveAttempt(id=1, puzzle_id="puzzle123", user_id="u1")
        assert attempt.get_puzzle_id() == "puzzle123"
    
    def test_get_user_id(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="user456")
        assert attempt.get_user_id() == "user456"
    
    def test_get_circuit_id_none(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", circuit_id=None)
        assert attempt.get_circuit_id() is None
    
    def test_get_circuit_id_value(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", circuit_id="circuit789")
        assert attempt.get_circuit_id() == "circuit789"
    
    def test_get_started_at(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", started_at=now)
        assert attempt.get_started_at() == now
    
    def test_get_submitted_at_none(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", submitted_at=None)
        assert attempt.get_submitted_at() is None
    
    def test_get_submitted_at_value(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", submitted_at=now)
        assert attempt.get_submitted_at() == now
    
    def test_get_passed_none(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", passed=None)
        assert attempt.get_passed() is None
    
    def test_get_passed_true(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", passed=True)
        assert attempt.get_passed() is True
    
    def test_get_passed_false(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", passed=False)
        assert attempt.get_passed() is False
    
    def test_get_fail_reason_none(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", fail_reason=None)
        assert attempt.get_fail_reason() is None
    
    def test_get_fail_reason_value(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", fail_reason="timeout")
        assert attempt.get_fail_reason() == "timeout"


class TestSolveAttemptSetters:
    """Comprehensive tests for all SolveAttempt setter methods"""

    def test_set_puzzle_id(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.set_puzzle_id("p2")
        assert attempt.puzzle_id == "p2"

    def test_set_puzzle_id_empty(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        with pytest.raises(ValidationError):
            attempt.set_puzzle_id("")

    def test_set_user_id(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.set_user_id("u2")
        assert attempt.user_id == "u2"

    def test_set_user_id_empty(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        with pytest.raises(ValidationError):
            attempt.set_user_id("")

    def test_set_circuit_id_valid(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.set_circuit_id("c2")
        assert attempt.circuit_id == "c2"

    def test_set_circuit_id_none(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1", circuit_id="c1")
        attempt.set_circuit_id(None)
        assert attempt.circuit_id is None

    def test_set_circuit_id_empty_string(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        with pytest.raises(ValidationError):
            attempt.set_circuit_id("")

    def test_set_circuit_id_whitespace(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        with pytest.raises(ValidationError):
            attempt.set_circuit_id("   ")

    def test_set_started_at(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        now = datetime.now(timezone.utc)
        attempt.set_started_at(now)
        assert attempt.started_at == now

    def test_set_submitted_at(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        now = datetime.now(timezone.utc)
        attempt.set_submitted_at(now)
        assert attempt.submitted_at == now

    def test_set_passed_true(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.set_passed(True)
        assert attempt.passed is True

    def test_set_passed_false(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.set_passed(False)
        assert attempt.passed is False

    def test_set_passed_none(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.set_passed(None)
        assert attempt.passed is None

    def test_set_passed_invalid(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        with pytest.raises(ValidationError):
            attempt.set_passed("yes")

    def test_set_fail_reason(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.set_fail_reason("Budget exceeded")
        assert attempt.fail_reason == "Budget exceeded"

    def test_set_fail_reason_none(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        attempt.set_fail_reason(None)
        assert attempt.fail_reason is None

    def test_set_fail_reason_invalid(self):
        attempt = SolveAttempt(id=1, puzzle_id="p1", user_id="u1")
        with pytest.raises(ValidationError):
            attempt.set_fail_reason(123)
