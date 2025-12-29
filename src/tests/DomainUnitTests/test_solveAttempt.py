import pytest
from datetime import datetime, timezone, timedelta

from Backend.DomainLayer.SolveAttempt import SolveAttempt
from Backend.DomainLayer.Exceptions import ValidationError


class TestSolveAttemptCreation:
    def test_create_solve_attempt_basic(self):
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1"
        )
        assert attempt.id == "attempt1"
        assert attempt.puzzle_id == "puzzle1"
        assert attempt.user_id == "user1"
        assert attempt.circuit_id is None
        assert attempt.started_at is not None
        assert attempt.submitted_at is None
        assert attempt.passed is None
        assert attempt.fail_reason is None

    def test_create_solve_attempt_with_circuit(self):
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1",
            circuit_id="circuit1"
        )
        assert attempt.circuit_id == "circuit1"

    def test_create_solve_attempt_missing_id(self):
        with pytest.raises(ValidationError) as exc_info:
            SolveAttempt(id="", puzzle_id="puzzle1", user_id="user1")
        assert "SolveAttempt.id is required" in str(exc_info.value)

    def test_create_solve_attempt_missing_puzzle_id(self):
        with pytest.raises(ValidationError) as exc_info:
            SolveAttempt(id="attempt1", puzzle_id="", user_id="user1")
        assert "SolveAttempt.puzzle_id is required" in str(exc_info.value)

    def test_create_solve_attempt_missing_user_id(self):
        with pytest.raises(ValidationError) as exc_info:
            SolveAttempt(id="attempt1", puzzle_id="puzzle1", user_id="")
        assert "SolveAttempt.user_id is required" in str(exc_info.value)


class TestSolveAttemptSubmission:
    def test_mark_submitted_pass(self):
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1"
        )
        assert attempt.passed is None
        attempt.mark_submitted(passed=True, circuit_id="circuit1")
        assert attempt.passed is True
        assert attempt.submitted_at is not None
        assert attempt.circuit_id == "circuit1"
        assert attempt.fail_reason is None

    def test_mark_submitted_fail_with_reason(self):
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1"
        )
        attempt.mark_submitted(passed=False, fail_reason="Budget exceeded")
        assert attempt.passed is False
        assert attempt.fail_reason == "Budget exceeded"

    def test_mark_submitted_fail_without_reason(self):
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1"
        )
        attempt.mark_submitted(passed=False)
        assert attempt.passed is False
        assert attempt.fail_reason == "unknown"

    def test_mark_submitted_pass_clears_fail_reason(self):
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1"
        )
        attempt.mark_submitted(passed=False, fail_reason="Initial failure")
        attempt.mark_submitted(passed=True, circuit_id="circuit2")
        assert attempt.passed is True
        assert attempt.fail_reason is None

    def test_mark_submitted_updates_circuit(self):
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1",
            circuit_id="original"
        )
        attempt.mark_submitted(passed=True, circuit_id="updated")
        assert attempt.circuit_id == "updated"

    def test_mark_submitted_preserves_circuit_if_none(self):
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1",
            circuit_id="existing"
        )
        attempt.mark_submitted(passed=True)
        assert attempt.circuit_id == "existing"


class TestSolveAttemptElapsedTime:
    def test_elapsed_seconds_not_submitted(self):
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1"
        )
        assert attempt.elapsed_seconds is None

    def test_elapsed_seconds_after_submission(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1",
            started_at=now - timedelta(seconds=30)
        )
        attempt.submitted_at = now
        elapsed = attempt.elapsed_seconds
        assert elapsed is not None
        assert 29 <= elapsed <= 31  # Allow some tolerance

    def test_elapsed_seconds_zero(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1",
            started_at=now
        )
        attempt.submitted_at = now
        assert attempt.elapsed_seconds == 0

    def test_elapsed_seconds_negative_becomes_zero(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1",
            started_at=now
        )
        attempt.submitted_at = now - timedelta(seconds=10)  # Submitted before started
        assert attempt.elapsed_seconds == 0


class TestSolveAttemptAttemptedMinutes:
    def test_attempted_minutes_not_submitted(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1",
            started_at=now - timedelta(minutes=5)
        )
        minutes = attempt.attempted_minutes()
        assert 4.9 <= minutes <= 5.1

    def test_attempted_minutes_submitted(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1",
            started_at=now - timedelta(minutes=10)
        )
        attempt.submitted_at = now
        minutes = attempt.attempted_minutes()
        assert 9.9 <= minutes <= 10.1

    def test_attempted_minutes_zero(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1",
            started_at=now
        )
        attempt.submitted_at = now
        assert attempt.attempted_minutes() >= 0

    def test_attempted_minutes_negative_becomes_zero(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id="attempt1",
            puzzle_id="puzzle1",
            user_id="user1",
            started_at=now
        )
        attempt.submitted_at = now - timedelta(minutes=5)
        assert attempt.attempted_minutes() >= 0


class TestSolveAttemptSerialization:
    def test_to_dict_not_submitted(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id="a1",
            puzzle_id="p1",
            user_id="u1",
            started_at=now
        )
        d = attempt.to_dict()
        assert d["id"] == "a1"
        assert d["puzzle_id"] == "p1"
        assert d["user_id"] == "u1"
        assert d["circuit_id"] is None
        assert d["started_at"] == now.isoformat()
        assert d["submitted_at"] is None
        assert d["passed"] is None
        assert d["fail_reason"] is None

    def test_to_dict_submitted_pass(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id="a1",
            puzzle_id="p1",
            user_id="u1",
            circuit_id="c1",
            started_at=now
        )
        attempt.submitted_at = now
        attempt.passed = True
        d = attempt.to_dict()
        assert d["circuit_id"] == "c1"
        assert d["passed"] is True
        assert d["fail_reason"] is None

    def test_to_dict_submitted_fail(self):
        now = datetime.now(timezone.utc)
        attempt = SolveAttempt(
            id="a1",
            puzzle_id="p1",
            user_id="u1",
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
            "id": "a1",
            "puzzle_id": "p1",
            "user_id": "u1",
            "circuit_id": "c1",
            "started_at": now.isoformat(),
            "submitted_at": now.isoformat(),
            "passed": True,
            "fail_reason": None
        }
        attempt = SolveAttempt.from_dict(d)
        assert attempt.id == "a1"
        assert attempt.puzzle_id == "p1"
        assert attempt.user_id == "u1"
        assert attempt.circuit_id == "c1"
        assert attempt.passed is True

    def test_from_dict_partial(self):
        d = {
            "id": "a1",
            "puzzle_id": "p1",
            "user_id": "u1"
        }
        attempt = SolveAttempt.from_dict(d)
        assert attempt.id == "a1"
        assert attempt.puzzle_id == "p1"
        assert attempt.user_id == "u1"
        assert attempt.circuit_id is None
        assert attempt.passed is None

    def test_roundtrip(self):
        original = SolveAttempt(
            id="a1",
            puzzle_id="p1",
            user_id="u1",
            circuit_id="c1"
        )
        original.mark_submitted(passed=True, circuit_id="c2")
        d = original.to_dict()
        restored = SolveAttempt.from_dict(d)
        assert restored.id == original.id
        assert restored.puzzle_id == original.puzzle_id
        assert restored.user_id == original.user_id
        assert restored.circuit_id == original.circuit_id
        assert restored.passed == original.passed
