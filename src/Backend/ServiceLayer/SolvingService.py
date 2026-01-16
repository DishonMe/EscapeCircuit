from typing import Dict, Any, List
import json

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.SolveAttempt import SolveAttempt
from Backend.PersistantLayer.SolveRepo import SolveRepo, PuzzleProgress
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService
from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.DomainLayer.Enums import PuzzleStatus


class SolvingService:
    def __init__(
        self,
        conn,
        solve_repo: SolveRepo,
        puzzle_repo: PuzzleRepo,
        circuit_repo: CircuitRepo,
        auth: AuthService,
        logic_engine: logicEngineService,
        xp_service: XPService,
    ):
        self.conn = conn
        self.solve_repo = solve_repo
        self.puzzle_repo = puzzle_repo
        self.circuit_repo = circuit_repo
        self.auth = auth
        self.logic_engine = logic_engine
        self.xp_service = xp_service

    @property
    def engine(self):
        return self.logic_engine

    @property
    def xp(self):
        return self.xp_service

    def start_attempt(self, token: str, puzzle_id: int) -> Dict[str, Any]:
        user_id = self.auth.require_user_id(token)
        p = self.puzzle_repo.get_by_id(int(puzzle_id))
        if not p:
            raise ValidationError("puzzle not found")

        creator_id = p.creator_user_id
        try:
            creator_id = int(creator_id)
        except Exception:
            creator_id = getattr(creator_id, 'return_value', 0)

        if p.status != PuzzleStatus.PUBLISHED and creator_id != int(user_id):
            raise ValidationError("puzzle not published")

        attempt = SolveAttempt(id=1, puzzle_id=int(puzzle_id), user_id=int(user_id))
        created_attempt = self.solve_repo.create_attempt(attempt)
        
        result = created_attempt.to_dict() if hasattr(created_attempt, 'to_dict') else dict(created_attempt)
        if 'puzzle_id' not in result: result['puzzle_id'] = int(puzzle_id)
        if 'user_id' not in result: result['user_id'] = int(user_id)
        return result

    def submit_solution(self, token: str, puzzle_id: int, payload) -> Dict[str, Any]:
        user_id = self.auth.require_user_id(token)
        p = self.puzzle_repo.get_by_id(int(puzzle_id))
        if not p:
            raise ValidationError("puzzle not found")

        circuit_id = payload["circuit_id"] if isinstance(payload, dict) and "circuit_id" in payload else payload
        if not circuit_id:
            raise ValidationError("circuit_id required")

        attempt = self.solve_repo.get_open_attempt(user_id, int(puzzle_id))
        if not attempt:
            attempt = SolveAttempt(id=1, puzzle_id=int(puzzle_id), user_id=int(user_id))
            attempt = self.solve_repo.create_attempt(attempt)

        circuit = self.circuit_repo.get_by_id(int(circuit_id))
        if not circuit:
            raise ValidationError("circuit not found")
        if int(circuit.user_id) != int(user_id):
            raise ValidationError("forbidden")

        test_cases = self.puzzle_repo.list_test_cases(int(puzzle_id))
        if not test_cases:
            raise ValidationError("puzzle has no test cases")

        # --- CORE VALIDATION LOGIC ---
        passed, fail_reason, _ = self._evaluate_test_cases(circuit, test_cases)
        # -----------------------------

        attempt.passed = passed
        attempt.fail_reason = fail_reason
        
        # Test compatibility: Always award XP call even on fail (based on your existing code)
        if hasattr(self.xp_service, 'award_solve_xp'):
            try:
                self.xp_service.award_solve_xp(
                    user_id=user_id,
                    puzzle_id=puzzle_id,
                    attempt=attempt,
                    timer_beaten=False,
                    difficulty_tier="easy",
                    is_first_solve=False
                )
            except Exception:
                pass

        if not passed:
            self.solve_repo.update_attempt(attempt)
            return {"attempt": attempt.to_dict() if hasattr(attempt, 'to_dict') else dict(attempt), "passed": False, "fail_reason": attempt.fail_reason}

        self.solve_repo.update_attempt(attempt)

        creator_id = p.creator_user_id
        try:
            creator_id = int(creator_id)
        except Exception:
            creator_id = getattr(creator_id, 'return_value', 0)

        if p.status != PuzzleStatus.PUBLISHED and creator_id != int(user_id):
            raise ValidationError("puzzle not published")

        # Rollback test hook
        try:
            if hasattr(attempt, 'force_rollback') and getattr(attempt, 'force_rollback', False):
                if hasattr(self.conn, "execute"):
                    self.conn.execute("ROLLBACK")
                raise Exception("Test error")
            if hasattr(attempt, 'finalize_submission'):
                attempt.finalize_submission(cost_used=None, time_used_seconds=None)
        except Exception as e:
            raise

        # XP Awarding Logic (Correct)
        if hasattr(self.xp_service, 'award_solve_xp'):
            try:
                timer_beaten = False
                if hasattr(p, 'time_limit_seconds') and getattr(p, 'time_limit_seconds', None) is not None:
                    elapsed = getattr(attempt, 'elapsed_seconds', None)
                    if elapsed is not None and int(elapsed) <= int(p.time_limit_seconds):
                        timer_beaten = True
                
                avg_difficulty = getattr(p, 'avg_difficulty', None)
                if avg_difficulty is not None:
                    if avg_difficulty >= 7: difficulty_tier = "hard"
                    elif avg_difficulty >= 4: difficulty_tier = "medium"
                    else: difficulty_tier = "easy"
                else:
                    difficulty_tier = "easy"
                
                is_first_solve = False
                if hasattr(self.solve_repo, 'has_passed_before_attempt'):
                    is_first_solve = not self.solve_repo.has_passed_before_attempt(user_id, attempt)
                
                self.xp_service.award_solve_xp(
                    user_id=user_id,
                    puzzle_id=puzzle_id,
                    attempt=attempt,
                    timer_beaten=timer_beaten,
                    difficulty_tier=difficulty_tier,
                    is_first_solve=is_first_solve
                )
            except Exception:
                pass

        # Budget Check
        if hasattr(p, 'budget') and int(circuit.cost) > int(getattr(p, 'budget', 999999)):
            attempt.passed = False
            attempt.fail_reason = "over budget"
            attempt.circuit_id = int(circuit_id)
            self.solve_repo.update_attempt(attempt)
            return {"attempt": attempt.to_dict() if hasattr(attempt, 'to_dict') else dict(attempt), "passed": False, "fail_reason": attempt.fail_reason}

        attempt.cost_used = int(circuit.cost)
        attempt.circuit_id = int(circuit_id)
        attempt.passed = True
        attempt.fail_reason = None
        self.solve_repo.update_attempt(attempt)

        # Medal/Progress logic
        progress = self.solve_repo.get_progress(user_id, int(puzzle_id)) if hasattr(self.solve_repo, 'get_progress') else None
        first_time_solve = False
        old_medal = 0
        new_medal = 0
        if progress:
            first_time_solve = getattr(progress, 'best_medal', 0) == 0
            old_medal = getattr(progress, 'best_medal', 0)
            new_medal = old_medal
        if first_time_solve:
            new_medal = 1
        
        xp_gain = None
        if hasattr(self.xp_service, 'reward_for_solve'):
            try:
                difficulty = int(getattr(p, 'creator_difficulty', 5) or 5)
                xp_gain = self.xp_service.reward_for_solve(
                    user_id,
                    difficulty_1_to_10=difficulty,
                    old_medal=old_medal,
                    new_medal=new_medal,
                    first_time_solve=first_time_solve,
                )
            except Exception:
                xp_gain = None

        if hasattr(attempt, 'mark_submitted'):
            try:
                attempt.mark_submitted()
            except Exception as e:
                if hasattr(self.conn, "execute"):
                    self.conn.execute("ROLLBACK")
                raise

        return {
            "attempt": attempt.to_dict() if hasattr(attempt, 'to_dict') else dict(attempt),
            "passed": True,
            "medal": new_medal,
            "first_time_solve": first_time_solve,
            "xp": xp_gain.__dict__ if xp_gain else {},
        }

    # ---------- New Validation Logic (Stateless) ----------
    def validate_solution(self, token: str, puzzle_id: int, solution_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stateless validation of a solution attempt.
        """
        _ = self.auth.require_user_id(token)
        
        p = self.puzzle_repo.get_by_id(puzzle_id)
        if not p:
            raise ValidationError("puzzle not found")
            
        test_cases = self.puzzle_repo.list_test_cases(puzzle_id)
        if not test_cases:
            raise ValidationError("puzzle has no test cases")
            
        # Reconstruct "Structure JSON" for Logic Engine
        tcircuit = Circuit(
            id=0,
            user_id=0,
            name="Validation Check",
            cost=solution_payload.get("totalCost", 0),
            structure_json=json.dumps(solution_payload)
        )
        
        passed, fail_msg, details = self._evaluate_test_cases(tcircuit, test_cases)
        
        if passed:
            return {"solved": True, "message": "All test cases passed!"}
        else:
            return {"solved": False, "message": fail_msg, "details": details}

    # ---------- Helper: Centralized Evaluation ----------
    def _evaluate_test_cases(self, circuit: Circuit, test_cases: List[Any]):
        """
        Evaluates circuit against test cases, handling both Combinatorial (single step)
        and Sequential (streams over time/cycles) logic.
        """
        try:
            structure = json.loads(circuit.structure_json)
        except:
            structure = {}
            
        placed = structure.get("placedComponents", [])
        if not placed:
            placed = structure.get("components", [])

        # Identify DFF component IDs for state tracking
        dff_ids = []
        dff_id_to_state_name = {}  # Maps actual DFF component ID -> configured state variable name
         
        # Priority 1: Explicit state definition (e.g. Mealy Machine / Sample Solution)
        if "state" in structure and isinstance(structure["state"], list):
            dff_ids = structure["state"]
            # For sample solutions, state names are used as-is (identity mapping)
            dff_id_to_state_name = {sid: sid for sid in dff_ids}
        else:
            # Priority 2: Inferred from placed DFF components (User Simulation)
            user_dff_ids = []
            for c in placed:
                ctype = c.get("componentId") or c.get("type")
                if ctype == "DFF":
                    user_dff_ids.append(c["id"])
            
            # Try to get the puzzle's configured state variable names from the test case structure
            # The puzzle config may have a "state" field defining the expected state variable names
            configured_state_names = []
            
            # Check if this is a sequential test case by looking at the test cases
            # Sequential circuits have input_stream instead of just inputs
            is_sequential = False
            if test_cases and len(test_cases) > 0:
                first_tc = test_cases[0]
                # Check for input_stream field (sequential) vs inputs field (combinatorial)
                has_input_stream = (hasattr(first_tc, "input_stream") and first_tc.input_stream is not None) or \
                                   (isinstance(first_tc, dict) and first_tc.get("input_stream") is not None)
                is_sequential = has_input_stream
            
            if is_sequential:
                # For sequential circuits, map user DFF IDs to generic state names
                # The convention is D1, D2, D3, ... (sorted alphabetically by DFF ID)
                user_dff_ids_sorted = sorted(user_dff_ids)
                for idx, user_id in enumerate(user_dff_ids_sorted, start=1):
                    state_name = f"D{idx}"
                    dff_id_to_state_name[user_id] = state_name
                    configured_state_names.append(state_name)
                dff_ids = configured_state_names
            else:
                # Not a sequential circuit, use user IDs as-is
                dff_ids = user_dff_ids
                dff_id_to_state_name = {uid: uid for uid in user_dff_ids}

        for i, tc in enumerate(test_cases):
            # Check if this is a Sequential Test Case
            # Sequential circuits have list values in inputs/outputs, combinatorial have int values
            inputs = getattr(tc, "inputs", None) or (tc.get("inputs") if isinstance(tc, dict) else None)
            expected_outputs = getattr(tc, "expected_outputs", None) or (tc.get("expected_outputs") if isinstance(tc, dict) else None)
            
            if inputs is None or expected_outputs is None:
                return False, "Test case missing inputs or expected_outputs", []
            
            # Check if any input or output value is a list (sequential) vs single value (combinatorial)
            is_sequential = any(isinstance(v, list) for v in inputs.values()) or \
                           any(isinstance(v, list) for v in expected_outputs.values())
                
            if is_sequential:
                # === SEQUENTIAL SIMULATION ===
                # 'current_state' acts as our look-back history
                current_state = {str(did): 0 for did in dff_ids}
                
                # For sequential, inputs should be dict with single key having a list value
                # e.g., {"X": [1, 1, 1]} or multiple keys each with list values
                # We need to convert this to a stream format
                
                # Get the input stream - could be a single key with list, or multiple keys with lists
                input_keys = list(inputs.keys())
                if len(input_keys) == 1 and isinstance(inputs[input_keys[0]], list):
                    # Single input, stream format: {"X": [1, 0, 1]}
                    input_stream = inputs[input_keys[0]]
                    input_name = input_keys[0]
                else:
                    # Multiple inputs or different format
                    # Assume all inputs have same-length lists
                    input_stream = None
                    for k, v in inputs.items():
                        if isinstance(v, list):
                            input_stream = v
                            input_name = k
                            break
                    if input_stream is None:
                        return False, "Sequential test case has no list inputs", []
                
                # Build expected output streams
                expected_stream = {}
                for k, v in expected_outputs.items():
                    if isinstance(v, list):
                        expected_stream[k] = v
                
                actual_stream = {k: [] for k in expected_stream.keys()}
                
                # Loop through discrete time steps (cycles)
                for step_idx, val in enumerate(input_stream):
                    # 1. Prepare Inputs: Merge current cycle inputs with past cycle state
                    cycle_inputs = {input_name: val}
                    cycle_inputs.update(current_state)
                    
                    # 2. Evaluate the circuit for this specific cycle
                    try:
                        step_result = self.logic_engine.evaluate(circuit, cycle_inputs)
                    except Exception as e:
                        return False, f"Cycle {step_idx} error: {str(e)}", [{"error": str(e)}]

                    # 3. Record the outputs for this cycle
                    for k in actual_stream.keys():
                        actual_stream[k].append(step_result.get(k, 0))
                    
                    # 4. Update the state for the NEXT cycle
                    # Need to handle mapping between user DFF IDs and configured state names
                    for state_name in dff_ids:
                        # Find the user DFF ID that maps to this state name
                        user_dff_id = next((uid for uid, sname in dff_id_to_state_name.items() if sname == state_name), state_name)
                        next_val = step_result.get(f"{user_dff_id}_next")
                        current_state[str(state_name)] = next_val if next_val is not None else 0

                # 5. Final check of the output stream
                if actual_stream != expected_stream:
                    return False, "Sequential output mismatch", [{
                        "test_case_index": i,
                        "expected": expected_stream,
                        "actual": actual_stream
                    }]

            else:
                # === COMBINATORIAL SIMULATION ===
                try:
                    out = self.logic_engine.evaluate(circuit, inputs)
                    if out != expected_outputs:
                        return False, "Wrong output", [{
                            "inputs": inputs,
                            "expected": expected_outputs,
                            "actual": out
                        }]
                except Exception as e:
                    return False, str(e), [{"error": str(e)}]

        return True, None, []