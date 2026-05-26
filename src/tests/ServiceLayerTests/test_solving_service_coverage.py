"""Targeted coverage tests for SolvingService — focused on real behavior
branches: permission/ownership, budget enforcement, attempt-id validation,
arsenal-allowed enforcement, duplicate-submission idempotency, failed-solve
recording, gate-limit constraint helpers, and simulate edge cases."""

import json
import sqlite3
from unittest.mock import Mock, MagicMock, patch
from typing import Any, Dict

import pytest

from Backend.ServiceLayer.SolvingService import SolvingService
from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.Enums import PuzzleStatus, PuzzleDifficulty, Medal
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Puzzle import Puzzle
from Backend.DomainLayer.SolveAttempt import SolveAttempt


def _make_service():
    conn = MagicMock()
    solve_repo = MagicMock()
    puzzle_repo = MagicMock()
    circuit_repo = MagicMock()
    auth = MagicMock()
    engine = MagicMock()
    xp = MagicMock()
    user_repo = MagicMock()
    notification = MagicMock()
    clues_repo = MagicMock()
    svc = SolvingService(
        conn,
        solve_repo,
        puzzle_repo,
        circuit_repo,
        auth,
        engine,
        xp,
        user_repo=user_repo,
        notification_service=notification,
        clues_repo=clues_repo,
    )
    return svc, conn, solve_repo, puzzle_repo, circuit_repo, auth, engine, xp, user_repo, notification, clues_repo


def _make_puzzle(**overrides):
    base = dict(
        id=1,
        name="P",
        creator_user_id=2,
        status=PuzzleStatus.PUBLISHED,
        budget=100,
        difficulty=PuzzleDifficulty.EASY,
        time_limit_seconds=None,
        allow_arsenal=True,
        allowed_arsenal_component_ids=[],
    )
    base.update(overrides)
    return Puzzle(**base)


# ---------------------------------------------------------------------------
# start_attempt — clue hydration + race condition
# ---------------------------------------------------------------------------

class TestStartAttemptCoverage:
    def test_reuses_open_attempt(self):
        svc, conn, solve_repo, puzzle_repo, *_ = _make_service()
        svc.auth.require_user_id.return_value = 1
        puzzle_repo.get_by_id.return_value = _make_puzzle()
        existing = SolveAttempt(id=42, puzzle_id=1, user_id=1)
        solve_repo.get_open_attempt.return_value = existing
        svc.clues_repo = None  # No clue hydration

        result = svc.start_attempt("tok", 1)
        # Re-uses existing — no create_attempt call
        solve_repo.create_attempt.assert_not_called()
        assert result["id"] == 42

    def test_hydrates_clue_data(self):
        svc, *_ = _make_service()
        svc.auth.require_user_id.return_value = 1
        puzzle = _make_puzzle()
        puzzle.clues = ["clue A", "clue B", "clue C"]
        svc.puzzle_repo.get_by_id.return_value = puzzle
        attempt = SolveAttempt(id=7, puzzle_id=1, user_id=1)
        svc.solve_repo.get_open_attempt.return_value = attempt
        # 1 valid clue + 1 out-of-range index (should be skipped)
        svc.clues_repo.list_for_attempt.return_value = [
            {"clue_index": 0, "penalty_seconds": 30},
            {"clue_index": 99, "penalty_seconds": 5},
        ]
        result = svc.start_attempt("tok", 1)
        assert len(result["revealed_clues"]) == 1
        assert result["revealed_clues"][0]["text"] == "clue A"
        # Penalty includes both even though only one was rendered
        assert result["total_clue_penalty_seconds"] == 35

    def test_creates_fresh_attempt_when_no_open_attempt_exists(self):
        """With BEGIN IMMEDIATE serialization, concurrent start_attempt calls
        cannot both observe 'no open attempt' — SQLite blocks the second
        until the first commits. So the optimistic-concurrency IntegrityError
        path is no longer reachable; this test verifies the straight-line
        create-when-empty behavior inside the transaction."""
        svc, *_ = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.puzzle_repo.get_by_id.return_value = _make_puzzle()
        svc.solve_repo.get_open_attempt.return_value = None
        fresh = SolveAttempt(id=99, puzzle_id=1, user_id=1)
        svc.solve_repo.create_attempt.return_value = fresh
        svc.clues_repo = None
        result = svc.start_attempt("tok", 1)
        assert result["id"] == 99
        svc.solve_repo.create_attempt.assert_called_once()

    def test_propagates_db_error_from_create_attempt(self):
        """Unexpected DB errors during create_attempt must NOT be swallowed —
        they propagate out so the caller surfaces a real failure instead of a
        misleading fake attempt id."""
        svc, *_ = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.puzzle_repo.get_by_id.return_value = _make_puzzle()
        svc.solve_repo.get_open_attempt.return_value = None
        svc.solve_repo.create_attempt.side_effect = sqlite3.IntegrityError("db down")
        with pytest.raises(sqlite3.IntegrityError):
            svc.start_attempt("tok", 1)

    def test_unpublished_creator_can_start(self):
        svc, *_ = _make_service()
        svc.auth.require_user_id.return_value = 2  # creator id matches
        svc.puzzle_repo.get_by_id.return_value = _make_puzzle(status=PuzzleStatus.DRAFT)
        existing = SolveAttempt(id=1, puzzle_id=1, user_id=2)
        svc.solve_repo.get_open_attempt.return_value = existing
        svc.clues_repo = None
        # Should not raise
        svc.start_attempt("tok", 1)

    def test_unpublished_non_creator_raises(self):
        svc, *_ = _make_service()
        svc.auth.require_user_id.return_value = 99  # not creator
        svc.puzzle_repo.get_by_id.return_value = _make_puzzle(status=PuzzleStatus.DRAFT)
        with pytest.raises(ValidationError, match="not published"):
            svc.start_attempt("tok", 1)


