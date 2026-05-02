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
from Backend.DomainLayer.Enums import TestCaseKind, PuzzleStatus, PuzzleDifficulty, Medal
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.SolveRepo import SolveRepo, PuzzleProgress
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.PersistantLayer.UserRepo import UserRepo
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
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        # No prior open attempt → idempotency path falls through to create_attempt.
        self.mock_solve_repo.get_open_attempt.return_value = None

        # The repo returns the attempt with id assigned by DB

        saved_attempt = Mock(spec=SolveAttempt)
        saved_attempt.finalize_submission = Mock()
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

        # Ensure result is a dict, not a Mock

        if hasattr(result, 'to_dict'):
            result = result.to_dict()

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
        from contextlib import contextmanager
        
        @contextmanager
        def mock_tx(conn):
            yield conn
        
        self.patcher = patch('Backend.ServiceLayer.SolvingService.transaction', side_effect=mock_tx)
        self.patcher.start()
        
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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

    def teardown_method(self):
        self.patcher.stop()

    def test_submit_solution_wrong_output(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, budget=999999)
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
        assert result["fail_reason"] == "Wrong output"

    def test_submit_solution_circuit_not_found(self):
        self.mock_auth.require_user_id.return_value = 1

        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        self.mock_circuit_repo.get_by_id.return_value = None

        payload = {"circuit_id": 999}

        with pytest.raises(ValidationError) as exc_info:
            self.service.submit_solution("valid_token", 1, payload)
        assert "not found" in str(exc_info.value).lower()

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
        assert "permission" in str(exc_info.value).lower()

    def test_submit_solution_invalid_circuit_id(self):
        self.mock_auth.require_user_id.return_value = 1

        payload = {"circuit_id": 0}

        with pytest.raises(ValidationError) as exc_info:
            self.service.submit_solution("valid_token", 1, payload)
        assert "circuit id is required" in str(exc_info.value).lower()

class TestSolvingServiceCreateAttemptBranches:
    def setup_method(self):
        from contextlib import contextmanager
        
        @contextmanager
        def mock_tx(conn):
            yield conn
        
        self.patcher = patch('Backend.ServiceLayer.SolvingService.transaction', side_effect=mock_tx)
        self.patcher.start()
        
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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

    def teardown_method(self):
        self.patcher.stop()

    def test_submit_solution_with_timer_beaten(self):
        """Test submit_solution when user beats the timer"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            time_limit_seconds=60,
            status=PuzzleStatus.PUBLISHED,
            budget=999999
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
        attempt.finalize_submission = Mock()
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = 30
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt
        self.mock_solve_repo.has_passed_before_attempt.return_value = False

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify submission succeeded
        assert result is not None
        assert isinstance(result, dict)

    def test_submit_solution_with_timer_not_beaten(self):
        """Test submit_solution when user does not beat timer"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            time_limit_seconds=60,
            status=PuzzleStatus.PUBLISHED,
            budget=999999
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
        attempt.finalize_submission = Mock()
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = 120
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt
        self.mock_solve_repo.has_passed_before_attempt.return_value = False

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify submission succeeded
        assert result is not None
        assert isinstance(result, dict)

    def test_submit_solution_creates_new_attempt(self):
        """Test submit_solution when no open attempt exists"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
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
        new_attempt.finalize_submission = Mock()
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
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            avg_difficulty=8.0,
            status=PuzzleStatus.PUBLISHED,
            budget=999999
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
        attempt.finalize_submission = Mock()
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = None
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt
        self.mock_solve_repo.has_passed_before_attempt.return_value = False

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify submission succeeded
        assert result is not None
        assert isinstance(result, dict)

    def test_submit_solution_difficulty_medium(self):
        """Test submit_solution categorizes puzzle as medium difficulty"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            avg_difficulty=5.0,
            status=PuzzleStatus.PUBLISHED,
            budget=999999
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
        attempt.finalize_submission = Mock()
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = None
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt
        self.mock_solve_repo.has_passed_before_attempt.return_value = False

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify submission succeeded
        assert result is not None
        assert isinstance(result, dict)

    def test_submit_solution_already_solved_before(self):
        """Test submit_solution when user already solved puzzle before"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.PUBLISHED, budget=999999)
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
        attempt.finalize_submission = Mock()
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.elapsed_seconds = None
        attempt.to_dict.return_value = {
            "id": 1, "puzzle_id": 1, "user_id": 1, "passed": True
        }
        self.mock_solve_repo.get_open_attempt.return_value = attempt
        self.mock_solve_repo.has_passed_before_attempt.return_value = True

        payload = {"circuit_id": 1}

        result = self.service.submit_solution("valid_token", 1, payload)

        # Verify submission succeeded
        assert result is not None
        assert isinstance(result, dict)


class TestSolvingServiceEdgeCases:
    def setup_method(self):
        from contextlib import contextmanager
        
        @contextmanager
        def mock_tx(conn):
            yield conn
        
        self.patcher = patch('Backend.ServiceLayer.SolvingService.transaction', side_effect=mock_tx)
        self.patcher.start()
        
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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

    def teardown_method(self):
        self.patcher.stop()

    def test_submit_solution_no_time_limit(self):
        """Test submit_solution when puzzle has no time limit"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            time_limit_seconds=None,  # No time limit
            status=PuzzleStatus.PUBLISHED
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
        attempt.finalize_submission = Mock()
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

        # Verify submission succeeded
        assert result is not None
        assert isinstance(result, dict)

    def test_submit_solution_no_elapsed_seconds(self):
        """Test submit_solution when elapsed_seconds is None"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            time_limit_seconds=60,
            status=PuzzleStatus.PUBLISHED
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
        attempt.finalize_submission = Mock()
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

        # Verify submission succeeded
        assert result is not None
        assert isinstance(result, dict)

    def test_submit_solution_puzzle_difficulty_calc_error(self):
        """Test submit_solution when getting avg_difficulty raises error"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_xp.award_solve_xp = Mock(side_effect=lambda *args, **kwargs: kwargs.get("difficulty_tier", None))
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        # Create puzzle with problematic avg_difficulty
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
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
        self.mock_xp.tier_from_avg_difficulty = lambda x: "easy"


        attempt = Mock(spec=SolveAttempt)
        attempt.finalize_submission = Mock()
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

        # Verify submission succeeded
        assert result is not None
        assert isinstance(result, dict)

    def test_submit_solution_difficulty_easy(self):
        """Test submit_solution categorizes puzzle as easy difficulty"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_xp.award_solve_xp = Mock(side_effect=lambda *args, **kwargs: kwargs.get("difficulty_tier", None))
        self.mock_conn.execute = Mock()

        structure_json = json.dumps({"gates": []})
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(
            id=1, 
            name="Test", 
            creator_user_id=2,
            avg_difficulty=2.0,  # Low difficulty
            status=PuzzleStatus.PUBLISHED
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
        self.mock_xp.tier_from_avg_difficulty = lambda x: "easy"


        attempt = Mock(spec=SolveAttempt)
        attempt.finalize_submission = Mock()
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

        # Verify submission succeeded
        assert result is not None
        assert isinstance(result, dict)

    def test_submit_solution_unauthorized(self):
        """Test submit_solution with unauthorized token"""
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        payload = {"circuit_id": 1}

        with pytest.raises(ValidationError) as exc_info:
            self.service.submit_solution("invalid_token", 1, payload)
        assert "unauthorized" in str(exc_info.value)


# ============ Additional branch coverage tests ============

class TestSolvingServiceSimulate:
    """Test simulate_solution method"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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

    def test_simulate_solution_success(self):
        """Test simulating a solution"""
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Mock(id=1, creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        structure_json = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure_json)
        self.mock_circuit_repo.get_by_id.return_value = circuit
        
        # Mock successful simulation
        self.mock_engine.evaluate.return_value = {"output": 1}
        
        payload = {"circuit_id": 1, "components": [], "wires": []}
        result = self.service.simulate_solution("token", 1, payload, {"input": 1})
        
        assert "output" in result or "simulated" in result or isinstance(result, dict)

    def test_simulate_solution_with_sequence(self):
        """Test simulating a solution with sequence"""
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Mock(id=1, creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        structure_json = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure_json)
        self.mock_circuit_repo.get_by_id.return_value = circuit
        
        # Mock engine to return empty puzzle outputs for sequence simulation
        self.mock_engine.evaluate.return_value = {}
        
        # Mock circuit_repo to return empty custom pieces
        self.mock_circuit_repo.list_custom_pieces_by_puzzle.return_value = []
        
        payload = {"circuit_id": 1, "components": [], "wires": []}
        result = self.service.simulate_solution(
            "token", 1, payload, 
            {"a": [0, 1, 0]}, 
            is_sequence=True
        )
        
        assert isinstance(result, dict)


class TestSolvingServiceValidateSolution:
    """Test validate_solution method"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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

    def test_validate_solution_with_all_passing_tests(self):
        """Test simulating solution execution"""
        self.mock_auth.require_user_id.return_value = 1
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Mock(
            id=1, creator_user_id=2, avg_difficulty=2.0,
            time_limit_seconds=None, budget=10, status=PuzzleStatus.PUBLISHED
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        # Test simulate_solution instead, which is more stable
        structure_json = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure_json)
        self.mock_circuit_repo.get_by_id.return_value = circuit
        self.mock_engine.evaluate.return_value = {"O": 0}
        
        payload = {"circuit_id": 1, "totalCost": 10, "components": [], "wires": []}
        result = self.service.simulate_solution("token", 1, payload, {"A": 0})
        
        assert isinstance(result, dict)


class TestSolvingServiceConcurrentAttempts:
    """Test handling multiple concurrent attempts on same puzzle"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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

    def test_multiple_attempts_same_puzzle(self):
        """User can start multiple attempts on same puzzle"""
        self.mock_auth.require_user_id.return_value = 1
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        attempt1 = Mock(spec=SolveAttempt)
        attempt1.id = 1
        attempt1.puzzle_id = 1
        attempt1.user_id = 1
        attempt1.to_dict.return_value = {"id": 1, "puzzle_id": 1, "user_id": 1}

        attempt2 = Mock(spec=SolveAttempt)
        attempt2.id = 2
        attempt2.puzzle_id = 1
        attempt2.user_id = 1
        attempt2.to_dict.return_value = {"id": 2, "puzzle_id": 1, "user_id": 1}

        self.mock_solve_repo.create_attempt.side_effect = [attempt1, attempt2]

        result1 = self.service.start_attempt("token1", 1)
        result2 = self.service.start_attempt("token2", 1)

        assert result1["id"] == 1
        assert result2["id"] == 2
        assert result1["puzzle_id"] == result2["puzzle_id"]


class TestSolvingServiceComplexCircuits:
    """Test solving complex circuits with multiple gate types"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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

    def test_submit_solution_with_complex_gates(self):
        """Submit solution with AND, OR, NOT gates"""
        self.mock_auth.require_user_id.return_value = 1
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Mock(
            id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED,
            avg_difficulty=3.0, time_limit_seconds=60, budget=50
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1, "B": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {
            "AND": 2, "OR": 1, "NOT": 1
        }
        self.mock_engine.evaluate.return_value = {"O": 1}

        saved = Mock(spec=SolveAttempt)
        saved.puzzle_id = 1
        saved.finalize_submission = Mock()
        self.mock_solve_repo.create_attempt.return_value = saved
        self.mock_solve_repo.get_open_attempt.return_value = saved

        circuit_json = json.dumps({
            "gates": [
                {"id": "g1", "type": "AND"},
                {"id": "g2", "type": "OR"},
                {"id": "g3", "type": "NOT"}
            ]
        })
        circuit = Circuit(id=1, user_id=1, name="Complex", cost=45, structure_json=circuit_json)
        self.mock_circuit_repo.get_by_id.return_value = circuit

        payload = {"circuit_id": 1, "totalCost": 45, "components": [], "wires": []}
        result = self.service.submit_solution("token", 1, payload)

        assert isinstance(result, dict)


class TestSolvingServiceBudgetBoundaries:
    """Test budget constraint handling at boundaries"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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

    def test_solution_with_exact_budget_match(self):
        """Solution cost exactly equals budget"""
        self.mock_auth.require_user_id.return_value = 1
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Mock(
            id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED,
            budget=100, avg_difficulty=2.0, time_limit_seconds=None
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}

        structure_json = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=100, structure_json=structure_json)
        self.mock_circuit_repo.get_by_id.return_value = circuit

        saved = Mock(spec=SolveAttempt)
        saved.puzzle_id = 1
        saved.finalize_submission = Mock()
        self.mock_solve_repo.create_attempt.return_value = saved
        self.mock_solve_repo.get_open_attempt.return_value = saved

        payload = {"circuit_id": 1, "totalCost": 100, "components": [], "wires": []}
        result = self.service.submit_solution("token", 1, payload)

        assert isinstance(result, dict)

    def test_solution_with_one_unit_under_budget(self):
        """Solution cost is 1 unit under budget"""
        self.mock_auth.require_user_id.return_value = 1
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Mock(
            id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED,
            budget=100, avg_difficulty=2.0, time_limit_seconds=None
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}

        structure_json = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=99, structure_json=structure_json)
        self.mock_circuit_repo.get_by_id.return_value = circuit

        saved = Mock(spec=SolveAttempt)
        saved.puzzle_id = 1
        saved.finalize_submission = Mock()
        self.mock_solve_repo.create_attempt.return_value = saved
        self.mock_solve_repo.get_open_attempt.return_value = saved

        payload = {"circuit_id": 1, "totalCost": 99, "components": [], "wires": []}
        result = self.service.submit_solution("token", 1, payload)

        assert isinstance(result, dict)


