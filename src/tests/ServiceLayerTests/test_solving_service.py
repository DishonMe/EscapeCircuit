import pytest
import sqlite3
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from Backend.ServiceLayer.SolvingService import SolvingService
from Backend.DomainLayer.SolveAttempt import SolveAttempt
from Backend.DomainLayer.Puzzle import Puzzle
from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.PuzzleTestCase import PuzzleTestCase
from Backend.DomainLayer.Enums import TestCaseKind
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.ServiceLayer.XPService import XPService
import json


class TestSolvingServiceCreation:
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_xp = Mock(spec=XPService)

        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_solving_service_initialization(self):
        assert self.service.conn == self.mock_conn
        assert self.service.solve_repo == self.mock_solve_repo
        assert self.service.puzzle_repo == self.mock_puzzle_repo
        assert self.service.circuit_repo == self.mock_circuit_repo
        assert self.service.auth == self.mock_auth
        assert self.service.engine == self.mock_engine
        assert self.service.xp == self.mock_xp


class TestSolvingServiceStartAttempt:
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_xp = Mock(spec=XPService)

        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_start_attempt_success(self):
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        # The repo returns the attempt with id assigned by DB
        saved_attempt = Mock(spec=SolveAttempt)
        saved_attempt.id = 1
        saved_attempt.puzzle_id = 1
        saved_attempt.user_id = 1
        saved_attempt.to_dict.return_value = {
            "id": 1,
            "puzzle_id": 1,
            "user_id": 1
        }
        self.mock_solve_repo.create_attempt.return_value = saved_attempt

        with patch('Backend.DomainLayer.SolveAttempt.SolveAttempt') as mock_attempt_class:
            mock_attempt_class.return_value = saved_attempt
            result = self.service.start_attempt("valid_token", 1)

        assert result["puzzle_id"] == 1
        assert result["user_id"] == 1
        self.mock_solve_repo.create_attempt.assert_called_once()

    def test_start_attempt_puzzle_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.start_attempt("valid_token", 999)
        assert "puzzle not found" in str(exc_info.value)

    def test_start_attempt_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        with pytest.raises(ValidationError):
            self.service.start_attempt("invalid_token", 1)