# ---------------------------------------------------------------------------
# submit_solution — budget exceeded, no circuit, fail recording
# ---------------------------------------------------------------------------

class TestSubmitSolutionBudgetAndPerm:
    def setup_method(self):
        (
            self.svc, self.conn, self.solve_repo, self.puzzle_repo,
            self.circuit_repo, self.auth, self.engine, self.xp, *_
        ) = _make_service()
        self.auth.require_user_id.return_value = 1
        self.puzzle = _make_puzzle(budget=10)
        self.puzzle_repo.get_by_id.return_value = self.puzzle
        self.puzzle_repo.list_test_cases.return_value = [Mock()]
        # Default: tests pass; cost test will override
        self.engine.evaluate.return_value = {"Y": 1}
        self.engine.extract_gate_counts.return_value = {}

    def _circuit(self, cost=5):
        c = Circuit(
            id=1, user_id=1, name="c", cost=cost,
            structure_json=json.dumps({"placedComponents": [], "wires": []}),
        )
        return c

    def test_circuit_id_zero_rejected(self):
        with pytest.raises(ValidationError, match="Circuit ID is required"):
            self.svc.submit_solution("tok", 1, 0)

    def test_circuit_id_none_rejected(self):
        with pytest.raises(ValidationError, match="Circuit ID is required"):
            self.svc.submit_solution("tok", 1, {"circuit_id": None})

    def test_circuit_not_found(self):
        self.circuit_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="Circuit not found"):
            self.svc.submit_solution("tok", 1, {"circuit_id": 99})

    def test_circuit_owned_by_other_user(self):
        c = self._circuit(cost=5)
        c.user_id = 999  # owned by someone else
        self.circuit_repo.get_by_id.return_value = c
        with pytest.raises(ValidationError, match="do not have permission"):
            self.svc.submit_solution("tok", 1, {"circuit_id": 1})

    def test_no_test_cases_rejects_submission(self):
        self.circuit_repo.get_by_id.return_value = self._circuit(cost=5)
        self.puzzle_repo.list_test_cases.return_value = []
        with pytest.raises(ValidationError, match="no test cases"):
            self.svc.submit_solution("tok", 1, {"circuit_id": 1})

    def test_budget_exceeded_records_failure(self):
        self.circuit_repo.get_by_id.return_value = self._circuit(cost=999)
        attempt = SolveAttempt(id=1, puzzle_id=1, user_id=1)
        self.solve_repo.get_open_attempt.return_value = attempt
        # _evaluate_test_cases would say "pass" but budget check kicks in inside transaction
        self.svc._evaluate_test_cases = Mock(return_value=(True, None, []))
        result = self.svc.submit_solution("tok", 1, {"circuit_id": 1})
        assert result["passed"] is False
        assert "exceeds puzzle budget" in result["fail_reason"]

    def test_failed_test_cases_records_failure(self):
        self.circuit_repo.get_by_id.return_value = self._circuit(cost=5)
        attempt = SolveAttempt(id=1, puzzle_id=1, user_id=1)
        self.solve_repo.get_open_attempt.return_value = attempt
        self.svc._evaluate_test_cases = Mock(return_value=(False, "wrong", []))
        result = self.svc.submit_solution("tok", 1, {"circuit_id": 1})
        assert result["passed"] is False
        assert result["fail_reason"] == "wrong"

    def test_unpublished_and_non_creator_after_pass_raises(self):
        # Even if test cases passed, an unpublished puzzle blocks non-creator
        # finalisation inside the transaction.
        self.puzzle = _make_puzzle(status=PuzzleStatus.DRAFT, budget=100, creator_user_id=999)
        self.puzzle_repo.get_by_id.return_value = self.puzzle
        self.circuit_repo.get_by_id.return_value = self._circuit(cost=5)
        attempt = SolveAttempt(id=1, puzzle_id=1, user_id=1)
        self.solve_repo.get_open_attempt.return_value = attempt
        self.svc._evaluate_test_cases = Mock(return_value=(True, None, []))
        with pytest.raises(ValidationError, match="not published"):
            self.svc.submit_solution("tok", 1, {"circuit_id": 1})