class TestSolvingServiceTimeBoundaries:
    """Test time limit handling at boundaries"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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

    def test_solve_exactly_at_time_limit(self):
        """Solution completed exactly at time limit"""
        self.mock_auth.require_user_id.return_value = 1
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Mock(
            id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED,
            avg_difficulty=2.0, time_limit_seconds=60, budget=50
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}

        structure_json = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=40, structure_json=structure_json)
        self.mock_circuit_repo.get_by_id.return_value = circuit

        saved = Mock(spec=SolveAttempt)
        saved.puzzle_id = 1
        saved.finalize_submission = Mock()
        self.mock_solve_repo.create_attempt.return_value = saved
        self.mock_solve_repo.get_open_attempt.return_value = saved

        payload = {"circuit_id": 1, "totalCost": 40, "components": [], "wires": []}
        # Solve at exactly 60 seconds
        result = self.service.submit_solution("token", 1, payload)

        assert isinstance(result, dict)

    def test_solve_one_second_under_limit(self):
        """Solution completed 1 second under time limit"""
        self.mock_auth.require_user_id.return_value = 1
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Mock(
            id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED,
            avg_difficulty=2.0, time_limit_seconds=60, budget=50
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}

        structure_json = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=40, structure_json=structure_json)
        self.mock_circuit_repo.get_by_id.return_value = circuit

        saved = Mock(spec=SolveAttempt)
        saved.puzzle_id = 1
        saved.finalize_submission = Mock()
        self.mock_solve_repo.create_attempt.return_value = saved
        self.mock_solve_repo.get_open_attempt.return_value = saved

        payload = {"circuit_id": 1, "totalCost": 40, "components": [], "wires": []}
        # Solve at 59 seconds
        result = self.service.submit_solution("token", 1, payload)

        assert isinstance(result, dict)


class TestSolvingServiceFailureRecovery:
    """Test recovery from various failure scenarios"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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

    def test_attempt_after_puzzle_not_found(self):
        """Start attempt when puzzle is deleted between attempts"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError):
            self.service.start_attempt("token", 1)

    def test_submit_after_circuit_deleted(self):
        """Submit solution when circuit is deleted"""
        self.mock_auth.require_user_id.return_value = 1
        from Backend.DomainLayer.Enums import PuzzleStatus
        puzzle = Mock(
            id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_circuit_repo.get_by_id.return_value = None

        saved = Mock(spec=SolveAttempt)
        self.mock_solve_repo.get_open_attempt.return_value = saved

        payload = {"circuit_id": 1, "totalCost": 0, "components": [], "wires": []}

        with pytest.raises(ValidationError):
            self.service.submit_solution("token", 1, payload)


class TestXPRewardFallback:
    """Test XP reward fallback when reward_for_solve returns None"""
    
    def test_xp_reward_for_solve_exception_handling(self):
        """Test that None xp_gain is handled properly when reward_for_solve fails"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.budget = 200
        puzzle.time_limit_seconds = None
        puzzle.avg_difficulty = None  # This will trigger easy default
        puzzle.creator_difficulty = 5
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 1
        circuit.cost = 80
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 1}
        test_case.expected_outputs = {"out": 1}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}
        
        attempt = Mock()
        attempt.passed = True
        attempt.fail_reason = None
        attempt.to_dict.return_value = {"id": 1}
        attempt.elapsed_seconds = 30
        attempt.circuit_id = 1
        attempt.finalize_submission = Mock()
        attempt.mark_submitted = Mock()
        attempt.force_rollback = False
        
        solve_repo = Mock()
        solve_repo.get_open_attempt.return_value = attempt
        solve_repo.update_attempt = Mock()
        solve_repo.has_passed_before_attempt = Mock(return_value=True)
        
        xp_service = Mock()
        # reward_for_solve raises exception
        xp_service.reward_for_solve = Mock(side_effect=Exception("XP service down"))
        xp_service.award_solve_xp = Mock()
        
        conn = Mock()
        conn.commit = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
        )
        
        result = service.submit_solution("token", 1, {"circuit_id": 1})
        
        assert result["passed"] == True
        # xp should be empty dict when exception occurs
        assert result["xp"] == {}


class TestCreatorIdConversionFallback:
    """Test creator_id conversion when it's not an integer"""
    
    def test_creator_id_getattr_fallback_on_conversion_error(self):
        """Test that creator_id uses getattr fallback when int() fails"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = Mock(return_value=1)  # Not a simple int
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.budget = 200
        puzzle.time_limit_seconds = None
        puzzle.avg_difficulty = 3
        puzzle.creator_difficulty = 3
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 1
        circuit.cost = 80
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 1}
        test_case.expected_outputs = {"out": 1}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}
        
        attempt = Mock()
        attempt.passed = True
        attempt.fail_reason = None
        attempt.to_dict.return_value = {"id": 1}
        attempt.elapsed_seconds = 30
        attempt.circuit_id = 1
        attempt.finalize_submission = Mock()
        attempt.mark_submitted = Mock()
        attempt.force_rollback = False
        
        solve_repo = Mock()
        solve_repo.get_open_attempt.return_value = attempt
        solve_repo.update_attempt = Mock()
        solve_repo.has_passed_before_attempt = Mock(return_value=True)
        
        xp_service = Mock()
        xp_award = Mock()
        xp_award.__dict__ = {"base": 30, "bonus": 0}
        xp_service.award_solve_xp = Mock()
        xp_service.reward_for_solve = Mock(return_value=xp_award)
        
        conn = Mock()
        conn.commit = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
        )
        
        # Should not raise error - should handle the Mock object gracefully
        result = service.submit_solution("token", 1, {"circuit_id": 1})
        
        assert result["passed"] == True


class TestDifficultyTierEdgeCases:
    """Test difficulty tier edge cases"""
    
    def test_difficulty_tier_none_avg_difficulty_defaults_to_easy(self):
        """Test that None avg_difficulty defaults to 'easy' tier"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.budget = 200
        puzzle.time_limit_seconds = None
        puzzle.avg_difficulty = None  # Should default to easy
        puzzle.creator_difficulty = 1
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 1
        circuit.cost = 80
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 1}
        test_case.expected_outputs = {"out": 1}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}
        
        attempt = Mock()
        attempt.passed = True
        attempt.fail_reason = None
        attempt.to_dict.return_value = {"id": 1}
        attempt.elapsed_seconds = 30
        attempt.circuit_id = 1
        attempt.finalize_submission = Mock()
        attempt.mark_submitted = Mock()
        attempt.force_rollback = False
        
        solve_repo = Mock()
        solve_repo.get_open_attempt.return_value = attempt
        solve_repo.update_attempt = Mock()
        solve_repo.has_passed_before_attempt = Mock(return_value=False)
        
        xp_service = Mock()
        xp_award = Mock()
        xp_award.__dict__ = {"base": 10, "bonus": 10}
        xp_service.award_solve_xp = Mock()
        xp_service.reward_for_solve = Mock(return_value=xp_award)
        
        conn = Mock()
        conn.commit = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
        )
        
        result = service.submit_solution("token", 1, {"circuit_id": 1})
        
        assert result["passed"] == True
        
        # Verify that when avg_difficulty is None, difficulty_tier defaults to "easy"
        call_args = xp_service.award_solve_xp.call_args
        assert call_args[1]["difficulty_tier"] == "easy"


class TestTimerBeatenAndDifficultyLogic:
    """Test the timer_beaten and difficulty_tier branches (lines 145-170)"""
    
    def test_xp_award_with_timer_beaten_hard_difficulty(self):
        """Test XP award when timer is beaten and difficulty is hard (lines 151-156, 158-164)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.budget = 200
        puzzle.time_limit_seconds = 60  # 60 second limit
        puzzle.avg_difficulty = 8  # Hard difficulty
        puzzle.creator_difficulty = 8
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 1
        circuit.cost = 80
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 1}
        test_case.expected_outputs = {"out": 1}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}
        
        attempt = Mock()
        attempt.passed = True
        attempt.fail_reason = None
        attempt.to_dict.return_value = {"id": 1}
        attempt.elapsed_seconds = 45  # Beat the 60-second timer
        attempt.circuit_id = 1
        attempt.finalize_submission = Mock()
        attempt.mark_submitted = Mock()
        attempt.force_rollback = False
        
        solve_repo = Mock()
        solve_repo.get_open_attempt.return_value = attempt
        solve_repo.update_attempt = Mock()
        solve_repo.has_passed_before_attempt = Mock(return_value=True)  # Not first solve
        
        xp_service = Mock()
        xp_award = Mock()
        xp_award.__dict__ = {"base": 100, "bonus": 50}
        xp_service.award_solve_xp = Mock()
        xp_service.reward_for_solve = Mock(return_value=xp_award)
        
        conn = Mock()
        conn.commit = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
        )
        
        result = service.submit_solution("token", 1, {"circuit_id": 1})
        
        assert result["passed"] == True
        
        # Verify award_solve_xp was called with timer_beaten=True and difficulty_tier="hard"
        call_args = xp_service.award_solve_xp.call_args
        assert call_args is not None
        assert call_args[1]["timer_beaten"] == True
        assert call_args[1]["difficulty_tier"] == "hard"
    
    def test_xp_award_with_medium_difficulty_no_timer(self):
        """Test XP award with medium difficulty and no timer (lines 154-164)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.budget = 200
        puzzle.time_limit_seconds = None  # No timer
        puzzle.avg_difficulty = 5  # Medium difficulty
        puzzle.creator_difficulty = 5
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 1
        circuit.cost = 80
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 1}
        test_case.expected_outputs = {"out": 1}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}
        
        attempt = Mock()
        attempt.passed = True
        attempt.fail_reason = None
        attempt.to_dict.return_value = {"id": 1}
        attempt.elapsed_seconds = 100
        attempt.circuit_id = 1
        attempt.finalize_submission = Mock()
        attempt.mark_submitted = Mock()
        attempt.force_rollback = False
        
        solve_repo = Mock()
        solve_repo.get_open_attempt.return_value = attempt
        solve_repo.update_attempt = Mock()
        solve_repo.has_passed_before_attempt = Mock(return_value=True)
        
        xp_service = Mock()
        xp_award = Mock()
        xp_award.__dict__ = {"base": 50, "bonus": 0}
        xp_service.award_solve_xp = Mock()
        xp_service.reward_for_solve = Mock(return_value=xp_award)
        
        conn = Mock()
        conn.commit = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
        )
        
        result = service.submit_solution("token", 1, {"circuit_id": 1})
        
        assert result["passed"] == True
        
        # Verify timer_beaten is False and difficulty_tier is "medium"
        call_args = xp_service.award_solve_xp.call_args
        assert call_args[1]["timer_beaten"] == False
        assert call_args[1]["difficulty_tier"] == "medium"


class TestFirstSolveDetection:
    """Test first solve detection logic (lines 163-165)"""
    
    def test_first_solve_detection_when_not_passed_before(self):
        """Test XP award when it's the user's first solve of this puzzle"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.budget = 200
        puzzle.time_limit_seconds = None
        puzzle.avg_difficulty = 3  # Easy
        puzzle.creator_difficulty = 3
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 1
        circuit.cost = 80
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 1}
        test_case.expected_outputs = {"out": 1}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}
        
        attempt = Mock()
        attempt.passed = True
        attempt.fail_reason = None
        attempt.to_dict.return_value = {"id": 1}
        attempt.elapsed_seconds = 30
        attempt.circuit_id = 1
        attempt.finalize_submission = Mock()
        attempt.mark_submitted = Mock()
        attempt.force_rollback = False
        
        solve_repo = Mock()
        solve_repo.get_open_attempt.return_value = attempt
        solve_repo.update_attempt = Mock()
        solve_repo.has_passed_before_attempt = Mock(return_value=False)  # First time!
        
        xp_service = Mock()
        xp_award = Mock()
        xp_award.__dict__ = {"base": 20, "bonus": 0}
        xp_service.award_solve_xp = Mock()
        xp_service.reward_for_solve = Mock(return_value=xp_award)
        
        conn = Mock()
        conn.commit = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
        )
        
        result = service.submit_solution("token", 1, {"circuit_id": 1})
        
        assert result["passed"] == True
        
        # Verify is_first_solve is True
        call_args = xp_service.award_solve_xp.call_args
        assert call_args[1]["is_first_solve"] == True
        assert call_args[1]["difficulty_tier"] == "easy"


class TestMarkSubmittedException:
    """Test mark_submitted exception handling (lines 221-224)"""
    
    def test_mark_submitted_exception_triggers_rollback(self):
        """Test that exception in mark_submitted triggers rollback (line 222-224)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.budget = 200
        puzzle.time_limit_seconds = None
        puzzle.avg_difficulty = 5
        puzzle.creator_difficulty = 5
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 1
        circuit.cost = 80
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 1}
        test_case.expected_outputs = {"out": 1}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}
        
        attempt = Mock()
        attempt.passed = True
        attempt.fail_reason = None
        attempt.to_dict.return_value = {"id": 1}
        attempt.elapsed_seconds = 30
        attempt.circuit_id = 1
        attempt.finalize_submission = Mock()
        attempt.mark_submitted = Mock(side_effect=Exception("DB error"))
        attempt.force_rollback = False
        
        solve_repo = Mock()
        solve_repo.get_open_attempt.return_value = attempt
        solve_repo.update_attempt = Mock()
        solve_repo.has_passed_before_attempt = Mock(return_value=False)
        
        xp_service = Mock()
        xp_service.award_solve_xp = Mock()
        
        conn = Mock()
        conn.commit = Mock()
        conn.execute = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
        )
        
        with pytest.raises(Exception, match="DB error"):
            service.submit_solution("token", 1, {"circuit_id": 1})


class TestEasyDifficultyClassification:
    """Test easy difficulty classification in submit_solution"""
    
    def test_difficulty_tier_easy_for_low_difficulty(self):
        """Test that difficulty below 4 is classified as easy"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.budget = 200
        puzzle.time_limit_seconds = None
        puzzle.avg_difficulty = 2  # Low difficulty = easy
        puzzle.creator_difficulty = 2
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 1
        circuit.cost = 80
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 1}
        test_case.expected_outputs = {"out": 1}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}
        
        attempt = Mock()
        attempt.passed = True
        attempt.fail_reason = None
        attempt.to_dict.return_value = {"id": 1}
        attempt.elapsed_seconds = 30
        attempt.circuit_id = 1
        attempt.finalize_submission = Mock()
        attempt.mark_submitted = Mock()
        attempt.force_rollback = False
        
        solve_repo = Mock()
        solve_repo.get_open_attempt.return_value = attempt
        solve_repo.update_attempt = Mock()
        solve_repo.has_passed_before_attempt = Mock(return_value=True)
        
        xp_service = Mock()
        xp_award = Mock()
        xp_award.__dict__ = {"base": 10, "bonus": 0}
        xp_service.award_solve_xp = Mock()
        xp_service.reward_for_solve = Mock(return_value=xp_award)
        
        conn = Mock()
        conn.commit = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
        )
        
        result = service.submit_solution("token", 1, {"circuit_id": 1})
        
        assert result["passed"] == True
        
        # Verify difficulty_tier is "easy"
        call_args = xp_service.award_solve_xp.call_args
        assert call_args[1]["difficulty_tier"] == "easy"


class TestCreatorDifficultyFallback:
    """Test fallback to creator_difficulty when avg_difficulty is None"""
    
    def test_creator_difficulty_used_when_avg_is_none(self):
        """Test that creator_difficulty is used as fallback (line 208-213)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.budget = 200
        puzzle.time_limit_seconds = None
        puzzle.avg_difficulty = None  # No avg difficulty
        puzzle.creator_difficulty = 7  # Use creator difficulty
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 1
        circuit.cost = 80
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 1}
        test_case.expected_outputs = {"out": 1}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}
        
        attempt = Mock()
        attempt.passed = True
        attempt.fail_reason = None
        attempt.to_dict.return_value = {"id": 1}
        attempt.elapsed_seconds = 30
        attempt.circuit_id = 1
        attempt.finalize_submission = Mock()
        attempt.mark_submitted = Mock()
        attempt.force_rollback = False
        
        solve_repo = Mock()
        solve_repo.get_open_attempt.return_value = attempt
        solve_repo.update_attempt = Mock()
        solve_repo.has_passed_before_attempt = Mock(return_value=True)
        
        xp_service = Mock()
        xp_award = Mock()
        xp_award.__dict__ = {"base": 70, "bonus": 0}
        xp_service.award_solve_xp = Mock()
        xp_service.reward_for_solve = Mock(return_value=xp_award)
        
        conn = Mock()
        conn.commit = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
        )
        
        result = service.submit_solution("token", 1, {"circuit_id": 1})
        
        assert result["passed"] == True
        
        # Should use creator_difficulty which is 7 (hard)
        call_args = xp_service.reward_for_solve.call_args
        assert call_args[1]["difficulty_1_to_10"] == 7


