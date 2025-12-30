from datetime import datetime, timezone
from statistics import mean
from typing import Dict, Any, List

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.RatingRepo import RatingRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService


def _parse_iso(dt_str: str) -> datetime:
    d = datetime.fromisoformat(dt_str)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


class RatingService:
    """
    - must be allowed only after solve or 5 minutes attempt (ARD)
    - experienced (level>=5) ratings have double weight
    - rating grants small XP (ADD) - only on first rating per puzzle
    """
    def __init__(
        self,
        rating_repo: RatingRepo,
        puzzle_repo: PuzzleRepo,
        solve_repo: SolveRepo,
        auth_service: AuthService,
        xp_service: XPService,
    ):
        self.rating_repo = rating_repo
        self.puzzle_repo = puzzle_repo
        self.solve_repo = solve_repo
        self.auth = auth_service
        self.xp = xp_service

    def _can_rate(self, user_id: int, puzzle_id: int) -> bool:
        if self.solve_repo.has_passed(user_id, puzzle_id):
            return True
        started = self.solve_repo.first_attempt_started_at(user_id, puzzle_id)
        if not started:
            return False
        try:
            t0 = _parse_iso(started)
        except Exception:
            return False
        now = datetime.now(timezone.utc)
        return (now - t0).total_seconds() >= 5 * 60

    def list_ratings(self, session_token: str, puzzle_id: int) -> List[dict]:
        _ = self.auth.require_user_id(session_token)
        ratings = self.rating_repo.list_by_puzzle(puzzle_id)
        return [r.to_dict() for r in ratings]

    def submit_rating(self, session_token: str, puzzle_id: int, payload: Dict[str, Any]) -> dict:
        user_id = self.auth.require_user_id(session_token)

        puzzle = self.puzzle_repo.get_by_id(puzzle_id)
        if not puzzle:
            raise ValidationError("puzzle not found")

        if not self._can_rate(user_id, puzzle_id):
            raise ValidationError("rating not allowed yet")

        # domain object
        from Backend.DomainLayer.Rating import Rating

        existing = self.rating_repo.get_by_puzzle_user(puzzle_id, user_id)
        first_time = existing is None

        # is_experienced snapshot:
        # We compute from current XP, but store snapshot in rating.
        # (Your domain already uses boolean snapshot.)
        from Backend.PersistantLayer.UserRepo import UserRepo  # local import to avoid circulars
        # NOTE: authService already verifies user exists in userRepo;
        # but XPService is the official source for level calc.
        is_exp = self.xp.is_experienced(self.xp.user_repo.get_by_id(user_id).xp)

        # Use id=1 for new ratings to satisfy domain validation
        rating = Rating(
            id=1,
            puzzle_id=puzzle_id,
            user_id=user_id,
            difficulty=int(payload.get("difficulty", 0)),
            fun=int(payload.get("fun", 0)),
            clearness=int(payload.get("clearness", 0)),
            is_experienced_at_rating=bool(is_exp),
        )
        saved = self.rating_repo.upsert(rating)

        # update weighted aggregates on puzzle (experienced weight=2)
        all_ratings = self.rating_repo.list_by_puzzle(puzzle_id)
        puzzle.rating_count = len(all_ratings)

        def w(r) -> int:
            return 2 if r.is_experienced_at_rating else 1

        total_w = sum(w(r) for r in all_ratings) or 1
        puzzle.avg_difficulty = sum(w(r) * r.difficulty for r in all_ratings) / total_w if all_ratings else 0.0
        puzzle.avg_fun = sum(w(r) * r.fun for r in all_ratings) / total_w if all_ratings else 0.0
        puzzle.avg_clearness = sum(w(r) * r.clearness for r in all_ratings) / total_w if all_ratings else 0.0

        self.puzzle_repo.update(puzzle)

        # small XP reward (ADD) only for first-time rating
        self.xp.award_rating_xp(user_id, first_time_rating=first_time)

        return saved.to_dict()