# ---------------------------------------------------------------------------
# validate_solution — attempt_id ownership/validation branches
# ---------------------------------------------------------------------------

class TestValidateSolutionAttemptId:
    def setup_method(self):
        (self.svc, *_) = _make_service()
        self.svc.auth.require_user_id.return_value = 1
        self.svc.puzzle_repo.get_by_id.return_value = _make_puzzle(allow_arsenal=True)
        self.svc.puzzle_repo.list_test_cases.return_value = [Mock()]
        self.svc._evaluate_test_cases = Mock(return_value=(False, "wrong", []))
        self.svc.clues_repo.total_penalty_for_attempt.return_value = 0
        self.svc.clues_repo.count_for_attempt.return_value = 0

    def test_attempt_not_found(self):
        self.svc.solve_repo.get_attempt_by_id.return_value = None
        with pytest.raises(ValidationError, match="attempt not found"):
            self.svc.validate_solution("tok", 1, {}, attempt_id=42)

    def test_attempt_belongs_to_wrong_user(self):
        bad = SolveAttempt(id=42, puzzle_id=1, user_id=999)
        self.svc.solve_repo.get_attempt_by_id.return_value = bad
        with pytest.raises(ValidationError, match="does not belong"):
            self.svc.validate_solution("tok", 1, {}, attempt_id=42)

    def test_attempt_belongs_to_wrong_puzzle(self):
        bad = SolveAttempt(id=42, puzzle_id=999, user_id=1)
        self.svc.solve_repo.get_attempt_by_id.return_value = bad
        with pytest.raises(ValidationError, match="does not belong"):
            self.svc.validate_solution("tok", 1, {}, attempt_id=42)

    def test_submitted_attempt_recovered_via_open_attempt(self):
        from Backend.DomainLayer.Utils import utcnow
        already_done = SolveAttempt(
            id=42, puzzle_id=1, user_id=1,
            submitted_at=utcnow(),
        )
        self.svc.solve_repo.get_attempt_by_id.return_value = already_done
        existing_open = SolveAttempt(id=7, puzzle_id=1, user_id=1)
        self.svc.solve_repo.get_open_attempt.return_value = existing_open
        # Fail path returns dict
        result = self.svc.validate_solution("tok", 1, {}, attempt_id=42)
        assert result["solved"] is False

    def test_submitted_attempt_no_open_creates_fresh(self):
        from Backend.DomainLayer.Utils import utcnow
        already_done = SolveAttempt(
            id=42, puzzle_id=1, user_id=1,
            submitted_at=utcnow(),
        )
        self.svc.solve_repo.get_attempt_by_id.return_value = already_done
        self.svc.solve_repo.get_open_attempt.return_value = None
        fresh = SolveAttempt(id=100, puzzle_id=1, user_id=1)
        self.svc.solve_repo.create_attempt.return_value = fresh
        result = self.svc.validate_solution("tok", 1, {}, attempt_id=42)
        # Fresh attempt was created — exact count varies since the fail path
        # also records a separate analytics attempt at the end.
        assert self.svc.solve_repo.create_attempt.call_count >= 1
        assert result["solved"] is False