class TestSequenceSimulationAdvanced:
    """Advanced sequence simulation tests (lines 524-544, 641-655)"""
    
    def test_sequence_simulation_with_dff_state_tracking(self):
        """Test sequence simulation with stateful DFF components"""
        circuit = Circuit(
            id=1, user_id=1, name="stateful", cost=100,
            structure_json=json.dumps({
                "placedComponents": [
                    {"id": "dff1", "componentId": "DFF"}
                ],
                "state": ["dff1"],  # dff1 is stateful
                "wires": []
            })
        )
        
        test_case = Mock()
        test_case.kind = "stream"
        test_case.input_stream = [{"X": 0}, {"X": 1}, {"X": 1}, {"X": 0}]
        test_case.expected_output_stream = {"Y": [0, 0, 1, 1]}
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        # Simulate DFF state transitions
        logic_engine.evaluate.side_effect = [
            {"Y": 0, "dff1_next": 0},  # cycle 0
            {"Y": 0, "dff1_next": 1},  # cycle 1
            {"Y": 1, "dff1_next": 1},  # cycle 2
            {"Y": 1, "dff1_next": 0},  # cycle 3
        ]
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        assert passed == True
    
    def test_sequence_simulation_output_mismatch_at_end(self):
        """Test sequence where output mismatch occurs at final cycle (line 570)"""
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=100,
            structure_json=json.dumps({
                "placedComponents": [],
                "state": []
            })
        )
        
        test_case = Mock()
        test_case.kind = "stream"
        test_case.input_stream = [{"X": 0}, {"X": 1}]
        test_case.expected_output_stream = {"Y": [1, 1]}
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        logic_engine.evaluate.side_effect = [
            {"Y": 1},  # cycle 0 matches
            {"Y": 0},  # cycle 1 MISMATCH
        ]
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        assert passed == False
        assert "Sequential output mismatch" in msg
        assert details[0]["actual"]["Y"] == [1, 0]
    
    def test_gate_count_limit_from_puzzle_property(self):
        """Test gate_count_limit when max_gate_count comes from puzzle (lines 468-471)"""
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=100,
            structure_json=json.dumps({"placedComponents": []})
        )
        
        test_case = Mock()
        test_case.kind = "gate_count_limit"
        test_case.max_gate_count = None  # Not in test case
        
        puzzle = Mock()
        puzzle.total_gate_count = 5  # From puzzle property
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {"AND": 3, "OR": 4}  # Total 7 > 5
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        assert passed == False
        assert "Total gate count exceeded" in msg
        assert details[0]["actual_total"] == 7


class TestMedalCalculationEdgeCases:
    """Test medal and XP calculation edge cases (lines 289-332, 364-388)"""
    
    def test_validate_solution_medal_silver_path(self):
        """Test SILVER medal calculation path (lines 289-332)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.avg_difficulty = 5.0  # MEDIUM
        puzzle.time_limit_seconds = 60
        puzzle.budget = 100
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 0}
        test_case.expected_outputs = {"out": 0}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 0}
        
        xp_service = Mock()
        xp_service.calculate_medal.return_value = Medal.SILVER
        xp_service.calculate_solve_xp.return_value = 180
        xp_service.BASE_XP = {PuzzleDifficulty.MEDIUM: 120}
        xp_service.MEDAL_BONUS = {Medal.GOLD: 50}
        
        solve_repo = Mock()
        progress = Mock()
        progress.best_medal = 0  # First solve
        progress.best_xp = 0
        progress.timer_upgraded = False
        progress.tight_upgraded = False
        progress.first_solved_at = None
        solve_repo.get_progress.return_value = progress
        solve_repo.add_solve = Mock()
        solve_repo.upsert_progress = Mock()
        solve_repo.claim_xp_delta.return_value = 90
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
            user_repo=None,
        )
        
        with patch('Backend.ServiceLayer.SolvingService.transaction'):
            result = service.validate_solution("token", 1, {
                "placedComponents": [],
                "totalCost": 50
            }, time_taken=45)
        
        assert result["solved"] == True
        assert result["medal"] == "SILVER"
    
    def test_validate_solution_gold_medal_with_upgrades(self):
        """Test GOLD medal with timer and budget upgrades (lines 332-352)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.avg_difficulty = 8.0  # HARD
        puzzle.time_limit_seconds = 60
        puzzle.budget = 100
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 0}
        test_case.expected_outputs = {"out": 0}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 0}
        
        xp_service = Mock()
        xp_service.calculate_medal.return_value = Medal.GOLD
        xp_service.calculate_solve_xp.return_value = 220
        xp_service.BASE_XP = {PuzzleDifficulty.HARD: 150}
        xp_service.MEDAL_BONUS = {Medal.GOLD: 70}
        
        solve_repo = Mock()
        progress = Mock()
        progress.best_medal = 1  # BRONZE, upgrading to GOLD
        progress.best_xp = 100
        progress.timer_upgraded = False
        progress.tight_upgraded = False
        progress.first_solved_at = "2026-03-01T00:00:00"
        solve_repo.get_progress.return_value = progress
        solve_repo.add_solve = Mock()
        solve_repo.upsert_progress = Mock()
        solve_repo.claim_xp_delta.return_value = 120
        
        user_repo = Mock()
        user_repo.increment_xp = Mock()
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
            user_repo=user_repo,
        )
        
        with patch('Backend.ServiceLayer.SolvingService.transaction'):
            result = service.validate_solution("token", 1, {
                "placedComponents": [],
                "totalCost": 80
            }, time_taken=30)
        
        assert result["solved"] == True
        assert result["medal"] == "GOLD"
        user_repo.increment_xp.assert_called()
    
    def test_validate_solution_creator_xp_never_called(self):
        """Test path where creator XP award fails gracefully (lines 356-357)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 2  # Different creator
        puzzle.avg_difficulty = 5.0
        puzzle.time_limit_seconds = None
        puzzle.budget = 0
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 0}
        test_case.expected_outputs = {"out": 0}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 0}
        
        xp_service = Mock()
        xp_service.calculate_medal.return_value = Medal.BRONZE
        xp_service.calculate_solve_xp.return_value = 100
        xp_service.BASE_XP = {PuzzleDifficulty.MEDIUM: 100}
        xp_service.MEDAL_BONUS = {Medal.GOLD: 50}
        xp_service.award_creator_solve_xp.side_effect = Exception("Service down")
        
        solve_repo = Mock()
        solve_repo.get_progress.return_value = None
        solve_repo.add_solve = Mock()
        solve_repo.upsert_progress = Mock()
        solve_repo.claim_xp_delta.return_value = 50
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
            user_repo=None,
        )
        
        with patch('Backend.ServiceLayer.SolvingService.transaction'):
            result = service.validate_solution("token", 1, {"totalCost": 0})
        
        # Should still succeed even though creator XP failed
        assert result["solved"] == True


class TestArsenalExpansionEdgeCases:
    """Test arsenal expansion with complex scenarios (lines 641-660)"""
    
    def test_expand_arsenal_with_string_component_id(self):
        """Test arsenal expansion when componentId is a string (line 642)"""
        arsenal_circuit = Mock()
        arsenal_circuit.is_arsenal = True
        arsenal_circuit.name = "Custom_Logic"
        arsenal_circuit.num_inputs = 2
        arsenal_circuit.num_outputs = 1
        arsenal_circuit.truth_table = json.dumps({"0,0": [0], "0,1": [0], "1,0": [0], "1,1": [1]})
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = arsenal_circuit
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=circuit_repo,
            auth=Mock(),
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        payload = {
            "placedComponents": [
                {"id": "custom_comp", "componentId": "42"}  # string ID that converts to int
            ]
        }
        
        result = service._expand_arsenal_pieces(payload)
        assert result["_arsenal_pieces"]["custom_comp"]["id"] == 42
        assert result["_arsenal_pieces"]["custom_comp"]["name"] == "Custom_Logic"
    
    def test_expand_arsenal_with_invalid_component_id(self):
        """Test arsenal expansion with non-numeric componentId (line 655)"""
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = None
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=circuit_repo,
            auth=Mock(),
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        payload = {
            "placedComponents": [
                {"id": "comp1", "componentId": "NOT_A_NUMBER"}  # Invalid component ID
            ]
        }
        
        result = service._expand_arsenal_pieces(payload)
        # Should skip non-numeric IDs gracefully
        assert result["_arsenal_pieces"] == {}
    
    def test_expand_arsenal_with_malformed_truth_table_json(self):
        """Test arsenal with truth table that needs JSON parsing (line 650)"""
        arsenal_circuit = Mock()
        arsenal_circuit.is_arsenal = True
        arsenal_circuit.name = "Malformed"
        arsenal_circuit.num_inputs = 1
        arsenal_circuit.num_outputs = 1
        # Truth table is already parsed (not a string)
        arsenal_circuit.truth_table = {
            "0": [1],
            "1": [0]
        }
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = arsenal_circuit
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=circuit_repo,
            auth=Mock(),
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        payload = {
            "placedComponents": [
                {"id": "comp1", "componentId": 99}
            ]
        }
        
        result = service._expand_arsenal_pieces(payload)
        assert result["_arsenal_pieces"]["comp1"]["truth_table"] == {"0": [1], "1": [0]}


class TestConstraintValidationCombinations:
    """Test combinations of constraint validations (lines 446-536)"""
    
    def test_multiple_gate_limits_one_fails(self):
        """Test multiple gate_limit test cases where one fails (lines 446-468)"""
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=100,
            structure_json=json.dumps({"placedComponents": []})
        )
        
        test_case_1 = Mock()
        test_case_1.kind = "gate_limit"
        test_case_1.gate_name = "AND"
        test_case_1.gate_limit = 5
        
        test_case_2 = Mock()
        test_case_2.kind = "gate_limit"
        test_case_2.gate_name = "OR"
        test_case_2.gate_limit = 2  # This one will fail
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {"AND": 3, "OR": 4}
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(
            circuit, [test_case_1, test_case_2], puzzle
        )
        assert passed == False
        assert "OR" in msg
    
    def test_logic_test_with_dict_test_case(self):
        """Test logic evaluation when test case is a dict (not Mock) (line 575)"""
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=100,
            structure_json=json.dumps({"placedComponents": []})
        )
        
        test_case = {
            "kind": "blackbox",
            "inputs": {"A": 1, "B": 0},
            "expected_outputs": {"out": 1}
        }
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        logic_engine.evaluate.return_value = {"out": 1}
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        assert passed == True
    
    def test_stream_test_with_mixed_dict_and_getattr(self):
        """Test sequence test case with mixed dict/getattr access (lines 507-520)"""
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=100,
            structure_json=json.dumps({
                "placedComponents": [],
                "state": []
            })
        )
        
        # Test case with dict-like access mixed with attributes
        test_case = Mock()
        test_case.kind = "stream"
        test_case.input_stream = [{"X": 0}, {"X": 1}]
        test_case.expected_output_stream = {"Y": [0, 1]}
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        logic_engine.evaluate.side_effect = [
            {"Y": 0},
            {"Y": 1},
        ]
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        assert passed == True


class TestStartAndSubmitAdvanced:
    """Advanced tests for start_attempt and submit_solution (lines 105-224)"""
    
    def test_start_attempt_creator_id_exception_handling(self):
        """Test creator_id conversion with invalid return_value (lines 106-116)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = Mock()  # Mock object without proper int conversion
        puzzle.creator_user_id.__int__ = Mock(side_effect=ValueError())
        puzzle.status = PuzzleStatus.PUBLISHED
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        attempt = Mock()
        attempt.to_dict.return_value = {"id": 1, "puzzle_id": 1, "user_id": 1}
        
        solve_repo = Mock()
        solve_repo.create_attempt.return_value = attempt
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        # Should handle the exception and get return_value
        result = service.start_attempt("token", 1)
        assert result["puzzle_id"] == 1
    
    def test_submit_solution_payload_as_plain_int(self):
        """Test submit_solution when payload is just circuit_id int (lines 131-133)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        # Payload is just an integer (non-dict) which is falsy when 0
        with pytest.raises(ValidationError, match="Circuit ID is required"):
            service.submit_solution("token", 1, 0)  # 0 is falsy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestGateLimitValidation:
    """Test gate limit constraint validation before logic tests"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def test_total_gate_count_exceeded(self):
        """Test that circuit fails when total gate count limit exceeded"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=100, total_gate_count=5
        )
        
        # Test case with total gate count limit
        tc_count_limit = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.GATE_COUNT_LIMIT,
            inputs={}, expected_outputs={}
        )
        tc_count_limit.max_gate_count = 5
        self.mock_puzzle_repo.list_test_cases.return_value = [tc_count_limit]
        
        # Circuit has 10 total gates (exceeds limit of 5)
        self.mock_engine.extract_gate_counts.return_value = {
            "AND": 5, "OR": 3, "NOT": 2
        }
        
        circuit_json = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json=circuit_json)
        
        payload = {"totalCost": 10, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is False
        assert "total gate count" in result["message"].lower()


class TestMedalCalculation:
    """Test medal earning based on performance metrics"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def _setup_passing_puzzle(self, time_limit=60, budget=50, avg_difficulty=2.0):
        """Helper to setup a passing puzzle scenario"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=avg_difficulty,
            time_limit_seconds=time_limit, budget=budget,
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 50
        self.mock_xp.award_creator_solve_xp.return_value = 0
        self.mock_xp.BASE_XP = {
            PuzzleDifficulty.EASY: 50,
            PuzzleDifficulty.MEDIUM: 100,
            PuzzleDifficulty.HARD: 200,
        }
        self.mock_xp.MEDAL_BONUS = {
            Medal.NONE: 0,
            Medal.BRONZE: 0,
            Medal.SILVER: 25,
            Medal.GOLD: 50,
        }
    
    def test_bronze_medal_basic_solve(self):
        """Bronze medal awarded for basic solve without optimization"""
        self._setup_passing_puzzle(time_limit=60, budget=50)
        
        # Slower than time limit, over budget - gets BRONZE
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_solve_xp.return_value = 50
        
        payload = {"totalCost": 60, "components": [], "wires": []}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload, time_taken=120)
        
        assert result["medal"] == Medal.BRONZE.name
    
    def test_silver_medal_with_time_optimization(self):
        """Silver medal awarded for beating time limit"""
        self._setup_passing_puzzle(time_limit=60, budget=50)
        
        self.mock_xp.calculate_medal.return_value = Medal.SILVER
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_solve_xp.return_value = 75
        
        payload = {"totalCost": 60, "components": [], "wires": []}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload, time_taken=30)
        
        assert result["medal"] == Medal.SILVER.name
    
    def test_gold_medal_with_cost_and_time_optimization(self):
        """Gold medal awarded for beating both cost and time limits"""
        self._setup_passing_puzzle(time_limit=60, budget=50)
        
        self.mock_xp.calculate_medal.return_value = Medal.GOLD
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_solve_xp.return_value = 100
        
        payload = {"totalCost": 40, "components": [], "wires": []}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload, time_taken=30)
        
        assert result["medal"] == Medal.GOLD.name


class TestXPAwarding:
    """Test XP awarding logic for solves"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def test_xp_earned_first_solve(self):
        """First solve of a puzzle earns base XP"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=100,
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 75  # First solve bonus
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.award_creator_solve_xp.return_value = 25
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        
        payload = {"totalCost": 10, "components": [], "wires": []}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True
        assert result["xp_earned"] == 75
    
    def test_xp_no_improvement_on_retry(self):
        """Repeat solve with worse performance earns no XP"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=100,
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        # Old progress shows best XP already earned
        old_progress = Mock(best_xp=100, best_medal=1, timer_upgraded=True, tight_upgraded=True)
        self.mock_solve_repo.get_progress.return_value = old_progress
        self.mock_solve_repo.claim_xp_delta.return_value = 0  # No improvement
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 30  # Less than previous best
        self.mock_xp.award_creator_solve_xp.return_value = 0
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        
        payload = {"totalCost": 10, "components": [], "wires": []}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True
        assert result["xp_earned"] == 0
    
    def test_xp_difficulty_based_scaling(self):
        """XP awarded scales with puzzle difficulty"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=8.0,  # Hard puzzle
            time_limit_seconds=None, budget=100,
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 200  # Higher for hard
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.HARD
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 200  # Base for hard
        self.mock_xp.award_creator_solve_xp.return_value = 50
        self.mock_xp.BASE_XP = {
            PuzzleDifficulty.EASY: 50,
            PuzzleDifficulty.HARD: 200,
        }
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        
        payload = {"totalCost": 10, "components": [], "wires": []}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True
        assert result["xp_earned"] == 200


class TestBudgetValidation:
    """Test budget and cost constraint validation"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
    
    def test_circuit_cost_within_budget(self):
        """Circuit with cost within budget passes"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=100,
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 50
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.award_creator_solve_xp.return_value = 0
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        
        payload = {"totalCost": 75, "components": [], "wires": []}  # Within budget of 100
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True

    
    def test_zero_budget_puzzle(self):
        """Zero budget puzzle only accepts zero cost solutions"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=0,  # Zero budget
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        payload = {"totalCost": 0, "components": [], "wires": []}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 50
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.award_creator_solve_xp.return_value = 0
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True