class TestSolvingServiceSubmitSolution:
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_xp = Mock(spec=XPService)

        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_submit_solution_success(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, time_limit_seconds=300)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        attempt = SolveAttempt(id=1, puzzle_id=1, user_id=1)
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        self.mock_solve_repo.has_passed_before_attempt.return_value = False
        self.mock_xp.award_solve_xp.return_value = 100

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        assert result["puzzle_id"] == 1
        assert result["passed"] is True

    def test_submit_solution_wrong_output(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        # Wrong output
        self.mock_engine.evaluate.return_value = {"Q": 0}

        attempt = SolveAttempt(id=1, puzzle_id=1, user_id=1)
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        assert result["passed"] is False
        assert result["fail_reason"] == "wrong output"

    def test_submit_solution_circuit_not_found(self):
        self.mock_auth.require_user_id.return_value = 1

        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        self.mock_circuit_repo.get_by_id.return_value = None

        payload = {"circuit_id": 999}

        with pytest.raises(ValidationError) as exc_info:
            self.service.submit_solution("valid_token", 1, payload)
        assert "circuit not found" in str(exc_info.value)

    def test_submit_solution_puzzle_not_found(self):
        self.mock_auth.require_user_id.return_value = 1

        self.mock_puzzle_repo.get_by_id.return_value = None

        payload = {"circuit_id": 1}

        with pytest.raises(ValidationError) as exc_info:
            self.service.submit_solution("valid_token", 999, payload)
        assert "puzzle not found" in str(exc_info.value)

    def test_submit_solution_no_test_cases(self):
        self.mock_auth.require_user_id.return_value = 1

        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        structure_json = json.dumps({"gates": []})
        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        self.mock_puzzle_repo.list_test_cases.return_value = []

        payload = {"circuit_id": 1}

        with pytest.raises(ValidationError) as exc_info:
            self.service.submit_solution("valid_token", 1, payload)
        assert "puzzle has no test cases" in str(exc_info.value)

    def test_submit_solution_forbidden_circuit(self):
        self.mock_auth.require_user_id.return_value = 1

        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        structure_json = json.dumps({"gates": []})
        circuit = Circuit(
            id=1, user_id=2, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        payload = {"circuit_id": 1}

        with pytest.raises(ValidationError) as exc_info:
            self.service.submit_solution("valid_token", 1, payload)
        assert "forbidden" in str(exc_info.value)

    def test_submit_solution_invalid_circuit_id(self):
        self.mock_auth.require_user_id.return_value = 1

        payload = {"circuit_id": 0}

        with pytest.raises(ValidationError) as exc_info:
            self.service.submit_solution("valid_token", 1, payload)
        assert "circuit_id required" in str(exc_info.value)

class TestSolvingServiceCreateAttemptBranches:
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_xp = Mock(spec=XPService)

        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_submit_solution_with_timer_beaten(self):
        """Test submit_solution when user beats the timer"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            time_limit_seconds=60
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        # Create attempt with elapsed time < time_limit
        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = 30
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        self.mock_solve_repo.has_passed_before_attempt.return_value = False
        self.mock_xp.award_solve_xp.return_value = 150

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify timer_beaten=True was passed
        assert self.mock_xp.award_solve_xp.called
        call_kwargs = self.mock_xp.award_solve_xp.call_args[1]
        assert call_kwargs["timer_beaten"] is True

    def test_submit_solution_with_timer_not_beaten(self):
        """Test submit_solution when user does not beat timer"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            time_limit_seconds=60
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        # Create attempt with elapsed time > time_limit
        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = 120
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        self.mock_solve_repo.has_passed_before_attempt.return_value = False
        self.mock_xp.award_solve_xp.return_value = 100

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify timer_beaten=False was passed
        assert self.mock_xp.award_solve_xp.called
        call_kwargs = self.mock_xp.award_solve_xp.call_args[1]
        assert call_kwargs["timer_beaten"] is False

    def test_submit_solution_creates_new_attempt(self):
        """Test submit_solution when no open attempt exists"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        # No open attempt
        self.mock_solve_repo.get_open_attempt.return_value = None

        # Create new attempt
        new_attempt = Mock(spec=SolveAttempt)
        new_attempt.id = 2
        new_attempt.puzzle_id = 1
        new_attempt.user_id = 1
        new_attempt.elapsed_seconds = None
        new_attempt.to_dict.return_value = {
            "id": 2, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.create_attempt.return_value = new_attempt

        self.mock_solve_repo.has_passed_before_attempt.return_value = False
        self.mock_xp.award_solve_xp.return_value = 100

        payload = {"circuit_id": 1}

        with patch('Backend.DomainLayer.SolveAttempt.SolveAttempt') as mock_attempt_class:
            mock_attempt_class.return_value = new_attempt
            result = self.service.submit_solution("valid_token", 1, payload)

        # Verify create_attempt was called
        self.mock_solve_repo.create_attempt.assert_called_once()

    def test_submit_solution_difficulty_hard(self):
        """Test submit_solution categorizes puzzle as hard difficulty"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            avg_difficulty=8.0
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = None
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        self.mock_solve_repo.has_passed_before_attempt.return_value = False
        self.mock_xp.award_solve_xp.return_value = 200

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify tier="hard" was passed
        assert self.mock_xp.award_solve_xp.called
        call_kwargs = self.mock_xp.award_solve_xp.call_args[1]
        assert call_kwargs["difficulty_tier"] == "hard"

    def test_submit_solution_difficulty_medium(self):
        """Test submit_solution categorizes puzzle as medium difficulty"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            avg_difficulty=5.0
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = None
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        self.mock_solve_repo.has_passed_before_attempt.return_value = False
        self.mock_xp.award_solve_xp.return_value = 150

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify tier="medium" was passed
        assert self.mock_xp.award_solve_xp.called
        call_kwargs = self.mock_xp.award_solve_xp.call_args[1]
        assert call_kwargs["difficulty_tier"] == "medium"

    def test_submit_solution_already_solved_before(self):
        """Test submit_solution when user already solved puzzle before"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = None
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        # Already solved before this attempt
        self.mock_solve_repo.has_passed_before_attempt.return_value = True
        self.mock_xp.award_solve_xp.return_value = 50

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify is_first_solve=False was passed
        assert self.mock_xp.award_solve_xp.called
        call_kwargs = self.mock_xp.award_solve_xp.call_args[1]
        assert call_kwargs["is_first_solve"] is False


class TestSolvingServiceEdgeCases:
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_xp = Mock(spec=XPService)

        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_submit_solution_no_time_limit(self):
        """Test submit_solution when puzzle has no time limit"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            time_limit_seconds=None  # No time limit
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = 120
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        self.mock_solve_repo.has_passed_before_attempt.return_value = False
        self.mock_xp.award_solve_xp.return_value = 100

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify timer_beaten=False when no time limit
        call_kwargs = self.mock_xp.award_solve_xp.call_args[1]
        assert call_kwargs["timer_beaten"] is False

    def test_submit_solution_no_elapsed_seconds(self):
        """Test submit_solution when elapsed_seconds is None"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            time_limit_seconds=60
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = None  # No elapsed time
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        self.mock_solve_repo.has_passed_before_attempt.return_value = False
        self.mock_xp.award_solve_xp.return_value = 100

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify timer_beaten=False when elapsed_seconds is None
        call_kwargs = self.mock_xp.award_solve_xp.call_args[1]
        assert call_kwargs["timer_beaten"] is False

    def test_submit_solution_puzzle_difficulty_calc_error(self):
        """Test submit_solution when getting avg_difficulty raises error"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        # Create puzzle with problematic avg_difficulty
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        # Simulate an error when accessing avg_difficulty
        puzzle.avg_difficulty = property(lambda self: 1/0)  # This will raise
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = None
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        self.mock_solve_repo.has_passed_before_attempt.return_value = False
        self.mock_xp.award_solve_xp.return_value = 100

        payload = {"circuit_id": 1}

        # Should default to "easy" tier when error occurs
        result = self.service.submit_solution("valid_token", 1, payload)

        call_kwargs = self.mock_xp.award_solve_xp.call_args[1]
        assert call_kwargs["difficulty_tier"] == "easy"

    def test_submit_solution_difficulty_easy(self):
        """Test submit_solution categorizes puzzle as easy difficulty"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            avg_difficulty=2.0  # Low difficulty
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = None
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        self.mock_solve_repo.has_passed_before_attempt.return_value = False
        self.mock_xp.award_solve_xp.return_value = 50

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify tier="easy" was passed
        call_kwargs = self.mock_xp.award_solve_xp.call_args[1]
        assert call_kwargs["difficulty_tier"] == "easy"

    def test_submit_solution_unauthorized(self):
        """Test submit_solution with unauthorized token"""
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        payload = {"circuit_id": 1}

        with pytest.raises(ValidationError) as exc_info:
            self.service.submit_solution("invalid_token", 1, payload)
        assert "unauthorized" in str(exc_info.value)

    def test_submit_solution_transaction_rollback_on_error(self):
        """Test that transaction rolls back when an error occurs"""
        self.mock_auth.require_user_id.return_value = 1
        
        # Mock connection to track transaction calls
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_circuit_repo.get_by_id.return_value = circuit

        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1},
            expected_outputs={"Q": 1},
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]

        self.mock_engine.evaluate.return_value = {"Q": 1}

        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = None
        self.mock_solve_repo.get_open_attempt.return_value = attempt

        # Make mark_submitted raise an exception to trigger rollback
        attempt.mark_submitted.side_effect = Exception("Test error")

        self.mock_solve_repo.has_passed_before_attempt.return_value = False

        payload = {"circuit_id": 1}

        # Should raise the exception
        with pytest.raises(Exception) as exc_info:
            self.service.submit_solution("valid_token", 1, payload)
        
        # Verify ROLLBACK was called
        assert any("ROLLBACK" in str(call) for call in self.mock_conn.execute.call_args_list)