# ---------------------------------------------------------------------------
# validate_solution — arsenal-not-allowed enforcement
# ---------------------------------------------------------------------------

class TestValidateArsenalAllowed:
    def setup_method(self):
        (self.svc, *_) = _make_service()
        self.svc.auth.require_user_id.return_value = 1
        self.svc.puzzle_repo.list_test_cases.return_value = [Mock()]
        self.svc._evaluate_test_cases = Mock(return_value=(False, "wrong", []))
        self.svc.clues_repo.total_penalty_for_attempt.return_value = 0
        self.svc.clues_repo.count_for_attempt.return_value = 0
        self.svc.solve_repo.get_open_attempt.return_value = None

    def test_blocks_personal_arsenal_piece_when_disallowed(self):
        self.svc.puzzle_repo.get_by_id.return_value = _make_puzzle(
            allow_arsenal=False, allowed_arsenal_component_ids=[]
        )
        piece = Mock(puzzle_id=None)  # personal arsenal piece (no puzzle id)
        self.svc.circuit_repo.get_by_id.return_value = piece
        payload = {"placedComponents": [{"componentId": "55"}]}
        with pytest.raises(ValidationError, match="not allowed"):
            self.svc.validate_solution("tok", 1, payload)

    def test_allows_creator_shared_arsenal_piece(self):
        self.svc.puzzle_repo.get_by_id.return_value = _make_puzzle(
            allow_arsenal=False, allowed_arsenal_component_ids=[55],
        )
        payload = {"placedComponents": [{"componentId": "55"}]}
        # Should not raise even though arsenal disallowed
        result = self.svc.validate_solution("tok", 1, payload)
        assert result["solved"] is False

    def test_allows_custom_puzzle_piece(self):
        self.svc.puzzle_repo.get_by_id.return_value = _make_puzzle(
            allow_arsenal=False, allowed_arsenal_component_ids=[],
        )
        # Custom piece — has puzzle_id set
        piece = Mock(puzzle_id=1)
        self.svc.circuit_repo.get_by_id.return_value = piece
        payload = {"placedComponents": [{"componentId": "77"}]}
        result = self.svc.validate_solution("tok", 1, payload)
        assert result["solved"] is False

    def test_skips_non_numeric_component_ids(self):
        # Non-numeric ids are basic gates, never blocked
        self.svc.puzzle_repo.get_by_id.return_value = _make_puzzle(
            allow_arsenal=False, allowed_arsenal_component_ids=[],
        )
        payload = {"placedComponents": [{"componentId": "AND"}]}
        result = self.svc.validate_solution("tok", 1, payload)
        # No exception → branch covered
        assert result["solved"] is False

    def test_invalid_allowed_ids_skipped_gracefully(self):
        self.svc.puzzle_repo.get_by_id.return_value = _make_puzzle(
            allow_arsenal=False, allowed_arsenal_component_ids=["not-int", 42],
        )
        # The "not-int" entry should be skipped, 42 kept.
        payload = {"placedComponents": [{"componentId": "42"}]}
        result = self.svc.validate_solution("tok", 1, payload)
        assert result["solved"] is False

    def test_no_test_cases_rejected(self):
        self.svc.puzzle_repo.get_by_id.return_value = _make_puzzle(allow_arsenal=True)
        self.svc.puzzle_repo.list_test_cases.return_value = []
        with pytest.raises(ValidationError, match="no test cases"):
            self.svc.validate_solution("tok", 1, {})

    def test_validate_puzzle_not_found(self):
        self.svc.puzzle_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="puzzle not found"):
            self.svc.validate_solution("tok", 1, {})


# ---------------------------------------------------------------------------
# _evaluate_gate_limit_constraint — arsenal/custom branches
# ---------------------------------------------------------------------------

