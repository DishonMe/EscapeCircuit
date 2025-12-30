import sqlite3
from contextlib import contextmanager
from typing import Dict, Any

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.ServiceLayer.XPService import XPService


@contextmanager
def _tx(conn: sqlite3.Connection):
    try:
        conn.execute("BEGIN;")
        yield
        conn.execute("COMMIT;")
    except Exception:
        conn.execute("ROLLBACK;")
        raise


class SolvingService:
    """
    Works with:
    - logicEngineService
    - XPService
    - puzzleRepo
    """
    def __init__(
        self,
        conn: sqlite3.Connection,
        solve_repo: SolveRepo,
        puzzle_repo: PuzzleRepo,
        circuit_repo: CircuitRepo,
        auth_service: AuthService,
        engine: logicEngineService,
        xp_service: XPService,
    ):
        self.conn = conn
        self.solve_repo = solve_repo
        self.puzzle_repo = puzzle_repo
        self.circuit_repo = circuit_repo
        self.auth = auth_service
        self.engine = engine
        self.xp = xp_service

    def start_attempt(self, session_token: str, puzzle_id: int) -> dict:
        user_id = self.auth.require_user_id(session_token)

        puzzle = self.puzzle_repo.get_by_id(puzzle_id)
        if not puzzle:
            raise ValidationError("puzzle not found")

        from Backend.DomainLayer.SolveAttempt import SolveAttempt
        attempt = SolveAttempt(id=0, puzzle_id=puzzle_id, user_id=user_id)
        created = self.solve_repo.create_attempt(attempt)
        return created.to_dict()

    def submit_solution(self, session_token: str, puzzle_id: int, payload: Dict[str, Any]) -> dict:
        user_id = self.auth.require_user_id(session_token)
        circuit_id = int(payload.get("circuit_id", 0))
        if circuit_id <= 0:
            raise ValidationError("circuit_id required")

        puzzle = self.puzzle_repo.get_by_id(puzzle_id)
        if not puzzle:
            raise ValidationError("puzzle not found")

        circuit = self.circuit_repo.get_by_id(circuit_id)
        if not circuit:
            raise ValidationError("circuit not found")
        if circuit.user_id != user_id:
            raise ValidationError("forbidden")

        testcases = self.puzzle_repo.list_test_cases(puzzle_id)
        if not testcases:
            raise ValidationError("puzzle has no test cases")

        # Evaluate
        passed = True
        fail_reason = None
        for tc in testcases:
            out = self.engine.evaluate(circuit, tc.inputs)
            if out != tc.expected_outputs:
                passed = False
                fail_reason = "wrong output"
                break

        # open attempt if exists, else create
        attempt = self.solve_repo.get_open_attempt(user_id, puzzle_id)
        if attempt is None:
            from Backend.DomainLayer.SolveAttempt import SolveAttempt
            attempt = SolveAttempt(id=0, puzzle_id=puzzle_id, user_id=user_id)
            attempt = self.solve_repo.create_attempt(attempt)

        # finalize attempt + XP atomically
        with _tx(self.conn):
            attempt.mark_submitted(passed=passed, circuit_id=circuit_id, fail_reason=fail_reason)
            self.solve_repo.update_attempt(attempt)

            if passed:
                already_solved_before = self.solve_repo.has_passed_before_attempt(user_id, puzzle_id, attempt.id)
                is_first_solve = not already_solved_before

                timer_beaten = False
                if puzzle.time_limit_seconds is not None and attempt.elapsed_seconds is not None:
                    timer_beaten = attempt.elapsed_seconds <= puzzle.time_limit_seconds

                # difficulty tier fallback:
                # If you later add explicit tier, replace this.
                # For now: use avg_difficulty if exists.
                tier = "easy"
                try:
                    if getattr(puzzle, "avg_difficulty", 0) >= 7:
                        tier = "hard"
                    elif getattr(puzzle, "avg_difficulty", 0) >= 4:
                        tier = "medium"
                except Exception:
                    pass

                self.xp.award_solve_xp(
                    user_id=user_id,
                    difficulty_tier=tier,
                    is_first_solve=is_first_solve,
                    timer_beaten=timer_beaten,
                    already_solved_before=already_solved_before
                )

        return attempt.to_dict()