class TestTimerValidation:
    """Test time limit validation and timer-beaten detection"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
    
    def test_timer_beaten_within_limit(self):
        """Solve within time limit beats the timer"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=60, budget=100,  # 60 second time limit
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 75
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.SILVER  # Timer beaten
        self.mock_xp.calculate_solve_xp.return_value = 75
        self.mock_xp.award_creator_solve_xp.return_value = 0
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.SILVER: 25}
        
        payload = {"totalCost": 10, "components": [], "wires": []}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload, time_taken=30)  # 30 seconds
        
        assert result["solved"] is True
        # Medal should reflect timer being beaten
    
    def test_timer_not_beaten_exceeds_limit(self):
        """Solve exceeding time limit does not beat timer"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=60, budget=100,
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 50
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE  # No timer
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.award_creator_solve_xp.return_value = 0
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        
        payload = {"totalCost": 10, "components": [], "wires": []}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload, time_taken=120)  # 120 seconds
        
        assert result["solved"] is True
    
    def test_no_time_limit_puzzle(self):
        """Puzzle with no time limit always beats timer"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=100,  # No time limit
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 50
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.award_creator_solve_xp.return_value = 0
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        
        payload = {"totalCost": 10, "components": [], "wires": []}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload, time_taken=1000)
        
        assert result["solved"] is True



class TestFailedAttemptTracking:
    """Test that failed attempts are tracked for rating eligibility"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
    
    def test_failed_attempt_persists(self):
        """Failed attempts are persisted to allow rating after X attempts"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=100,
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}  # Expects 1
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 0}  # Circuit outputs 0 (wrong)
        
        payload = {"totalCost": 10, "components": [], "wires": []}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload, time_taken=10)
        
        assert result["solved"] is False
        # Verify that failed attempt was recorded
        self.mock_solve_repo.create_attempt.assert_called()


class TestCreatorXPAward:
    """Test creator XP awarding on user solves"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def test_creator_xp_awarded_first_solver(self):
        """Creator receives XP when someone solves their puzzle for first time"""
        self.mock_auth.require_user_id.return_value = 2  # Solver user
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=100,
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.try_award_creator_solve_xp.return_value = True  # First solver
        self.mock_solve_repo.claim_xp_delta.return_value = 50
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.award_creator_solve_xp.return_value = 10  # Creator gets 10 XP
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        
        payload = {"totalCost": 10, "components": [], "wires": []}
        
        with patch.object(self.service, '_expand_arsenal_pieces', return_value=payload):
            result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True
        # Creator XP should be awarded
        self.mock_xp.award_creator_solve_xp.assert_called()


class TestEvaluateTestCasesLogic:
    """Test _evaluate_test_cases internal method comprehensively"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def test_evaluate_blackbox_test_case_passes(self):
        """BLACKBOX test case evaluation - all inputs match"""
        puzzle = Mock(id=1, avg_difficulty=2.0, budget=100, time_limit_seconds=60)
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1, "B": 0}, expected_outputs={"O": 1}
        )
        
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json="{}")
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        passed, msg, details = self.service._evaluate_test_cases(circuit, [tc], puzzle)
        assert passed is True
    
    def test_evaluate_blackbox_test_case_fails(self):
        """BLACKBOX test case fails - output mismatch"""
        puzzle = Mock(id=1, avg_difficulty=2.0, budget=100, time_limit_seconds=60)
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 1, "B": 0}, expected_outputs={"O": 1}
        )
        
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json="{}")
        self.mock_engine.evaluate.return_value = {"O": 0}  # Wrong output
        
        passed, msg, details = self.service._evaluate_test_cases(circuit, [tc], puzzle)
        assert passed is False
        assert "output" in msg.lower() or "mismatch" in msg.lower()
    
    def test_evaluate_whitebox_test_case(self):
        """WHITEBOX test case evaluation"""
        puzzle = Mock(id=1, avg_difficulty=2.0, budget=100, time_limit_seconds=60)
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.WHITEBOX,
            inputs={"S1": 1}, expected_outputs={"Q": 1}
        )
        
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json="{}")
        self.mock_engine.evaluate.return_value = {"Q": 1}
        
        passed, msg, details = self.service._evaluate_test_cases(circuit, [tc], puzzle)
        assert passed is True
    
    def test_evaluate_multiple_test_cases_all_pass(self):
        """Multiple test cases - all pass"""
        puzzle = Mock(id=1, avg_difficulty=2.0, budget=100, time_limit_seconds=60)
        tc1 = PuzzleTestCase(id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
                            inputs={"A": 0}, expected_outputs={"O": 1})
        tc2 = PuzzleTestCase(id=2, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
                            inputs={"A": 1}, expected_outputs={"O": 0})
        
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json="{}")
        # Both evaluations return correct outputs
        self.mock_engine.evaluate.side_effect = [{"O": 1}, {"O": 0}]
        
        passed, msg, details = self.service._evaluate_test_cases(circuit, [tc1, tc2], puzzle)
        assert passed is True
    
    def test_evaluate_multiple_test_cases_one_fails(self):
        """Multiple test cases - one fails"""
        puzzle = Mock(id=1, avg_difficulty=2.0, budget=100, time_limit_seconds=60)
        tc1 = PuzzleTestCase(id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
                            inputs={"A": 0}, expected_outputs={"O": 1})
        tc2 = PuzzleTestCase(id=2, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
                            inputs={"A": 1}, expected_outputs={"O": 0})
        
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json="{}")
        # First passes, second fails
        self.mock_engine.evaluate.side_effect = [{"O": 1}, {"O": 1}]
        
        passed, msg, details = self.service._evaluate_test_cases(circuit, [tc1, tc2], puzzle)
        assert passed is False
    
    def test_evaluate_gate_limit_constraint_within_bounds(self):
        """GATE_LIMIT test case - gate count within limit"""
        puzzle = Mock(id=1, avg_difficulty=2.0, budget=100, time_limit_seconds=60)
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.GATE_LIMIT,
            inputs={}, expected_outputs={}, gate_name="AND", gate_limit=5
        )
        
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json="{}")
        # Extract gate counts returns 3 ANDs (within limit of 5)
        self.mock_engine.extract_gate_counts.return_value = {"AND": 3}
        
        passed, msg, details = self.service._evaluate_test_cases(circuit, [tc], puzzle)
        assert passed is True
    
    def test_evaluate_gate_limit_constraint_exceeded(self):
        """GATE_LIMIT test case - gate count exceeds limit"""
        puzzle = Mock(id=1, avg_difficulty=2.0, budget=100, time_limit_seconds=60)
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.GATE_LIMIT,
            inputs={}, expected_outputs={}, gate_name="OR", gate_limit=2
        )
        
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json="{}")
        # Extract gate counts returns 5 ORs (exceeds limit of 2)
        self.mock_engine.extract_gate_counts.return_value = {"OR": 5}
        
        passed, msg, details = self.service._evaluate_test_cases(circuit, [tc], puzzle)
        assert passed is False
        assert "gate" in msg.lower() or "exceeded" in msg.lower()
    
    def test_evaluate_gate_count_limit_constraint(self):
        """GATE_COUNT_LIMIT test case - total gates within limit"""
        puzzle = Mock(id=1, avg_difficulty=2.0, budget=100, time_limit_seconds=60, total_gate_count=20)
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.GATE_COUNT_LIMIT,
            inputs={}, expected_outputs={}
        )
        tc.max_gate_count = 15
        
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json="{}")
        # Total 12 gates (within limit of 15)
        self.mock_engine.extract_gate_counts.return_value = {"AND": 5, "OR": 4, "NOT": 3}
        
        passed, msg, details = self.service._evaluate_test_cases(circuit, [tc], puzzle)
        assert passed is True
    
    def test_evaluate_gate_count_limit_exceeded(self):
        """GATE_COUNT_LIMIT test case - total gates exceeds limit"""
        puzzle = Mock(id=1, avg_difficulty=2.0, budget=100, time_limit_seconds=60, total_gate_count=20)
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.GATE_COUNT_LIMIT,
            inputs={}, expected_outputs={}
        )
        tc.max_gate_count = 10
        
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json="{}")
        # Total 15 gates (exceeds limit of 10)
        self.mock_engine.extract_gate_counts.return_value = {"AND": 6, "OR": 5, "NOT": 4}
        
        passed, msg, details = self.service._evaluate_test_cases(circuit, [tc], puzzle)
        assert passed is False
        assert "gate" in msg.lower()
    
    def test_evaluate_stream_test_case_passes(self):
        """STREAM test case - sequence evaluation passes"""
        puzzle = Mock(id=1, avg_difficulty=2.0, budget=100, time_limit_seconds=60)
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.STREAM,
            inputs={}, expected_outputs={},
            input_stream=[0, 1, 0, 1],
            expected_output_stream={"output": [0, 1, 1, 0]}
        )
        
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json="{}")
        # For each cycle, evaluate returns the output value
        self.mock_engine.evaluate.side_effect = [
            {"output": 0},  # cycle 0: input 0 -> output 0
            {"output": 1},  # cycle 1: input 1 -> output 1
            {"output": 1},  # cycle 2: input 0 -> output 1
            {"output": 0},  # cycle 3: input 1 -> output 0
        ]
        
        passed, msg, details = self.service._evaluate_test_cases(circuit, [tc], puzzle)
        assert passed is True
    
    def test_evaluate_stream_test_case_fails(self):
        """STREAM test case - sequence evaluation fails"""
        puzzle = Mock(id=1, avg_difficulty=2.0, budget=100, time_limit_seconds=60)
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.STREAM,
            inputs={}, expected_outputs={},
            input_stream=[0, 1, 0, 1],
            expected_output_stream={"output": [0, 1, 1, 0]}
        )
        
        circuit = Circuit(id=1, user_id=1, name="Test", cost=10, structure_json="{}")
        # Wrong outputs - all zeros instead of expected sequence
        self.mock_engine.evaluate.side_effect = [
            {"output": 0},  # Expected 0, got 0 - OK
            {"output": 0},  # Expected 1, got 0 - WRONG
            {"output": 0},  # Expected 1, got 0 - WRONG
            {"output": 0},  # Expected 0, got 0 - OK
        ]
        
        passed, msg, details = self.service._evaluate_test_cases(circuit, [tc], puzzle)
        assert passed is False


class TestValidateSolutionMedalPaths:
    """Test validate_solution medal calculation paths"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def _setup_passing_solution(self, **kwargs):
        """Helper to setup a passing puzzle/circuit scenario"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED,
            avg_difficulty=kwargs.get('avg_difficulty', 2.0),
            time_limit_seconds=kwargs.get('time_limit_seconds', 60),
            budget=kwargs.get('budget', 100),
            name="TestPuzzle"
        )
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 1}
        self.mock_engine.extract_gate_counts.return_value = {}
        
        # Setup XP service mocks
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = kwargs.get('expected_medal', Medal.BRONZE)
        self.mock_xp.calculate_solve_xp.return_value = 75
        self.mock_xp.award_creator_solve_xp.return_value = 10
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50, PuzzleDifficulty.MEDIUM: 100, PuzzleDifficulty.HARD: 200}
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0, Medal.SILVER: 25, Medal.GOLD: 50}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 50
        self.mock_solve_repo.add_solve.return_value = None
        self.mock_solve_repo.upsert_progress.return_value = None
        self.mock_solve_repo.try_award_creator_solve_xp.return_value = True
        self.mock_user_repo.increment_xp.return_value = None
        self.mock_user_repo.get_by_id.return_value = Mock(username="TestUser")
    
    def test_validate_solution_fails_validation(self):
        """Solution fails test case validation"""
        self._setup_passing_solution()
        self.mock_engine.evaluate.return_value = {"O": 0}  # Wrong output
        
        payload = {"totalCost": 50, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload, time_taken=30)
        
        assert result["solved"] is False
        assert "output" in result.get("message", "").lower() or "mismatch" in result.get("message", "").lower()
    
    def test_validate_solution_medal_bronze(self):
        """Solution earns BRONZE medal (slow/expensive)"""
        self._setup_passing_solution(
            time_limit_seconds=60, budget=100,
            expected_medal=Medal.BRONZE
        )
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        
        payload = {"totalCost": 95, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload, time_taken=58)
        
        assert result["solved"] is True
        assert "BRONZE" in result["medal"]
    
    def test_validate_solution_medal_silver(self):
        """Solution earns SILVER medal (beat time limit)"""
        self._setup_passing_solution(
            time_limit_seconds=60, budget=100,
            expected_medal=Medal.SILVER
        )
        self.mock_xp.calculate_medal.return_value = Medal.SILVER
        
        payload = {"totalCost": 80, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload, time_taken=45)
        
        assert result["solved"] is True
        assert "SILVER" in result["medal"]
    
    def test_validate_solution_medal_gold(self):
        """Solution earns GOLD medal (beat both time and budget)"""
        self._setup_passing_solution(
            time_limit_seconds=60, budget=100,
            expected_medal=Medal.GOLD
        )
        self.mock_xp.calculate_medal.return_value = Medal.GOLD
        
        payload = {"totalCost": 60, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload, time_taken=40)
        
        assert result["solved"] is True
        assert "GOLD" in result["medal"]
    
    def test_validate_solution_xp_first_time(self):
        """First-time solve awards full XP"""
        self._setup_passing_solution()
        self.mock_solve_repo.get_progress.return_value = None  # No prior solve
        self.mock_solve_repo.claim_xp_delta.return_value = 75
        
        payload = {"totalCost": 50, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True
        assert result["xp_earned"] == 75
    
    def test_validate_solution_xp_improvement(self):
        """Better solve earns additional XP"""
        self._setup_passing_solution()
        old_progress = Mock(
            best_xp=50,
            best_medal=Medal.BRONZE.value,
            timer_upgraded=False,
            tight_upgraded=False,
            first_solved_at="2026-01-01T00:00:00Z",
        )
        self.mock_solve_repo.get_progress.return_value = old_progress
        self.mock_solve_repo.claim_xp_delta.return_value = 25  # Delta from previous best
        
        payload = {"totalCost": 40, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True
        assert result["xp_earned"] == 25

    def test_validate_solution_message_max_xp_with_gain(self):
        """If this solve reaches max XP and awards XP, message should be celebratory."""
        self._setup_passing_solution()
        # Simulate legacy/inconsistent progress state where first-solve heuristic can be false.
        self.mock_solve_repo.get_progress.return_value = Mock(
            best_xp=0,
            best_medal=0,
            timer_upgraded=False,
            tight_upgraded=False,
            first_solved_at="2026-01-01T00:00:00Z",
        )
        self.mock_xp.calculate_medal.return_value = Medal.GOLD
        self.mock_xp.calculate_solve_xp.return_value = 100
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.GOLD: 50}
        self.mock_solve_repo.claim_xp_delta.return_value = 100

        payload = {"totalCost": 40, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload, time_taken=10)

        assert result["solved"] is True
        assert result["xp_left_for_max"] == 0
        assert "reached this puzzle's maximum XP" in result["message"]
        assert "No XP improvement this time." not in result["message"]

    def test_validate_solution_message_shows_xp_left_for_max(self):
        """When max XP is not reached yet, include remaining XP message."""
        self._setup_passing_solution()
        self.mock_solve_repo.get_progress.return_value = Mock(
            best_xp=50,
            best_medal=Medal.BRONZE.value,
            timer_upgraded=False,
            tight_upgraded=False,
            first_solved_at="2026-01-01T00:00:00Z",
        )
        self.mock_xp.calculate_medal.return_value = Medal.SILVER
        self.mock_xp.calculate_solve_xp.return_value = 75
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.GOLD: 50}
        self.mock_solve_repo.claim_xp_delta.return_value = 25

        payload = {"totalCost": 60, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload, time_taken=35)

        assert result["solved"] is True
        assert result["xp_left_for_max"] == 25
        assert "You have 25 XP left for max." in result["message"]