class TestEvaluateGateLimit:
    def setup_method(self):
        self.svc, *_ = _make_service()

    def test_standard_failure_min_not_met(self):
        ctx = {"per_gate_counts": {"AND": 1}}
        ok, msg, detail = self.svc._evaluate_gate_limit_constraint("AND", 5, None, ctx)
        assert ok is False
        assert "Insufficient" in msg
        assert detail["error_type"] == "gate_limit_insufficient"

    def test_standard_failure_max_exceeded(self):
        ctx = {"per_gate_counts": {"AND": 10}}
        ok, msg, detail = self.svc._evaluate_gate_limit_constraint("AND", None, 5, ctx)
        assert ok is False
        assert detail["error_type"] == "gate_limit_exceeded"

    def test_standard_within_range(self):
        ctx = {"per_gate_counts": {"AND": 3}}
        ok, msg, detail = self.svc._evaluate_gate_limit_constraint("AND", 1, 5, ctx)
        assert ok is True
        assert msg is None

    def test_arsenal_each_per_piece_min(self):
        ctx = {"private_arsenal_piece_counts": {"55": 1}}
        ok, msg, detail = self.svc._evaluate_gate_limit_constraint(
            self.svc.ARSENAL_EACH_KEY, 3, None, ctx
        )
        assert ok is False
        assert "Insufficient private arsenal" in msg

    def test_arsenal_each_per_piece_max(self):
        ctx = {"private_arsenal_piece_counts": {"55": 10}}
        ok, msg, _ = self.svc._evaluate_gate_limit_constraint(
            self.svc.ARSENAL_EACH_KEY, None, 3, ctx
        )
        assert ok is False
        assert "per-piece limit exceeded" in msg

    def test_arsenal_each_within_range(self):
        ctx = {"private_arsenal_piece_counts": {"55": 2}}
        ok, _, _ = self.svc._evaluate_gate_limit_constraint(
            self.svc.ARSENAL_EACH_KEY, 1, 5, ctx
        )
        assert ok is True

    def test_arsenal_shared_each_per_piece_min(self):
        ctx = {"shared_arsenal_piece_counts": {"55": 1}}
        ok, msg, _ = self.svc._evaluate_gate_limit_constraint(
            self.svc.ARSENAL_SHARED_EACH_KEY, 3, None, ctx
        )
        assert ok is False
        assert "Insufficient shared arsenal" in msg

    def test_arsenal_shared_each_per_piece_max(self):
        ctx = {"shared_arsenal_piece_counts": {"55": 10}}
        ok, msg, _ = self.svc._evaluate_gate_limit_constraint(
            self.svc.ARSENAL_SHARED_EACH_KEY, None, 3, ctx
        )
        assert ok is False
        assert "Shared arsenal per-piece" in msg

    def test_arsenal_shared_within_range(self):
        ctx = {"shared_arsenal_piece_counts": {"55": 2}}
        ok, _, _ = self.svc._evaluate_gate_limit_constraint(
            self.svc.ARSENAL_SHARED_EACH_KEY, 1, 5, ctx
        )
        assert ok is True

    def test_custom_piece_prefix_branch(self):
        ctx = {"custom_piece_counts": {"FullAdder": 1}}
        gate = self.svc.CUSTOM_PIECE_PREFIX + "FullAdder"
        # Need 2 but have 1
        ok, msg, _ = self.svc._evaluate_gate_limit_constraint(gate, 2, None, ctx)
        assert ok is False
        assert "Insufficient" in msg


# ---------------------------------------------------------------------------
# _evaluate_test_cases — gate_count_limit & latency_limit branches
# ---------------------------------------------------------------------------

