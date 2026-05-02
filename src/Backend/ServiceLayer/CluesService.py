from typing import Any, Dict, Optional

from Backend.DomainLayer.CluePenalty import resolve_clue_penalty
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.CluesRepo import CluesRepo, CluesExhausted
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.PersistantLayer._db import transaction
from Backend.ServiceLayer.AuthService import AuthService


class CluePuzzleHasNoClues(ValidationError):
    """Puzzle has no clues authored — POST /clue should 404."""


class ClueAttemptInvalid(ValidationError):
    """Attempt id is missing, mismatched, or already submitted."""


class CluesAllConsumed(ValidationError):
    """All clues for this puzzle have been revealed on this attempt — POST /clue should 410."""


class CluesService:
    def __init__(
        self,
        conn,
        clues_repo: CluesRepo,
        puzzle_repo: PuzzleRepo,
        solve_repo: SolveRepo,
        auth: AuthService,
    ) -> None:
        self.conn = conn
        self.clues_repo = clues_repo
        self.puzzle_repo = puzzle_repo
        self.solve_repo = solve_repo
        self.auth = auth

    def request_clue(
        self,
        token: str,
        puzzle_id: int,
        attempt_id: int,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_id = self.auth.require_user_id(token)

        puzzle = self.puzzle_repo.get_by_id(int(puzzle_id))
        if puzzle is None:
            raise ValidationError("puzzle not found")

        clues = list(getattr(puzzle, "clues", None) or [])
        if not clues:
            raise CluePuzzleHasNoClues("puzzle has no clues")

        attempt = self.solve_repo.get_attempt_by_id(int(attempt_id)) if hasattr(self.solve_repo, "get_attempt_by_id") else None
        if attempt is None:
            raise ClueAttemptInvalid("attempt not found")
        if int(attempt.user_id) != int(user_id):
            raise ClueAttemptInvalid("attempt does not belong to this user")
        if int(attempt.puzzle_id) != int(puzzle_id):
            raise ClueAttemptInvalid("attempt does not match puzzle")
        if attempt.submitted_at is not None:
            raise ClueAttemptInvalid("attempt already submitted")

        penalty = int(resolve_clue_penalty(puzzle))
        total_clues = len(clues)

        with transaction(self.conn):
            try:
                recorded = self.clues_repo.record_next_clue(
                    attempt_id=int(attempt_id),
                    user_id=int(user_id),
                    puzzle_id=int(puzzle_id),
                    penalty_seconds=penalty,
                    total_clues=total_clues,
                    request_id=request_id,
                )
            except CluesExhausted as exc:
                raise CluesAllConsumed("all clues already revealed for this attempt") from exc

        clue_index = int(recorded["clue_index"])
        if clue_index < 0 or clue_index >= total_clues:
            # Defensive: should never happen because record_next_clue gates on total_clues.
            raise CluesAllConsumed("clue index out of range")

        clues_used = self.clues_repo.count_for_attempt(int(attempt_id))
        total_penalty = self.clues_repo.total_penalty_for_attempt(int(attempt_id))

        return {
            "clue_index": clue_index,
            "clue_text": clues[clue_index],
            "penalty_seconds": int(recorded["penalty_seconds"]),
            "total_clues": total_clues,
            "clues_used_so_far": int(clues_used),
            "total_penalty_so_far": int(total_penalty),
            "replayed": bool(recorded.get("replayed", False)),
        }