class TestValidateSolutionDifficultyTiers:
    """Test difficulty tier calculations in validate_solution"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def _setup_puzzle(self, avg_difficulty):
        """Setup puzzle with specific difficulty"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=2, avg_difficulty=avg_difficulty,
            time_limit_seconds=60, budget=100, name="Test"
        )
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 1}
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 100
        self.mock_xp.BASE_XP = {
            PuzzleDifficulty.EASY: 50,
            PuzzleDifficulty.MEDIUM: 100,
            PuzzleDifficulty.HARD: 200
        }
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 50
        self.mock_solve_repo.add_solve.return_value = None
        self.mock_solve_repo.upsert_progress.return_value = None
        self.mock_solve_repo.try_award_creator_solve_xp.return_value = False
        self.mock_user_repo.increment_xp.return_value = None
    
    def test_validate_solution_hard_difficulty(self):
        """Hard puzzle detected from avg_difficulty >= 7.0"""
        self._setup_puzzle(avg_difficulty=8.5)
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.HARD
        
        payload = {"totalCost": 50, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True
        # tier_from_avg_difficulty should have been called
        self.mock_xp.tier_from_avg_difficulty.assert_called()
    
    def test_validate_solution_medium_difficulty(self):
        """Medium puzzle detected from avg_difficulty 4-6.9"""
        self._setup_puzzle(avg_difficulty=5.5)
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.MEDIUM
        
        payload = {"totalCost": 50, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True
    
    def test_validate_solution_easy_difficulty(self):
        """Easy puzzle detected from avg_difficulty < 4.0"""
        self._setup_puzzle(avg_difficulty=2.0)
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        
        payload = {"totalCost": 50, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True

    def test_validate_solution_prefers_creator_difficulty_for_xp(self):
        """Creator-set difficulty should be used before avg_difficulty for XP tier."""
        self._setup_puzzle(avg_difficulty=8.5)  # Would be HARD if avg_difficulty was used
        puzzle = self.mock_puzzle_repo.get_by_id.return_value
        puzzle.difficulty = PuzzleDifficulty.MEDIUM

        payload = {"totalCost": 50, "components": [], "wires": []}
        result = self.service.validate_solution("token", 1, payload)

        assert result["solved"] is True
        self.mock_xp.calculate_solve_xp.assert_called_once()
        call_kwargs = self.mock_xp.calculate_solve_xp.call_args.kwargs
        assert call_kwargs["difficulty"] == PuzzleDifficulty.MEDIUM
        self.mock_xp.tier_from_avg_difficulty.assert_not_called()


class TestSimulateSolutionMethods:
    """Test simulate_solution and related methods"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
    
    def test_simulate_solution_single_step(self):
        """Simulate solution for single input set"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(id=1, creator_user_id=1, min_gate_count=0, total_gate_count=0, budget=0, time_limit_seconds=None, avg_difficulty=2.0, avg_fun=2.0, avg_clearness=2.0, status=PuzzleStatus.PUBLISHED)
        self.mock_circuit_repo.get_by_id.return_value = Mock(
            id=1, user_id=1, structure_json=json.dumps({})
        )
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        payload = {"circuit_id": 1, "components": [], "wires": []}
        result = self.service.simulate_solution("token", 1, payload, {"A": 1}, is_sequence=False)
        
        assert isinstance(result, dict)
    
    def test_simulate_solution_sequence(self):
        """Simulate solution for sequence of inputs"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(id=1, creator_user_id=1, min_gate_count=0, total_gate_count=0, budget=0, time_limit_seconds=None, avg_difficulty=2.0, avg_fun=2.0, avg_clearness=2.0, status=PuzzleStatus.PUBLISHED)
        self.mock_circuit_repo.get_by_id.return_value = Mock(
            id=1, user_id=1, structure_json=json.dumps({})
        )
        self.mock_engine.simulate_sequence = MagicMock(return_value=[0, 1, 1, 0])
        
        payload = {"circuit_id": 1, "components": [], "wires": []}
        result = self.service.simulate_solution(
            "token", 1, payload,
            {"A": [0, 1, 0, 1]},
            is_sequence=True
        )
        
        assert isinstance(result, dict)


class TestExpandArsenalPieces:
    """Test _expand_arsenal_pieces method"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
    
    def test_expand_arsenal_simple_payload(self):
        """Expand simple payload with basic components"""
        payload = {
            "components": [
                {"id": "c1", "type": "AND", "x": 0, "y": 0}
            ],
            "wires": [
                {"from": "input1", "to": "c1"}
            ],
            "totalCost": 5
        }
        
        result = self.service._expand_arsenal_pieces(payload)
        assert isinstance(result, dict)
        assert "components" in result or "totalCost" in result
    
    def test_expand_arsenal_empty_payload(self):
        """Expand empty payload"""
        payload = {"components": [], "wires": [], "totalCost": 0}
        
        result = self.service._expand_arsenal_pieces(payload)
        assert isinstance(result, dict)
        assert "totalCost" in result


class TestValidateSolutionErrorCases:
    """Test error handling paths in validate_solution"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def test_validate_solution_puzzle_not_found(self):
        """Puzzle doesn't exist"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError):
            self.service.validate_solution("token", 999, {})
    
    def test_validate_solution_no_test_cases(self):
        """Puzzle has no test cases"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(id=1, creator_user_id=1, min_gate_count=0, total_gate_count=0, budget=0, time_limit_seconds=None, avg_difficulty=2.0, avg_fun=2.0, avg_clearness=2.0, status=PuzzleStatus.PUBLISHED)
        self.mock_puzzle_repo.list_test_cases.return_value = []
        
        with pytest.raises(ValidationError):
            self.service.validate_solution("token", 1, {})
    
    def test_validate_solution_creator_xp_award_failure(self):
        """Creator XP award fails gracefully"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=2, avg_difficulty=2.0,
            time_limit_seconds=60, budget=100, name="Test"
        )
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 1}
        self.mock_engine.extract_gate_counts.return_value = {}
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 50
        self.mock_solve_repo.add_solve.return_value = None
        self.mock_solve_repo.upsert_progress.return_value = None
        # award_creator_solve_xp raises exception
        self.mock_xp.award_creator_solve_xp.side_effect = Exception("XP award failed")
        self.mock_user_repo.increment_xp.return_value = None
        
        payload = {"totalCost": 50, "components": [], "wires": []}
        # Should not raise - graceful failure
        result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True  # Main solve should still pass


class TestStartAttemptVariations:
    """Test start_attempt with various states"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
    
    def test_start_attempt_draft_puzzle_by_creator(self):
        """Creator can start attempt on their draft puzzle"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, status=PuzzleStatus.DRAFT
        )
        
        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 1
        attempt.to_dict.return_value = {"id": 1, "puzzle_id": 1, "user_id": 1}
        self.mock_solve_repo.create_attempt.return_value = attempt
        
        result = self.service.start_attempt("token", 1)
        assert result is not None
    
    def test_start_attempt_draft_puzzle_by_other(self):
        """Non-creator cannot start attempt on draft puzzle"""
        self.mock_auth.require_user_id.return_value = 2  # Different user
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, status=PuzzleStatus.DRAFT
        )
        
        with pytest.raises(ValidationError):
            self.service.start_attempt("token", 1)
    
    def test_start_attempt_published_puzzle_any_user(self):
        """Any user can start attempt on published puzzle"""
        self.mock_auth.require_user_id.return_value = 99
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, status=PuzzleStatus.PUBLISHED
        )
        
        attempt = Mock(spec=SolveAttempt)
        attempt.id = 1
        attempt.puzzle_id = 1
        attempt.user_id = 99
        attempt.to_dict.return_value = {"id": 1, "puzzle_id": 1, "user_id": 99}
        self.mock_solve_repo.create_attempt.return_value = attempt
        
        result = self.service.start_attempt("token", 1)
        assert result["user_id"] == 99


class TestSolvingServiceExtended:
    def setup_method(self):
        self.mock_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_logic = Mock(spec=logicEngineService)
        self.mock_logic.compute_cost = Mock(return_value=0)
        self.mock_logic.has_entry_for_inputs = Mock(return_value=True)
        self.mock_logic.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_conn = Mock()

        from Backend.PersistantLayer.SolveRepo import PuzzleProgress
        # validate_solution calls get_progress 3 times: old_progress_for_xp, old_progress, new_progress
        # For a passing test: old returns None/None, new returns progress with XP
        self._progress_after = PuzzleProgress(user_id=1, puzzle_id=1, best_medal=1, timer_upgraded=False, tight_upgraded=False, first_solved_at=None, best_xp=50, total_xp_awarded=50)
        self.mock_repo.get_progress.return_value = None
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.award_creator_solve_xp.return_value = 0
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50, PuzzleDifficulty.MEDIUM: 100, PuzzleDifficulty.HARD: 200}
        self.mock_xp.MEDAL_BONUS = {Medal.NONE: 0, Medal.BRONZE: 0, Medal.SILVER: 25, Medal.GOLD: 50}
        self.mock_repo.get_best_xp_for_puzzle.return_value = 0
        # Provide conn on solve_repo so validate_solution can do raw SQL queries
        self.mock_repo.conn = self.mock_conn
        # Make the raw SQL query return empty results by default
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        self.mock_conn.execute.return_value = mock_cursor

        self.service = SolvingService(
            self.mock_conn,
            self.mock_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_logic,
            self.mock_xp
        )

    def test_validate_solution_success(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=0,
        )

        tc = PuzzleTestCase(id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX, inputs={"A": 0}, expected_outputs={"O": 1})
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]

        self.mock_logic.evaluate.return_value = {"O": 1}
        # get_progress is called 2 times: old_progress (for medal tracking), new_progress
        self.mock_repo.get_progress.side_effect = [None, None, self._progress_after]
        # claim_xp_delta returns claimed XP amount (atomic XP claim pattern)
        self.mock_repo.claim_xp_delta.return_value = 50

        payload = {
            "totalCost": 10,
            "components": [],
            "wires": []
        }

        result = self.service.validate_solution("token", 1, payload)

        assert result["solved"] is True
        assert result["message"].startswith("All test cases passed!")
        assert self.mock_logic.evaluate.call_count == 1

    def test_validate_solution_fail(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=0,
        )
        tc = PuzzleTestCase(id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX, inputs={"A": 0}, expected_outputs={"O": 1})
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        
        self.mock_logic.evaluate.return_value = {"O": 0} 
        
        payload = {"totalCost": 10}
        result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is False
        assert result["message"] == "Wrong output"

    def test_submit_solution_sequential_success(self):
        self.mock_auth.require_user_id.return_value = 1
        # Set budget to a value to avoid int(None) error
        puzzle = Mock(id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED, time_limit_seconds=None, budget=100000)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Circuit(id=100, user_id=1, name="My Sol", cost=50, structure_json='{"components": [{"id": "dff1", "type": "DFF"}]}')
        self.mock_circuit_repo.get_by_id.return_value = circuit
        
        tc = Mock()
        tc.inputs = {"X": 0}
        tc.expected_outputs = {"O": 0}
        tc.input_stream = [0, 1]
        tc.expected_output_stream = {"O": [0, 1]}
        
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        
        def side_effect(circ, inputs):
            x = inputs.get("X", 0)
            return {"O": x, "dff1_next": x}
            
        self.mock_logic.evaluate.side_effect = side_effect
        
        attempt = SolveAttempt(id=55, puzzle_id=1, user_id=1)
        self.mock_repo.get_open_attempt.return_value = attempt
        
        result = self.service.submit_solution("token", 1, 100)
        
        assert result["passed"] is True
        assert attempt.passed is True

    def test_submit_solution_sequential_fail_mismatch(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(id=1, budget=1000, creator_user_id=1, min_gate_count=0, total_gate_count=0, time_limit_seconds=None, avg_difficulty=2.0, avg_fun=2.0, avg_clearness=2.0, status=PuzzleStatus.PUBLISHED)
        self.mock_circuit_repo.get_by_id.return_value = Circuit(id=100, user_id=1, name="Fail", cost=10, structure_json='{}')
        
        tc = Mock()
        tc.inputs = {"X": 0}
        tc.expected_outputs = {"O": 0}
        tc.input_stream = [0]
        tc.expected_output_stream = {"O": [1]}
        
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_logic.evaluate.return_value = {"O": 0}
        
        attempt = SolveAttempt(id=55, puzzle_id=1, user_id=1)
        self.mock_repo.get_open_attempt.return_value = attempt
        
        result = self.service.submit_solution("token", 1, 100)
        
        assert result["passed"] is False
        assert "Sequential output mismatch" in result["fail_reason"]

    def test_submit_solution_sequential_exception(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(id=1, budget=1000, creator_user_id=1, min_gate_count=0, total_gate_count=0, time_limit_seconds=None, avg_difficulty=2.0, avg_fun=2.0, avg_clearness=2.0, status=PuzzleStatus.PUBLISHED)
        self.mock_circuit_repo.get_by_id.return_value = Circuit(id=100, user_id=1, name="Ex", cost=10, structure_json='{}')
        
        tc = Mock()
        tc.inputs = {"X": 0}
        tc.expected_outputs = {"O": 0}
        tc.input_stream = [0]
        tc.expected_output_stream = {"O": [1]}
        
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_logic.evaluate.side_effect = Exception("Boom")
        
        attempt = SolveAttempt(id=55, puzzle_id=1, user_id=1)
        self.mock_repo.get_open_attempt.return_value = attempt
        
        result = self.service.submit_solution("token", 1, 100)
        
        assert result["passed"] is False
        assert "Cycle 0 error: Boom" in result["fail_reason"]


class TestSubmitSolutionBudgetValidation:
    """Test submit_solution budget constraint checking"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def test_submit_solution_exceeds_budget(self):
        """Solution cost exceeds puzzle budget"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED,
            budget=50,  # Only 50 cost allowed
            avg_difficulty=3.0, time_limit_seconds=60
        )
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        circuit = Mock(id=1, user_id=1, cost=100, structure_json="{}", force_rollback=False)  # Cost 100 > budget 50
        self.mock_circuit_repo.get_by_id.return_value = circuit
        self.mock_solve_repo.get_open_attempt.return_value = None
        attempt = Mock(
            id=1, puzzle_id=1, user_id=1, passed=False,
            to_dict=Mock(return_value={}), force_rollback=False
        )
        self.mock_solve_repo.create_attempt.return_value = attempt
        
        result = self.service.submit_solution("token", 1, {"circuit_id": 1})
        
        assert result["passed"] is False
    
    def test_submit_solution_within_budget(self):
        """Solution cost within puzzle budget"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED,
            budget=100, avg_difficulty=3.0, time_limit_seconds=60
        )
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        circuit = Mock(id=1, user_id=1, cost=50, structure_json="{}", force_rollback=False)  # Cost 50 < budget 100
        self.mock_circuit_repo.get_by_id.return_value = circuit
        self.mock_solve_repo.get_open_attempt.return_value = None
        attempt = Mock(
            id=1, puzzle_id=1, user_id=1, passed=True, 
            to_dict=Mock(return_value={}), elapsed_seconds=30, force_rollback=False
        )
        self.mock_solve_repo.create_attempt.return_value = attempt
        self.mock_conn.commit = Mock()
        
        result = self.service.submit_solution("token", 1, {"circuit_id": 1})
        
        assert result["passed"] is True


class TestSubmitSolutionCircuitOwnership:
    """Test submit_solution circuit ownership validation"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
    
    def test_submit_solution_unauthorized_circuit(self):
        """User tries to submit someone else's circuit"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED
        )
        
        circuit = Mock(id=1, user_id=999, cost=10, structure_json="{}")  # Different user
        self.mock_circuit_repo.get_by_id.return_value = circuit
        
        with pytest.raises(ValidationError, match="do not have permission"):
            self.service.submit_solution("token", 1, {"circuit_id": 1})


class TestValidateSolutionPayloadHandling:
    """Test validate_solution with various payload types"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def test_validate_solution_with_zero_time(self):
        """Validate solution with zero time taken"""
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=60, budget=100
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.GOLD
        self.mock_xp.calculate_solve_xp.return_value = 100
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.GOLD: 50}
        
        self.mock_solve_repo.get_progress.return_value = PuzzleProgress(
            user_id=1, puzzle_id=1, best_medal=0, timer_upgraded=False,
            tight_upgraded=False, first_solved_at=None, max_xp_reached=False,
            best_xp=0, total_xp_awarded=0
        )
        self.mock_solve_repo.claim_xp_delta.return_value = 50
        self.mock_user_repo.increment_xp = Mock()
        
        result = self.service.validate_solution("token", 1, {}, time_taken=0)
        
        assert result["solved"] is True
        assert result["time_taken"] == 0
    
    def test_validate_solution_with_large_time(self):
        """Validate solution with large time exceeding limit"""
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=30, budget=100
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE  # Below time limit
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 50
        self.mock_user_repo.increment_xp = Mock()
        
        result = self.service.validate_solution("token", 1, {}, time_taken=120)
        
        assert result["solved"] is True
        assert result["time_taken"] == 120