class TestEvaluateTestCasesConstraints:
    def setup_method(self):
        self.svc, *_ = _make_service()
        self.svc._build_gate_usage_context = Mock(return_value={
            "per_gate_counts": {"AND": 2},
            "total_gate_count": 2,
        })

    def _circuit(self):
        return Circuit(id=0, user_id=0, name="c", cost=0,
                       structure_json=json.dumps({"placedComponents": [], "wires": []}))

    def test_gate_count_limit_insufficient(self):
        tc = Mock(spec_set=["kind", "min_gate_count", "max_gate_count", "input_stream"])
        tc.kind = "gate_count_limit"
        tc.min_gate_count = 5
        tc.max_gate_count = None
        tc.input_stream = None
        ok, msg, _ = self.svc._evaluate_test_cases(self._circuit(), [tc])
        assert ok is False
        assert "minimum is 5" in msg

    def test_gate_count_limit_exceeded(self):
        tc = Mock(spec_set=["kind", "min_gate_count", "max_gate_count", "input_stream"])
        tc.kind = "gate_count_limit"
        tc.min_gate_count = None
        tc.max_gate_count = 1
        tc.input_stream = None
        ok, msg, _ = self.svc._evaluate_test_cases(self._circuit(), [tc])
        assert ok is False
        assert "exceeded" in msg

    def test_global_min_gate_count_from_puzzle(self):
        # No gate_count_limit tc, puzzle has min_gate_count > total
        tc = Mock(spec_set=["kind", "inputs", "expected_outputs", "input_stream",
                            "expected_output_stream"])
        tc.kind = "blackbox"
        tc.inputs = {"A": 0}
        tc.expected_outputs = {"Y": 0}
        tc.input_stream = None
        tc.expected_output_stream = None
        puzzle = Mock(min_gate_count=10, total_gate_count=None,
                      riddle_base_name=None)
        ok, msg, _ = self.svc._evaluate_test_cases(self._circuit(), [tc], puzzle=puzzle)
        assert ok is False
        assert "Insufficient gates" in msg

    def test_global_max_gate_count_from_puzzle(self):
        tc = Mock(spec_set=["kind", "inputs", "expected_outputs", "input_stream",
                            "expected_output_stream"])
        tc.kind = "blackbox"
        tc.inputs = {"A": 0}
        tc.expected_outputs = {"Y": 0}
        tc.input_stream = None
        tc.expected_output_stream = None
        puzzle = Mock(min_gate_count=None, total_gate_count=1, riddle_base_name=None)
        ok, msg, _ = self.svc._evaluate_test_cases(self._circuit(), [tc], puzzle=puzzle)
        assert ok is False
        assert "maximum allowed is 1" in msg


# ---------------------------------------------------------------------------
# simulate_solution — branch on puzzle_id=0 vs >0, plus puzzle not found
# ---------------------------------------------------------------------------

class TestSimulateSolution:
    def setup_method(self):
        self.svc, *_ = _make_service()
        self.svc.auth.require_user_id.return_value = 1
        self.svc.engine.evaluate.return_value = {"out0": 1}
        # Mock arsenal expansion and run_simulation to keep test focused on the
        # routing/permission code in simulate_solution itself.
        self.svc._expand_arsenal_pieces = Mock(side_effect=lambda p: dict(p))
        self.svc._run_simulation = Mock(return_value={"puzzleOutputs": {"Y": 1}})

    def test_puzzle_zero_skips_lookup(self):
        # puzzle_id == 0 → no puzzle_repo.get_by_id call
        self.svc.simulate_solution("tok", 0, {"placedComponents": [], "wires": []}, {"X": 0})
        self.svc.puzzle_repo.get_by_id.assert_not_called()

    def test_puzzle_positive_not_found(self):
        self.svc.puzzle_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="puzzle not found"):
            self.svc.simulate_solution("tok", 1, {}, {"X": 0})

    def test_sequence_uses_sequence_method(self):
        self.svc.puzzle_repo.get_by_id.return_value = _make_puzzle()
        self.svc._simulate_sequence = Mock(return_value={"steps": []})
        result = self.svc.simulate_solution(
            "tok", 1, {"placedComponents": []}, {"X": [0, 1, 0]}, is_sequence=True
        )
        self.svc._simulate_sequence.assert_called_once()

    def test_sequence_empty_input_raises(self):
        self.svc.puzzle_repo.get_by_id.return_value = _make_puzzle()
        with pytest.raises(ValidationError, match="No input sequences"):
            self.svc.simulate_solution("tok", 1, {"placedComponents": []}, {}, is_sequence=True)

    def test_sequence_unequal_lengths_raises(self):
        self.svc.puzzle_repo.get_by_id.return_value = _make_puzzle()
        with pytest.raises(ValidationError, match="same length"):
            self.svc.simulate_solution(
                "tok", 1, {"placedComponents": []},
                {"A": [0, 1], "B": [0, 1, 0]}, is_sequence=True,
            )


# ---------------------------------------------------------------------------
# _expand_arsenal_pieces — id parsing branches
# ---------------------------------------------------------------------------

