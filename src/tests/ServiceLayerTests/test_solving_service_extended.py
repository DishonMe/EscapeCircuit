import pytest
import json
from unittest.mock import Mock, MagicMock
from Backend.ServiceLayer.SolvingService import SolvingService
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.PuzzleTestCase import PuzzleTestCase
from Backend.DomainLayer.SolveAttempt import SolveAttempt
from Backend.DomainLayer.Enums import PuzzleStatus, TestCaseKind, Medal, PuzzleDifficulty
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService
from Backend.ServiceLayer.logicEngineService import logicEngineService

class TestSolvingServiceExtended:
    def setup_method(self):
        self.mock_repo = Mock(spec=SolveRepo)
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_logic = Mock(spec=logicEngineService)
        self.mock_xp = Mock(spec=XPService)
        self.mock_conn = Mock()
        
        self.mock_repo.get_progress.return_value = None
        self.mock_xp.tier_from_avg_difficulty.return_value = PuzzleDifficulty.EASY
        self.mock_xp.calculate_medal.return_value = Medal.BRONZE
        self.mock_xp.calculate_solve_xp.return_value = 50
        self.mock_xp.award_creator_solve_xp.return_value = 0
        self.mock_repo.get_best_xp_for_puzzle.return_value = 0
        
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
        
        payload = {
            "totalCost": 10,
            "components": [],
            "wires": []
        }
        
        result = self.service.validate_solution("token", 1, payload)
        
        assert result["solved"] is True
        assert result["message"] == "All test cases passed!"
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
        self.mock_puzzle_repo.get_by_id.return_value = Mock(id=1, budget=1000)
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
        self.mock_puzzle_repo.get_by_id.return_value = Mock(id=1, budget=1000)
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