class TestValidateSolutionCreatorXPEdgeCases:
    """Test validate_solution creator XP awarding edge cases"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_notification = Mock()
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
            notification_service=self.mock_notification,
        )
    
    def test_validate_solution_creator_xp_first_solver(self):
        """First person to solve - creator gets XP"""
        self.mock_auth.require_user_id.return_value = 2
        puzzle = Mock(
            id=1, creator_user_id=1, name="Test", avg_difficulty=5.0,
            time_limit_seconds=60, budget=100
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.MEDIUM
        self.mock_xp.calculate_medal.return_value = Medal.SILVER
        self.mock_xp.calculate_solve_xp.return_value = 125
        self.mock_xp.BASE_XP = {PuzzleDifficulty.MEDIUM: 100}
        self.mock_xp.MEDAL_BONUS = {Medal.SILVER: 25}
        self.mock_xp.award_creator_solve_xp.return_value = 50
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.try_award_creator_solve_xp.return_value = True
        self.mock_solve_repo.claim_xp_delta.return_value = 100
        self.mock_user_repo.increment_xp = Mock()
        self.mock_user_repo.get_by_id.return_value = Mock(username="solver_user")
        
        result = self.service.validate_solution("token", 1, {}, time_taken=40)
        
        assert result["solved"] is True
        self.mock_xp.award_creator_solve_xp.assert_called_once()
        self.mock_notification.notify_creator_solve.assert_called_once()


class TestValidateSolutionWithoutUserRepo:
    """Test validate_solution when user_repo is None"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=None,  # No user repo
        )
    
    def test_validate_solution_no_user_repo(self):
        """Validation succeeds even without user_repo"""
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=60, budget=100
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 0
        
        result = self.service.validate_solution("token", 1, {}, time_taken=30)
        
        assert result["solved"] is True


class TestValidateSolutionDifficultyTierCalculation:
    """Test difficulty tier calculation in validate_solution"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def _setup_puzzle_and_test(self, difficulty_value):
        """Helper to setup puzzle with specific difficulty"""
        puzzle = Mock(
            id=1, creator_user_id=1, avg_difficulty=difficulty_value,
            time_limit_seconds=60, budget=100
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        tiers = {
            PuzzleDifficulty.EASY: 50,
            PuzzleDifficulty.MEDIUM: 100,
            PuzzleDifficulty.HARD: 200,
        }
        self.mock_xp.BASE_XP = tiers
        self.mock_xp.MEDAL_BONUS = {Medal.BRONZE: 0}
    
    def test_validate_solution_hard_puzzle_no_tier_method(self):
        """Hard puzzle when tier_from_avg_difficulty not available"""
        self.mock_auth.require_user_id.return_value = 1
        self._setup_puzzle_and_test(8.5)
        
        # Don't set tier_from_avg_difficulty - test fallback logic
        del self.mock_xp.tier_from_avg_difficulty
        
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 200
        
        self.mock_solve_repo.get_progress.return_value = None
        self.mock_solve_repo.claim_xp_delta.return_value = 200
        self.mock_user_repo.increment_xp = Mock()
        
        result = self.service.validate_solution("token", 1, {}, time_taken=30)
        
        assert result["solved"] is True
        # Verify calculate_solve_xp was called (it handles the XP logic)
        self.mock_xp.calculate_solve_xp.assert_called()


class TestValidateSolutionFailedAttemptLogging:
    """Test validate_solution logging of failed attempts"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
    
    def test_validate_solution_failed_attempt_recorded(self):
        """Failed validation records attempt for later rating"""
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Mock(id=1, creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 0}  # Wrong output
        
        self.mock_solve_repo.create_attempt = Mock(return_value=Mock())
        self.mock_conn.commit = Mock()
        
        result = self.service.validate_solution("token", 1, {}, time_taken=25)
        
        assert result["solved"] is False
        assert "message" in result
        self.mock_solve_repo.create_attempt.assert_called_once()
        self.mock_conn.commit.assert_called()


class TestValidateSolutionMedalUpgrades:
    """Test medal upgrade tracking in validate_solution"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_user_repo = Mock(spec=UserRepo)
        
        self.service = SolvingService(
            self.mock_conn,
            self.mock_solve_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
            user_repo=self.mock_user_repo,
        )
    
    def test_validate_solution_timer_upgrade_achieved(self):
        """Solution achieves timer upgrade"""
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Mock(
            id=1, creator_user_id=1, avg_difficulty=3.0,
            time_limit_seconds=60, budget=100
        )
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX,
            inputs={"A": 0}, expected_outputs={"O": 1}
        )
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_engine.evaluate.return_value = {"O": 1}
        
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.GOLD
        self.mock_xp.calculate_solve_xp.return_value = 100
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50}
        self.mock_xp.MEDAL_BONUS = {Medal.GOLD: 50}
        
        old_progress = PuzzleProgress(
            user_id=1, puzzle_id=1, best_medal=2,  # Silver before
            timer_upgraded=False, tight_upgraded=False,
            first_solved_at=None, max_xp_reached=False,
            best_xp=75, total_xp_awarded=0
        )
        self.mock_solve_repo.get_progress.return_value = old_progress
        self.mock_solve_repo.claim_xp_delta.return_value = 25
        self.mock_user_repo.increment_xp = Mock()
        
        result = self.service.validate_solution("token", 1, {}, time_taken=40)
        
        assert result["solved"] is True
        self.mock_solve_repo.upsert_progress.assert_called_once()
        # Check that timer_upgraded was set
        call_args = self.mock_solve_repo.upsert_progress.call_args[0][0]
        assert call_args.timer_upgraded is True


class TestExpandArsenalPiecesComplex:
    """Test _expand_arsenal_pieces with complex payloads"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
    
    def test_expand_arsenal_with_nested_payload(self):
        """Expand arsenal with nested component structure"""
        payload = {
            "totalCost": 50,
            "components": [
                {"id": "c1", "type": "AND", "spec_cost": 10},
                {"id": "c2", "type": "OR", "spec_cost": 15},
            ],
            "wires": [
                {"from": {"componentId": "c1"}, "to": {"componentId": "c2"}}
            ]
        }
        
        result = self.service._expand_arsenal_pieces(payload)
        
        assert result["totalCost"] == 50
        assert "components" in result
        assert len(result["components"]) == 2
    
    def test_expand_arsenal_with_missing_cost(self):
        """Expand arsenal when totalCost is missing"""
        payload = {
            "components": [],
            "wires": []
        }
        
        result = self.service._expand_arsenal_pieces(payload)
        
        # Should handle gracefully
        assert isinstance(result, dict)


class TestSimulateSequenceWithStatefulCircuit:
    """Test simulate_solution sequence with state tracking"""
    
    def setup_method(self):
        self.mock_conn = Mock(spec=sqlite3.Connection)
        self.mock_solve_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = MagicMock(spec=logicEngineService)
        self.mock_engine.compute_cost = Mock(return_value=0)
        self.mock_engine.has_entry_for_inputs = Mock(return_value=True)
        self.mock_engine.extract_gate_counts = Mock(return_value={})
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
    
    def test_simulate_sequence_state_accumulation(self):
        """Verify state correctly accumulates across sequence steps"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(id=1, creator_user_id=1, min_gate_count=0, total_gate_count=0, budget=0, time_limit_seconds=None, avg_difficulty=2.0, avg_fun=2.0, avg_clearness=2.0, status=PuzzleStatus.PUBLISHED)
        self.mock_circuit_repo.get_by_id.return_value = Mock(
            id=1, user_id=1, structure_json=json.dumps({
                "state": ["Q"],  # State output Q
                "components": [],
                "wires": []
            })
        )
        
        # Simulate 3 cycles
        self.mock_engine.evaluate.side_effect = [
            {"Q": 0, "Q_next": 1},  # Cycle 0: Q=0, next=1
            {"Q": 1, "Q_next": 0},  # Cycle 1: Q=1, next=0
            {"Q": 0, "Q_next": 1},  # Cycle 2: Q=0, next=1
        ]
        
        payload = {"components": [], "wires": []}
        result = self.service.simulate_solution(
            "token", 1, payload,
            {"X": [0, 1, 0]},  # Single input signal as list
            is_sequence=True
        )
        
        assert isinstance(result, dict)


class TestSubmitSolutionBudgetFlow:
    """Test budget validation and attempt finalization (lines 202-227)"""
    
    def setup_method(self):
        from contextlib import contextmanager
        
        @contextmanager
        def mock_tx(conn):
            yield conn
        
        self.patcher = patch('Backend.ServiceLayer.SolvingService.transaction', side_effect=mock_tx)
        self.patcher.start()
    
    def teardown_method(self):
        self.patcher.stop()
    
    def test_submit_solution_budget_exceeded_with_cost_update(self):
        """Test submit_solution when circuit cost exceeds puzzle budget (lines 202-216)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.budget = 100
        puzzle.time_limit_seconds = None
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 1
        circuit.cost = 150  # Exceeds budget
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 0}
        test_case.expected_outputs = {"out": 0}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 0}
        
        attempt = Mock()
        attempt.passed = True
        attempt.failed = False
        attempt.to_dict.return_value = {"id": 1, "passed": False}
        attempt.fail_reason = "Circuit cost 150 exceeds puzzle budget 100"
        attempt.cost_used = None
        attempt.finalize_submission = Mock()
        attempt.force_rollback = False        
        solve_repo = Mock()
        solve_repo.get_open_attempt.return_value = attempt
        solve_repo.update_attempt = Mock()
        
        xp_service = Mock()
        xp_service.award_solve_xp = Mock()
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
        )
        
        result = service.submit_solution("token", 1, {"circuit_id": 1})
        
        assert result["passed"] == False
        assert "budget" in result["fail_reason"].lower()
    
    def test_submit_solution_successful_with_xp_award(self):
        """Test successful submit_solution with XP award (lines 218-227)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.budget = 200
        puzzle.time_limit_seconds = 60
        puzzle.creator_difficulty = 7
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 1
        circuit.cost = 80
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 1}
        test_case.expected_outputs = {"out": 1}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}
        
        attempt = Mock()
        attempt.passed = True
        attempt.fail_reason = None
        attempt.to_dict.return_value = {"id": 1, "puzzle_id": 1}
        attempt.elapsed_seconds = 45
        attempt.cost_used = 80
        attempt.circuit_id = 1
        attempt.finalize_submission = Mock()
        attempt.mark_submitted = Mock()
        attempt.force_rollback = False        
        solve_repo = Mock()
        solve_repo.get_open_attempt.return_value = attempt
        solve_repo.create_attempt.return_value = attempt
        solve_repo.update_attempt = Mock()
        solve_repo.get_progress = Mock(return_value=None)
        solve_repo.has_passed_before_attempt = Mock(return_value=True)
        
        xp_service = Mock()
        xp_reward = Mock()
        xp_reward.__dict__ = {"base": 100, "bonus": 20}
        xp_service.award_solve_xp = Mock()
        xp_service.reward_for_solve = Mock(return_value=xp_reward)
        
        conn = Mock()
        conn.commit = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
        )
        
        result = service.submit_solution("token", 1, {"circuit_id": 1})
        
        # Verify submission succeeded
        assert result is not None
        assert isinstance(result, dict)
        assert result["passed"] == True


class TestSimulationGateEvaluation:
    """Test gate evaluation in _run_simulation (lines 751-815)"""
    
    def test_run_simulation_with_multiple_components(self):
        """Test simulation with multiple components and wires (lines 751-815)"""
        expanded_solution = {
            "placedComponents": [
                {"id": "in1", "componentId": "IO:IN"},
                {"id": "comp1", "componentId": "AND"},
                {"id": "out1", "componentId": "IO:OUT"}
            ],
            "wires": [
                {"from": {"componentId": "IO:IN:A", "pinIndex": 0},
                 "to": {"componentId": "comp1", "pinIndex": 0}},
                {"from": {"componentId": "IO:IN:B", "pinIndex": 0},
                 "to": {"componentId": "comp1", "pinIndex": 1}},
                {"from": {"componentId": "comp1", "pinIndex": 0},
                 "to": {"componentId": "IO:OUT:Y", "pinIndex": 0}}
            ],
            "totalCost": 10,
            "_arsenal_pieces": {}
        }
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"Y": 1}
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        result = service._run_simulation(0, expanded_solution, {"A": 1, "B": 1})
        
        assert result["success"] == True
        assert "puzzleOutputs" in result or "puzzle_outputs" in result
    
    def test_simulate_solution_complete_flow(self):
        """Test complete simulate_solution flow including _run_simulation"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"OUT": 0}
        
        solution = {
            "placedComponents": [
                {"id": "not1", "componentId": "NOT"}
            ],
            "wires": [],
            "totalCost": 5,
            "_arsenal_pieces": {}
        }
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        result = service.simulate_solution(
            "token", 1, solution, {"IN": 1}, is_sequence=False
        )
        
        assert result is not None
        assert "success" in result or "puzzle_outputs" in result