class TestExpandArsenalPieces:
    def setup_method(self):
        self.svc, *_ = _make_service()

    def test_non_numeric_id_skipped(self):
        result = self.svc._expand_arsenal_pieces({
            "placedComponents": [{"componentId": "AND", "id": "p1"}]
        })
        assert result["_arsenal_pieces"] == {}

    def test_int_id_fetched(self):
        piece = Mock()
        piece.name = "MyPiece"
        piece.is_arsenal = True
        piece.truth_table = json.dumps({"0": {"out0": 1}})
        piece.num_inputs = 1
        piece.num_outputs = 1
        piece.structure_json = json.dumps({"placedComponents": []})
        self.svc.circuit_repo.get_by_id.return_value = piece
        result = self.svc._expand_arsenal_pieces({
            "placedComponents": [{"componentId": 99, "id": "p1"}]
        })
        assert "MyPiece" in result["_arsenal_pieces"]
        assert "p1" in result["_arsenal_pieces"]

    def test_truth_table_invalid_json_falls_back_to_empty(self):
        piece = Mock()
        piece.name = "Bad"
        piece.is_arsenal = True
        piece.truth_table = "{not-json"
        piece.num_inputs = 1
        piece.num_outputs = 1
        piece.structure_json = json.dumps({"placedComponents": []})
        self.svc.circuit_repo.get_by_id.return_value = piece
        result = self.svc._expand_arsenal_pieces({
            "placedComponents": [{"componentId": "99", "id": "p1"}]
        })
        info = result["_arsenal_pieces"].get("Bad")
        assert info is not None
        assert info["truth_table"] == {}

    def test_missing_piece_skipped(self):
        self.svc.circuit_repo.get_by_id.return_value = None
        result = self.svc._expand_arsenal_pieces({
            "placedComponents": [{"componentId": "99", "id": "p1"}]
        })
        assert result["_arsenal_pieces"] == {}

    def test_piece_without_io_skipped(self):
        piece = Mock()
        piece.name = "NoIO"
        piece.is_arsenal = True
        piece.truth_table = ""
        piece.num_inputs = 0  # not > 0
        piece.num_outputs = 0
        piece.structure_json = ""
        self.svc.circuit_repo.get_by_id.return_value = piece
        result = self.svc._expand_arsenal_pieces({
            "placedComponents": [{"componentId": "99", "id": "p1"}]
        })
        assert result["_arsenal_pieces"] == {}

    def test_fetch_error_swallowed(self):
        self.svc.circuit_repo.get_by_id.side_effect = Exception("db")
        # Should not raise
        result = self.svc._expand_arsenal_pieces({
            "placedComponents": [{"componentId": "99", "id": "p1"}]
        })
        assert result["_arsenal_pieces"] == {}


# ---------------------------------------------------------------------------
# _load_structure_dict, _normalize_id_set, _to_optional_int helpers
# ---------------------------------------------------------------------------

class TestPureHelpers:
    def test_load_structure_dict_from_dict(self):
        assert SolvingService._load_structure_dict({"a": 1}) == {"a": 1}

    def test_load_structure_dict_from_json_string(self):
        assert SolvingService._load_structure_dict('{"a": 1}') == {"a": 1}

    def test_load_structure_dict_invalid_returns_empty(self):
        assert SolvingService._load_structure_dict("bad-json") == {}

    def test_load_structure_dict_none(self):
        assert SolvingService._load_structure_dict(None) == {}

    def test_normalize_id_set_from_list(self):
        assert SolvingService._normalize_id_set([1, "2", "bad", 3.5]) == {1, 2, 3}

    def test_normalize_id_set_non_iterable(self):
        assert SolvingService._normalize_id_set(42) == set()
        assert SolvingService._normalize_id_set(None) == set()

    def test_to_optional_int(self):
        assert SolvingService._to_optional_int("5") == 5
        assert SolvingService._to_optional_int(None) is None
        assert SolvingService._to_optional_int("not-a-num") is None

    def test_get_tc_field_dict(self):
        assert SolvingService._get_tc_field({"x": 1}, "x") == 1
        assert SolvingService._get_tc_field({"x": 1}, "missing", default=42) == 42

    def test_get_tc_field_obj(self):
        obj = Mock(spec_set=["x"])
        obj.x = 5
        assert SolvingService._get_tc_field(obj, "x") == 5

    def test_get_tc_kind_with_enum(self):
        kind = Mock()
        kind.value = "blackbox"
        tc = Mock(spec_set=["kind"])
        tc.kind = kind
        assert SolvingService._get_tc_kind(tc) == "blackbox"

    def test_get_tc_kind_none(self):
        tc = Mock(spec_set=["kind"])
        tc.kind = None
        assert SolvingService._get_tc_kind(tc) is None

    def test_get_tc_kind_plain_string(self):
        tc = Mock(spec_set=["kind"])
        tc.kind = "blackbox"
        assert SolvingService._get_tc_kind(tc) == "blackbox"
