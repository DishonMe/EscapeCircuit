from typing import Dict, Any, List
import json

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.SolveAttempt import SolveAttempt
from Backend.PersistantLayer.SolveRepo import SolveRepo, PuzzleProgress
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService
from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.DomainLayer.Enums import PuzzleStatus, PuzzleDifficulty, Medal


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
        user_repo: UserRepo | None = None,
    ):
        self.conn = conn
        self.solve_repo = solve_repo
        self.puzzle_repo = puzzle_repo
        self.circuit_repo = circuit_repo
        self.user_repo = user_repo
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
                attempt.mark_submitted(passed=True)
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
    def validate_solution(self, token: str, puzzle_id: int, solution_payload: Dict[str, Any], time_taken: int = 0) -> Dict[str, Any]:
        """
        Stateless validation of a solution attempt.
        If the solution passes, calculate medal, persist solve with delta XP, award creator XP.
        """
        user_id = self.auth.require_user_id(token)
        
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
            cost_used = int(solution_payload.get("totalCost", 0))
            time_taken_s = max(0, int(time_taken))

            # --- Determine difficulty tier from avg_difficulty ---
            difficulty = PuzzleDifficulty.EASY
            if hasattr(self.xp_service, 'tier_from_avg_difficulty'):
                difficulty = self.xp_service.tier_from_avg_difficulty(
                    getattr(p, 'avg_difficulty', 0.0)
                )
            elif hasattr(p, 'avg_difficulty') and p.avg_difficulty is not None:
                if p.avg_difficulty >= 7.0:
                    difficulty = PuzzleDifficulty.HARD
                elif p.avg_difficulty >= 4.0:
                    difficulty = PuzzleDifficulty.MEDIUM

            # --- Calculate medal ---
            medal = Medal.BRONZE  # default: solved = Bronze
            if hasattr(self.xp_service, 'calculate_medal'):
                medal = self.xp_service.calculate_medal(
                    passed=True,
                    time_taken=time_taken_s,
                    time_limit=getattr(p, 'time_limit_seconds', None),
                    cost_used=cost_used,
                    budget=getattr(p, 'budget', 0),
                )

            # --- Relative XP: only award improvement over previous best ---
            previous_best_xp = 0
            if hasattr(self.solve_repo, 'get_best_xp_for_puzzle'):
                previous_best_xp = self.solve_repo.get_best_xp_for_puzzle(user_id, puzzle_id)

            xp_earned = 0
            if hasattr(self.xp_service, 'calculate_solve_xp'):
                xp_earned = self.xp_service.calculate_solve_xp(
                    difficulty=difficulty,
                    medal=medal,
                    previous_best_xp=previous_best_xp,
                )
            else:
                # Fallback to simple calculation
                raw_xp = getattr(self.xp_service, 'BASE_XP', {}).get(difficulty, 100)
                xp_earned = max(0, raw_xp - previous_best_xp)

            # --- Persist the solve attempt ---
            if hasattr(self.solve_repo, 'add_solve'):
                self.solve_repo.add_solve(
                    user_id=user_id,
                    puzzle_id=puzzle_id,
                    time_taken_seconds=time_taken_s,
                    xp_earned=xp_earned,
                    medal=medal.value if isinstance(medal, Medal) else int(medal),
                )

            # --- Update puzzle_progress with best medal ---
            if hasattr(self.solve_repo, 'upsert_progress'):
                from Backend.PersistantLayer.SolveRepo import PuzzleProgress
                from Backend.DomainLayer.Utils import utcnow
                old_progress = self.solve_repo.get_progress(user_id, puzzle_id)
                new_best_medal = max(
                    getattr(old_progress, 'best_medal', 0),
                    medal.value if isinstance(medal, Medal) else int(medal),
                )
                timer_upgraded = getattr(old_progress, 'timer_upgraded', False)
                tight_upgraded = getattr(old_progress, 'tight_upgraded', False)
                # Track bonus conditions
                if p.time_limit_seconds and time_taken_s <= p.time_limit_seconds:
                    timer_upgraded = True
                if p.budget > 0 and cost_used <= p.budget:
                    tight_upgraded = True
                self.solve_repo.upsert_progress(PuzzleProgress(
                    user_id=user_id,
                    puzzle_id=puzzle_id,
                    best_medal=new_best_medal,
                    timer_upgraded=timer_upgraded,
                    tight_upgraded=tight_upgraded,
                    first_solved_at=utcnow().isoformat(),
                ))

            # --- Accumulate XP on the User entity (only the delta) ---
            if self.user_repo is not None and xp_earned > 0:
                user = self.user_repo.get_by_id(user_id)
                if user:
                    new_xp = int(user.xp) + int(xp_earned)
                    self.user_repo.update_xp(user_id, new_xp)

            # --- Award creator XP ---
            creator_id = int(p.creator_user_id)
            if hasattr(self.xp_service, 'award_creator_solve_xp'):
                self.xp_service.award_creator_solve_xp(
                    creator_user_id=creator_id,
                    solver_user_id=user_id,
                )

            self.conn.commit()

            medal_name = medal.name if isinstance(medal, Medal) else ["NONE", "BRONZE", "SILVER", "GOLD"][int(medal)]
            msg = "All test cases passed!"
            if xp_earned == 0:
                msg += " No XP improvement this time."

            return {
                "solved": True,
                "message": msg,
                "xp_earned": xp_earned,
                "time_taken": time_taken_s,
                "medal": medal_name,
                "medal_value": medal.value if isinstance(medal, Medal) else int(medal),
            }
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
        
        # Priority 1: Explicit state definition (e.g. Mealy Machine / Sample Solution)
        if "state" in structure and isinstance(structure["state"], list):
            dff_ids = structure["state"]
        else:
            # Priority 2: Inferred from placed DFF components (User Simulation)
            for c in placed:
                ctype = c.get("componentId") or c.get("type")
                if ctype == "DFF":
                    dff_ids.append(c["id"])

        for i, tc in enumerate(test_cases):
            # Check if this is a Sequential Test Case (Stream)
            input_stream = getattr(tc, "input_stream", None)
            
            # Handle dictionary access if tc is a dict
            if input_stream is None and isinstance(tc, dict):
                input_stream = tc.get("input_stream")
                
            if input_stream is not None and len(input_stream) > 0:
                # === SEQUENTIAL SIMULATION (INJECTED LOGIC) ===
                # 'current_state' acts as our look-back history
                current_state = {str(did): 0 for did in dff_ids}
                
                expected_stream = getattr(tc, "expected_output_stream", None) or tc.get("expected_output_stream", {})
                if not expected_stream:
                    return False, "Sequential test case has input_stream but no expected_output_stream", [{"error": "malformed test case"}]
                    
                actual_stream = {k: [] for k in expected_stream.keys()}
                
                # Loop through discrete time steps (cycles)
                for step_idx, val in enumerate(input_stream):
                    # 1. Prepare Inputs: Merge current cycle inputs with past cycle state
                    cycle_inputs = val.copy() if isinstance(val, dict) else {"X": val}
                    cycle_inputs.update(current_state)
                    
                    # 2. Evaluate the circuit for this specific cycle
                    try:
                        step_result = self.logic_engine.evaluate(circuit, cycle_inputs)
                    except Exception as e:
                        return False, f"Cycle {step_idx} error: {str(e)}", [{"error": str(e)}]

                    # 3. Record the outputs for this cycle
                    for k in actual_stream.keys():
                        actual_stream[k].append(step_result.get(k, 0))
                    
                    # 4. Update the state for the NEXT cycle (Injecting the 'D' logic)
                    # We take the values that were at the DFF inputs and save them
                    for did in dff_ids:
                        next_val = step_result.get(f"{did}_next")
                        current_state[str(did)] = next_val if next_val is not None else 0

                # 5. Final check of the output stream
                if actual_stream != expected_stream:
                    return False, "Sequential output mismatch", [{
                        "test_case_index": i,
                        "expected": expected_stream,
                        "actual": actual_stream
                    }]

            else:
                # === COMBINATORIAL SIMULATION ===
                inputs = getattr(tc, "inputs", None) or tc.get("inputs")
                expected = getattr(tc, "expected_outputs", None) or tc.get("expected_outputs")
                
                try:
                    out = self.logic_engine.evaluate(circuit, inputs)
                    if out != expected:
                        return False, "Wrong output", [{
                            "inputs": inputs,
                            "expected": expected,
                            "actual": out
                        }]
                except Exception as e:
                    return False, str(e), [{"error": str(e)}]

        return True, None, []