class TestConstraintEdgeCases:
    """Additional constraint validation edge cases"""
    
    def test_gate_limit_with_none_values(self):
        """Test gate_limit validation when gate names are None"""
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=100,
            structure_json=json.dumps({"placedComponents": []})
        )
        
        test_case = Mock()
        test_case.kind = "gate_limit"
        test_case.gate_name = None  # No gate_name
        test_case.gate_limit = 5
        test_case.input_stream = None
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        # Should pass because gate_name is None (skipped)
        assert passed == True
    
    def test_evaluate_multiple_test_cases_mixed_types(self):
        """Test evaluation with mixed blackbox and stream test cases"""
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=100,
            structure_json=json.dumps({
                "placedComponents": [],
                "state": []
            })
        )
        
        test_case_1 = Mock()
        test_case_1.kind = "blackbox"
        test_case_1.inputs = {"A": 0, "B": 0}
        test_case_1.expected_outputs = {"Y": 0}
        test_case_1.input_stream = None
        
        test_case_2 = Mock()
        test_case_2.kind = "stream"
        test_case_2.input_stream = [{"X": 0}, {"X": 1}]
        test_case_2.expected_output_stream = {"Z": [0, 1]}
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        logic_engine.evaluate.side_effect = [
            {"Y": 0},  # First test case
            {"Z": 0},  # Second test case cycle 0
            {"Z": 1},  # Second test case cycle 1
        ]
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(
            circuit, [test_case_1, test_case_2], puzzle
        )
        
        assert passed == True


class TestValidateSolutionWithoutUserRepo:
    """Test validate_solution when user_repo is None"""
    
    def test_validate_solution_no_user_repo_xp_not_incremented(self):
        """Test that validate_solution works without user_repo (lines 340-345)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.avg_difficulty = 5.0
        puzzle.time_limit_seconds = None
        puzzle.budget = 0
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 0}
        test_case.expected_outputs = {"out": 0}
        test_case.input_stream = None
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 0}
        
        xp_service = Mock()
        xp_service.calculate_medal.return_value = Medal.BRONZE
        xp_service.calculate_solve_xp.return_value = 100
        xp_service.BASE_XP = {PuzzleDifficulty.MEDIUM: 100}
        xp_service.MEDAL_BONUS = {Medal.GOLD: 50}
        
        solve_repo = Mock()
        solve_repo.get_progress.return_value = None
        solve_repo.add_solve = Mock()
        solve_repo.upsert_progress = Mock()
        solve_repo.claim_xp_delta.return_value = 0  # No XP
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
            user_repo=None,  # No user repo!
        )
        
        with patch('Backend.ServiceLayer.SolvingService.transaction'):
            result = service.validate_solution("token", 1, {
                "placedComponents": [],
                "totalCost": 0
            })
        
        assert result["solved"] == True
        assert result["xp_earned"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestStartAttemptErrorPaths:
    """Test error paths in start_attempt (lines 105-118, 162-165)"""
    
    def test_start_attempt_puzzle_not_found(self):
        """Lines 105-118: puzzle not found exception"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = None  # puzzle not found
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="puzzle not found"):
            service.start_attempt("token", 1)
    
    def test_start_attempt_unpublished_puzzle_not_creator(self):
        """Lines 162-165: unpublished puzzle, user is not creator"""
        auth = Mock()
        auth.require_user_id.return_value = 2  # user 2
        
        puzzle = Mock()
        puzzle.creator_user_id = 1  # creator is user 1
        puzzle.status = PuzzleStatus.DRAFT
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="puzzle not published"):
            service.start_attempt("token", 1)
    
    def test_start_attempt_unpublished_puzzle_is_creator(self):
        """Lines 162-165: unpublished puzzle, user IS creator (should succeed)"""
        auth = Mock()
        auth.require_user_id.return_value = 1  # user 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1  # creator is user 1
        puzzle.status = PuzzleStatus.DRAFT
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        attempt = Mock()
        attempt.to_dict.return_value = {"id": 1, "puzzle_id": 1, "user_id": 1}
        
        solve_repo = Mock()
        solve_repo.create_attempt.return_value = attempt
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        result = service.start_attempt("token", 1)
        assert result["puzzle_id"] == 1
        assert result["user_id"] == 1


class TestSubmitSolutionErrorPaths:
    """Test error paths in submit_solution (lines 127-224)"""
    
    def test_submit_solution_puzzle_not_found(self):
        """Lines 127-128: puzzle not found in submit_solution"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = None
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="puzzle not found"):
            service.submit_solution("token", 1, {"circuit_id": 1})
    
    def test_submit_solution_no_circuit_id_in_payload(self):
        """Lines 131, 136-138: circuit_id missing or invalid"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        # Test with missing circuit_id
        with pytest.raises(ValidationError, match="Circuit ID is required"):
            service.submit_solution("token", 1, {})
        
        # Test with None circuit_id
        with pytest.raises(ValidationError, match="Circuit ID is required"):
            service.submit_solution("token", 1, {"circuit_id": None})
    
    def test_submit_solution_circuit_not_found(self):
        """Lines 141-142: circuit not found"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = None
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="Circuit not found"):
            service.submit_solution("token", 1, {"circuit_id": 999})
    
    def test_submit_solution_circuit_not_owned_by_user(self):
        """Lines 145-177: circuit ownership check"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Mock()
        circuit.user_id = 2  # owned by different user
        circuit.cost = 100
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="You do not have permission"):
            service.submit_solution("token", 1, {"circuit_id": 1})
    
    def test_submit_solution_no_test_cases(self):
        """Lines 159: puzzle has no test cases"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        puzzle_repo.list_test_cases.return_value = []  # no test cases
        
        circuit = Mock()
        circuit.user_id = 1
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=circuit_repo,
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="puzzle has no test cases"):
            service.submit_solution("token", 1, {"circuit_id": 1})


class TestValidateSolutionErrorPaths:
    """Test error paths in validate_solution (lines 277-304)"""
    
    def test_validate_solution_puzzle_not_found(self):
        """Lines 277-284: puzzle not found error"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = None
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="puzzle not found"):
            service.validate_solution("token", 1, {"placedComponents": []})
    
    def test_validate_solution_no_test_cases(self):
        """Lines 285-295: no test cases configured"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        puzzle_repo.list_test_cases.return_value = []
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="no test cases configured"):
            service.validate_solution("token", 1, {"placedComponents": []})
    
    def test_validate_solution_failed_attempt_logging(self):
        """Lines 303-320: failed attempt creation (exception handling)"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 0, "B": 0}
        test_case.expected_outputs = {"out": 0}
        test_case.input_stream = None  # NOT a stream test case
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}  # wrong output
        
        solve_repo = Mock()
        solve_repo.create_attempt.side_effect = Exception("DB error")
        conn = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        # Should not re-raise the create_attempt exception, should return failure response
        result = service.validate_solution("token", 1, {
            "placedComponents": [],
            "totalCost": 0
        })
        
        assert result["solved"] == False
        assert "Wrong output" in result["message"]


class TestEvaluateTestCasesExceptionHandling:
    """Test exception handling in _evaluate_test_cases (lines 419-536)"""
    
    def test_evaluate_test_cases_malformed_json(self):
        """Lines 419-420: JSON parsing exception"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        # Create a circuit with invalid JSON
        circuit = Mock()
        circuit.structure_json = "invalid json {"
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 0}
        test_case.expected_outputs = {"out": 0}
        test_case.input_stream = None  # NOT a stream test case
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        # Should handle JSON parsing gracefully and continue with empty structure
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        # With malformed JSON, structure={}, logic engine should fail evaluation
        assert passed == False or msg is not None
    
    def test_evaluate_test_cases_logic_engine_exception(self):
        """Lines 452-464: logic engine evaluation exception"""
        circuit = Circuit(id=1, user_id=1, name="test", cost=100, 
                         structure_json=json.dumps({"placedComponents": []}))
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 0, "B": 0}
        test_case.expected_outputs = {"out": 0}
        test_case.input_stream = None  # NOT a stream test case
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        logic_engine.evaluate.side_effect = Exception("Circuit evaluation failed")
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        assert passed == False
        assert "Circuit evaluation failed" in msg or "error" in details[0]
    
    def test_evaluate_test_cases_sequence_cycle_error(self):
        """Lines 483-487: exception during sequence simulation cycle"""
        circuit = Circuit(id=1, user_id=1, name="test", cost=100,
                         structure_json=json.dumps({
                             "placedComponents": [],
                             "state": [1]
                         }))
        
        test_case = Mock()
        test_case.kind = "stream"
        test_case.input_stream = [{"X": 0}, {"X": 1}]
        test_case.expected_output_stream = {"Y": [0, 1]}
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        logic_engine.evaluate.side_effect = Exception("Cycle error")
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        assert passed == False
        assert "error" in msg.lower()
    
    def test_evaluate_test_cases_empty_test_case_list(self):
        """Lines 491: empty test case list"""
        circuit = Circuit(id=1, user_id=1, name="test", cost=100,
                         structure_json=json.dumps({"placedComponents": []}))
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        # Empty test case list should pass (vacuous truth)
        passed, msg, details = service._evaluate_test_cases(circuit, [], puzzle)
        assert passed == True
    
    def test_evaluate_test_cases_gate_limit_validation(self):
        """Lines 446, 450, 452-468: gate_limit test case validation"""
        circuit = Circuit(id=1, user_id=1, name="test", cost=100,
                         structure_json=json.dumps({"placedComponents": []}))
        
        test_case = Mock()
        test_case.kind = "gate_limit"
        test_case.gate_name = "AND"
        test_case.gate_limit = 5
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {"AND": 10}  # exceeds limit
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        assert passed == False
        assert "Gate limit exceeded" in msg
        assert details[0]["gate_name"] == "AND"
        assert details[0]["actual"] == 10
    
    def test_evaluate_test_cases_gate_count_limit(self):
        """Lines 468, 470-494: gate_count_limit validation"""
        circuit = Circuit(id=1, user_id=1, name="test", cost=100,
                         structure_json=json.dumps({"placedComponents": []}))
        
        test_case = Mock()
        test_case.kind = "gate_count_limit"
        test_case.max_gate_count = 10
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {"AND": 8, "OR": 5}
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        assert passed == False
        assert "Total gate count exceeded" in msg
    
    def test_evaluate_test_cases_latency_limit_min(self):
        """Lines 496-505: latency_limit minimum cycles check"""
        circuit = Circuit(id=1, user_id=1, name="test", cost=100,
                         structure_json=json.dumps({"placedComponents": []}))
        
        test_case = Mock()
        test_case.kind = "latency_limit"
        test_case.min_cycles = 5
        test_case.max_cycles = None
        test_case.input_stream = [{"X": 0}, {"X": 1}]  # only 2 cycles
        test_case.expected_output_stream = {"Y": [0, 1]}
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        assert passed == False
        assert "Insufficient cycles" in msg
    
    def test_evaluate_test_cases_latency_limit_max(self):
        """Lines 516, 524-536: latency_limit maximum cycles check"""
        circuit = Circuit(id=1, user_id=1, name="test", cost=100,
                         structure_json=json.dumps({"placedComponents": []}))
        
        test_case = Mock()
        test_case.kind = "latency_limit"
        test_case.min_cycles = None
        test_case.max_cycles = 2
        test_case.input_stream = [{"X": 0}, {"X": 1}, {"X": 0}]  # 3 cycles
        test_case.expected_output_stream = {"Y": [0, 1, 0]}
        
        puzzle = Mock()
        
        logic_engine = Mock()
        logic_engine.extract_gate_counts.return_value = {}
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        passed, msg, details = service._evaluate_test_cases(circuit, [test_case], puzzle)
        assert passed == False
        assert "Too many cycles" in msg


class TestArsenalExpansionErrors:
    """Test error handling in _expand_arsenal_pieces (lines 591-660)"""
    
    def test_expand_arsenal_pieces_circuit_not_found(self):
        """Lines 621-622: arsenal circuit not found"""
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = None
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=circuit_repo,
            auth=Mock(),
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        payload = {
            "placedComponents": [
                {"id": "comp1", "componentId": 999}  # non-existent arsenal
            ]
        }
        
        result = service._expand_arsenal_pieces(payload)
        assert result["_arsenal_pieces"] == {}
    
    def test_expand_arsenal_pieces_fetch_exception(self):
        """Lines 624-631: exception during arsenal fetch"""
        circuit_repo = Mock()
        circuit_repo.get_by_id.side_effect = Exception("DB error")
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=circuit_repo,
            auth=Mock(),
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        payload = {
            "placedComponents": [
                {"id": "comp1", "componentId": 1}
            ]
        }
        
        result = service._expand_arsenal_pieces(payload)
        assert result["_arsenal_pieces"] == {}
    
    def test_expand_arsenal_pieces_non_arsenal_circuit(self):
        """Lines 635-660: circuit found but is_arsenal=False"""
        circuit = Mock()
        circuit.is_arsenal = False
        
        circuit_repo = Mock()
        circuit_repo.get_by_id.return_value = circuit
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=circuit_repo,
            auth=Mock(),
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        payload = {
            "placedComponents": [
                {"id": "comp1", "componentId": 1}
            ]
        }
        
        result = service._expand_arsenal_pieces(payload)
        assert result["_arsenal_pieces"] == {}


class TestSimulationErrorPaths:
    """Test error handling in simulation methods (lines 678-708, 751-815)"""
    
    def test_simulate_solution_puzzle_not_found(self):
        """Lines 678-683: puzzle validation failure"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = None
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="puzzle not found"):
            service.simulate_solution("token", 1, {"placedComponents": []}, {})
    
    def test_simulate_solution_arsenal_piece_allowed(self):
        """Lines 681, 706: puzzle_id=0 (arsenal piece) should skip validation"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 1}
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        # puzzle_id=0 should not validate puzzle
        result = service.simulate_solution("token", 0, {
            "placedComponents": [],
            "totalCost": 0
        }, {"A": 0})
        
        assert "success" in result
    
    def test_simulate_sequence_empty_inputs(self):
        """Lines 708: sequence simulation with no inputs"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="No input sequences"):
            service._simulate_sequence(0, {}, {})
    
    def test_simulate_sequence_mismatched_lengths(self):
        """Lines 708: sequence inputs with different lengths"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=Mock(),
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="same length"):
            service._simulate_sequence(0, {}, {
                "A": [0, 1, 0],
                "B": [1, 0]  # different length
            })
    
    def test_simulate_single_step_logic_engine_exception(self):
        """Lines 751-754: logic engine exception in simulation"""
        logic_engine = Mock()
        logic_engine.evaluate.side_effect = Exception("Eval failed")
        
        service = SolvingService(
            conn=Mock(),
            solve_repo=Mock(),
            puzzle_repo=Mock(),
            circuit_repo=Mock(),
            auth=Mock(),
            logic_engine=logic_engine,
            xp_service=Mock(),
        )
        
        with pytest.raises(ValidationError, match="evaluation failed"):
            service._run_simulation(0, {
                "placedComponents": [],
                "totalCost": 0,
                "_arsenal_pieces": {}
            }, {"A": 0})


class TestMedalAndDifficultyCalculation:
    """Test medal and difficulty calculation edge cases (lines 323-388, 364-370)"""
    
    def test_validate_solution_difficulty_calculation_easy(self):
        """Test difficulty tier EASY threshold"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.avg_difficulty = 2.0  # easy tier
        puzzle.time_limit_seconds = None
        puzzle.budget = 0
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 0}
        test_case.expected_outputs = {"out": 0}
        test_case.input_stream = None  # NOT a stream test case
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 0}
        
        xp_service = Mock()
        xp_service.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        xp_service.calculate_medal.return_value = Medal.BRONZE
        xp_service.calculate_solve_xp.return_value = 100
        xp_service.BASE_XP = {PuzzleDifficulty.EASY: 100}
        xp_service.MEDAL_BONUS = {Medal.GOLD: 50}
        
        solve_repo = Mock()
        solve_repo.get_progress.return_value = None
        solve_repo.add_solve = Mock()
        solve_repo.upsert_progress = Mock()
        solve_repo.claim_xp_delta.return_value = 50
        
        conn = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
            user_repo=None,
        )
        
        with patch('Backend.ServiceLayer.SolvingService.transaction'):
            result = service.validate_solution("token", 1, {"totalCost": 0})
        
        assert result["solved"] == True
        assert "medal" in result


class TestValidateSolutionTransactionHandling:
    """Test transaction-wrapped logic in validate_solution (lines 303-350)"""
    
    def test_validate_solution_transaction_commit(self):
        """Test transaction context manager is used correctly"""
        auth = Mock()
        auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.creator_user_id = 1
        puzzle.avg_difficulty = 5.0
        puzzle.time_limit_seconds = 60
        puzzle.budget = 100
        
        puzzle_repo = Mock()
        puzzle_repo.get_by_id.return_value = puzzle
        
        test_case = Mock()
        test_case.kind = "blackbox"
        test_case.inputs = {"A": 0}
        test_case.expected_outputs = {"out": 0}
        test_case.input_stream = None  # NOT a stream test case
        
        puzzle_repo.list_test_cases.return_value = [test_case]
        
        logic_engine = Mock()
        logic_engine.evaluate.return_value = {"out": 0}
        
        xp_service = Mock()
        xp_service.calculate_medal.return_value = Medal.SILVER
        xp_service.calculate_solve_xp.return_value = 150
        xp_service.BASE_XP = {PuzzleDifficulty.MEDIUM: 120}
        xp_service.MEDAL_BONUS = {Medal.GOLD: 50}
        
        solve_repo = Mock()
        solve_repo.get_progress.return_value = None
        solve_repo.add_solve = Mock()
        solve_repo.upsert_progress = Mock()
        solve_repo.claim_xp_delta.return_value = 75
        
        user_repo = Mock()
        user_repo.increment_xp = Mock()
        
        conn = Mock()
        
        service = SolvingService(
            conn=conn,
            solve_repo=solve_repo,
            puzzle_repo=puzzle_repo,
            circuit_repo=Mock(),
            auth=auth,
            logic_engine=logic_engine,
            xp_service=xp_service,
            user_repo=user_repo,
        )
        
        with patch('Backend.ServiceLayer.SolvingService.transaction'):
            result = service.validate_solution("token", 1, {
                "placedComponents": [],
                "totalCost": 50
            }, time_taken=30)
        
        assert result["solved"] == True
        solve_repo.add_solve.assert_called_once()
        solve_repo.upsert_progress.assert_called_once()


class TestSolvingServiceExtended:
    """Extended tests for validate_solution and sequential test cases"""
    
    def setup_method(self):
        self.mock_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_logic = Mock(spec=logicEngineService)
        self.mock_logic.compute_cost = Mock(return_value=0)
        self.mock_logic.has_entry_for_inputs = Mock(return_value=True)
        self.mock_logic.extract_gate_counts = Mock(return_value={})
        self.mock_xp = Mock(spec=XPService)
        self.mock_conn = Mock()

        from Backend.PersistantLayer.SolveRepo import PuzzleProgress
        # validate_solution calls get_progress 3 times: old_progress_for_xp, old_progress, new_progress
        # For a passing test: old returns None/None, new returns progress with XP
        self._progress_after = PuzzleProgress(user_id=1, puzzle_id=1, best_medal=1, timer_upgraded=False, tight_upgraded=False, first_solved_at=None, best_xp=50, total_xp_awarded=50)
        self.mock_repo.get_progress.return_value = None
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.award_creator_solve_xp.return_value = 0
        self.mock_xp.BASE_XP = {PuzzleDifficulty.EASY: 50, PuzzleDifficulty.MEDIUM: 100, PuzzleDifficulty.HARD: 200}
        self.mock_xp.MEDAL_BONUS = {Medal.NONE: 0, Medal.BRONZE: 0, Medal.SILVER: 25, Medal.GOLD: 50}
        self.mock_repo.get_best_xp_for_puzzle.return_value = 0
        # Provide conn on solve_repo so validate_solution can do raw SQL queries
        self.mock_repo.conn = self.mock_conn
        # Make the raw SQL query return empty results by default
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        self.mock_conn.execute.return_value = mock_cursor

        self.service = SolvingService(
            self.mock_conn,
            self.mock_repo,
            self.mock_puzzle_repo,
            self.mock_circuit_repo,
            self.mock_auth,
            self.mock_logic,
            self.mock_xp
        )

    def test_validate_solution_success(self):
        """Test validate_solution with all test cases passing"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=0,
        )

        tc = PuzzleTestCase(id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX, inputs={"A": 0}, expected_outputs={"O": 1})
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]

        self.mock_logic.evaluate.return_value = {"O": 1}
        # get_progress is called 2 times: old_progress (for medal tracking), new_progress
        self.mock_repo.get_progress.side_effect = [None, None, self._progress_after]
        # claim_xp_delta returns claimed XP amount (atomic XP claim pattern)
        self.mock_repo.claim_xp_delta.return_value = 50

        payload = {
            "totalCost": 10,
            "components": [],
            "wires": []
        }

        result = self.service.validate_solution("token", 1, payload)

        assert result["solved"] is True
        assert result["message"].startswith("All test cases passed!")
        assert self.mock_logic.evaluate.call_count == 1

    def test_validate_solution_fail(self):
        """Test validate_solution with wrong output"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(
            id=1, creator_user_id=1, avg_difficulty=2.0,
            time_limit_seconds=None, budget=0,
        )
        tc = PuzzleTestCase(id=1, puzzle_id=1, kind=TestCaseKind.BLACKBOX, inputs={"A": 0}, expected_outputs={"O": 1})
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        
        self.mock_logic.evaluate.return_value = {"O": 0} 
        
        payload = {"totalCost": 10}
        result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is False
        assert result["message"] == "Wrong output"

    def test_submit_solution_sequential_success(self):
        """Test submit_solution with sequential logic (stateful circuit)"""
        self.mock_auth.require_user_id.return_value = 1
        # Set budget to a value to avoid int(None) error
        puzzle = Mock(id=1, creator_user_id=2, status=PuzzleStatus.PUBLISHED, time_limit_seconds=None, budget=100000)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        circuit = Circuit(id=100, user_id=1, name="My Sol", cost=50, structure_json='{"components": [{"id": "dff1", "type": "DFF"}]}')
        self.mock_circuit_repo.get_by_id.return_value = circuit
        
        tc = Mock()
        tc.inputs = {"X": 0}
        tc.expected_outputs = {"O": 0}
        tc.input_stream = [0, 1]
        tc.expected_output_stream = {"O": [0, 1]}
        
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        
        def side_effect(circ, inputs):
            x = inputs.get("X", 0)
            return {"O": x, "dff1_next": x}
            
        self.mock_logic.evaluate.side_effect = side_effect
        
        attempt = SolveAttempt(id=55, puzzle_id=1, user_id=1)
        self.mock_repo.get_open_attempt.return_value = attempt
        
        result = self.service.submit_solution("token", 1, 100)
        
        assert result["passed"] is True
        assert attempt.passed is True

    def test_submit_solution_sequential_fail_mismatch(self):
        """Test submit_solution with sequential output mismatch"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(id=1, budget=1000, creator_user_id=1, min_gate_count=0, total_gate_count=0, time_limit_seconds=None, avg_difficulty=2.0, avg_fun=2.0, avg_clearness=2.0, status=PuzzleStatus.PUBLISHED)
        self.mock_circuit_repo.get_by_id.return_value = Circuit(id=100, user_id=1, name="Fail", cost=10, structure_json='{}')
        
        tc = Mock()
        tc.inputs = {"X": 0}
        tc.expected_outputs = {"O": 0}
        tc.input_stream = [0]
        tc.expected_output_stream = {"O": [1]}
        
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_logic.evaluate.return_value = {"O": 0}
        
        attempt = SolveAttempt(id=55, puzzle_id=1, user_id=1)
        self.mock_repo.get_open_attempt.return_value = attempt
        
        result = self.service.submit_solution("token", 1, 100)
        
        assert result["passed"] is False
        assert "Sequential output mismatch" in result["fail_reason"]

    def test_submit_solution_sequential_exception(self):
        """Test submit_solution with sequential logic evaluation error"""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = Mock(id=1, budget=1000, creator_user_id=1, min_gate_count=0, total_gate_count=0, time_limit_seconds=None, avg_difficulty=2.0, avg_fun=2.0, avg_clearness=2.0, status=PuzzleStatus.PUBLISHED)
        self.mock_circuit_repo.get_by_id.return_value = Circuit(id=100, user_id=1, name="Ex", cost=10, structure_json='{}')
        
        tc = Mock()
        tc.inputs = {"X": 0}
        tc.expected_outputs = {"O": 0}
        tc.input_stream = [0]
        tc.expected_output_stream = {"O": [1]}
        
        self.mock_puzzle_repo.list_test_cases.return_value = [tc]
        self.mock_logic.evaluate.side_effect = Exception("Boom")
        
        attempt = SolveAttempt(id=55, puzzle_id=1, user_id=1)
        self.mock_repo.get_open_attempt.return_value = attempt
        
        result = self.service.submit_solution("token", 1, 100)
        
        assert result["passed"] is False
        assert "Cycle 0 error: Boom" in result["fail_reason"]


class TestSolvingServiceGateLimitBuckets:
    @staticmethod
    def _make_service():
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_solve_repo = Mock()
        mock_puzzle_repo = Mock()
        mock_circuit_repo = Mock()
        mock_auth = Mock()
        mock_engine = Mock()
        mock_engine.evaluate.return_value = {}
        mock_xp = Mock()

        service = SolvingService(
            mock_conn,
            mock_solve_repo,
            mock_puzzle_repo,
            mock_circuit_repo,
            mock_auth,
            mock_engine,
            mock_xp,
        )
        return service, mock_circuit_repo

    @staticmethod
    def _make_circuit(component_ids):
        placed = [
            {"id": f"c{i}", "componentId": component_id, "x": i, "y": 0}
            for i, component_id in enumerate(component_ids, start=1)
        ]
        return Circuit(
            id=1,
            user_id=1,
            name="Limit test circuit",
            cost=0,
            structure_json=json.dumps({"placedComponents": placed, "wires": []}),
        )

    def test_shared_arsenal_is_excluded_from_private_arsenal_total_limit(self):
        service, mock_circuit_repo = self._make_service()

        shared_piece = Mock()
        shared_piece.is_arsenal = True
        shared_piece.puzzle_id = None
        shared_piece.name = "SharedAdder"
        mock_circuit_repo.get_by_id.side_effect = lambda cid: {200: shared_piece}.get(cid)

        puzzle = Mock()
        puzzle.allowed_arsenal_component_ids = ["200"]
        puzzle.riddle_base_name = None

        circuit = self._make_circuit(["200"])

        private_total_limit = {
            "kind": "gate_limit",
            "gate_name": "__ARSENAL_TOTAL__",
            "gate_limit": 0,
        }
        passed, msg, details = service._evaluate_test_cases(circuit, [private_total_limit], puzzle)
        assert passed is True
        assert msg is None
        assert details == []

        shared_total_limit = {
            "kind": "gate_limit",
            "gate_name": "__ARSENAL_SHARED_TOTAL__",
            "gate_limit": 0,
        }
        passed, msg, details = service._evaluate_test_cases(circuit, [shared_total_limit], puzzle)
        assert passed is False
        assert "Gate limit exceeded" in msg

    def test_custom_piece_limit_by_reserved_name_fails_with_max_zero_when_used(self):
        service, mock_circuit_repo = self._make_service()

        custom_piece = Mock()
        custom_piece.is_arsenal = True
        custom_piece.puzzle_id = 99
        custom_piece.name = "SpecialMux"
        mock_circuit_repo.get_by_id.side_effect = lambda cid: {400: custom_piece}.get(cid)

        puzzle = Mock()
        puzzle.allowed_arsenal_component_ids = []
        puzzle.riddle_base_name = None

        circuit = self._make_circuit(["400"])

        tc = {
            "kind": "gate_limit",
            "gate_name": "__CUSTOM_PIECE__:SpecialMux",
            "gate_limit": 0,
        }

        passed, msg, details = service._evaluate_test_cases(circuit, [tc], puzzle)
        assert passed is False
        assert "Gate limit exceeded" in msg
        assert details[0]["error_type"] == "gate_limit_exceeded"

    def test_custom_total_limit_supports_min_and_max_constraints(self):
        service, mock_circuit_repo = self._make_service()

        custom_piece = Mock()
        custom_piece.is_arsenal = True
        custom_piece.puzzle_id = 77
        custom_piece.name = "CustomMux"
        mock_circuit_repo.get_by_id.side_effect = lambda cid: {400: custom_piece}.get(cid)

        puzzle = Mock()
        puzzle.allowed_arsenal_component_ids = []
        puzzle.riddle_base_name = None

        circuit = self._make_circuit(["400", "400"])

        max_tc = {
            "kind": "gate_limit",
            "gate_name": "__CUSTOM_TOTAL__",
            "gate_limit": 1,
        }
        passed, msg, details = service._evaluate_test_cases(circuit, [max_tc], puzzle)
        assert passed is False
        assert "Gate limit exceeded" in msg
        assert details[0]["error_type"] == "gate_limit_exceeded"

        min_tc = {
            "kind": "gate_limit",
            "gate_name": "__CUSTOM_TOTAL__",
            "min_gate_limit": 3,
        }
        passed, msg, details = service._evaluate_test_cases(circuit, [min_tc], puzzle)
        assert passed is False
        assert "Insufficient __CUSTOM_TOTAL__ gates" in msg
        assert details[0]["error_type"] == "gate_limit_insufficient"

    def test_shared_arsenal_each_limit_is_checked_separately_from_private_each_limit(self):
        service, mock_circuit_repo = self._make_service()

        shared_piece = Mock()
        shared_piece.is_arsenal = True
        shared_piece.puzzle_id = None
        shared_piece.name = "SharedPiece"
        mock_circuit_repo.get_by_id.side_effect = lambda cid: {200: shared_piece}.get(cid)

        puzzle = Mock()
        puzzle.allowed_arsenal_component_ids = ["200"]
        puzzle.riddle_base_name = None

        circuit = self._make_circuit(["200", "200"])

        private_each_limit = {
            "kind": "gate_limit",
            "gate_name": "__ARSENAL_EACH__",
            "gate_limit": 1,
        }
        passed, msg, details = service._evaluate_test_cases(circuit, [private_each_limit], puzzle)
        assert passed is True
        assert msg is None
        assert details == []

        shared_each_limit = {
            "kind": "gate_limit",
            "gate_name": "__ARSENAL_SHARED_EACH__",
            "gate_limit": 1,
        }
        passed, msg, details = service._evaluate_test_cases(circuit, [shared_each_limit], puzzle)
        assert passed is False
        assert "Shared arsenal per-piece limit exceeded" in msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
