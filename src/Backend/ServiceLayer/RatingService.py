def _parse_iso(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
from datetime import datetime, timezone
from typing import List

from Backend.DomainLayer.Rating import Rating
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.RatingRepo import RatingRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService


class RatingService:
    # Alias for test compatibility
    def list_ratings(self, token: str, puzzle_id: int) -> list:
        return self.list_ratings_for_puzzle(token, puzzle_id)

    def submit_rating(self, token: str, puzzle_id: int, payload: dict) -> Rating:
        # The test likely passes a dict payload with keys: difficulty, fun, clearness
        return self.rate_puzzle(
            token,
            puzzle_id,
            payload["difficulty"],
            payload["fun"],
            payload["clearness"]
        )
    def __init__(self, rating_repo: RatingRepo, puzzle_repo: PuzzleRepo, solve_repo: SolveRepo, auth: AuthService, xp_service: XPService):
        self.rating_repo = rating_repo
        self.puzzle_repo = puzzle_repo
        self.solve_repo = solve_repo
        self.auth = auth
        self.xp_service = xp_service

    @property
    def xp(self):
        return self.xp_service

    def _can_rate(self, user_id: int, puzzle_id: int) -> bool:
        # Rule: allowed if user solved OR at least 5 minutes passed since first attempt started
        if self.solve_repo.has_passed(user_id, puzzle_id):
            return True

        started_iso = self.solve_repo.first_attempt_started_at(user_id, puzzle_id)
        if not started_iso:
            return False
        try:
            started = datetime.fromisoformat(started_iso)
        except Exception:
            return False
        now = datetime.now(timezone.utc)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return (now - started).total_seconds() >= 5 * 60

    def rate_puzzle(self, token: str, puzzle_id: int, difficulty: int, fun: int, clearness: int) -> Rating:
        user_id = self.auth.require_user_id(token)
        puzzle = self.puzzle_repo.get_by_id(int(puzzle_id))
        if not puzzle:
            raise ValidationError("puzzle not found")

        if not self._can_rate(user_id, int(puzzle_id)):
            raise ValidationError("rating not allowed yet")

        is_experienced = self.xp_service.is_experienced(user_id)

        r = Rating(
            id=0,
            puzzle_id=int(puzzle_id),
            user_id=int(user_id),
            difficulty=int(difficulty),
            fun=int(fun),
            clearness=int(clearness),
            is_experienced_at_rating=bool(is_experienced),
        )

        # upsert + recalc
        saved = self.rating_repo.upsert(r)
        self._recalculate_and_store(puzzle.id)

        # XP for rating (once per rating action)
        self.xp_service.reward_for_rating(user_id)
        return saved

    def remove_rating(self, token: str, puzzle_id: int) -> bool:
        user_id = self.auth.require_user_id(token)
        ok = self.rating_repo.delete(int(puzzle_id), int(user_id))
        if ok:
            self._recalculate_and_store(int(puzzle_id))
        return ok

    def list_ratings_for_puzzle(self, token: str, puzzle_id: int) -> List[dict]:
        _ = self.auth.require_user_id(token)
        return [r.to_dict() for r in self.rating_repo.list_by_puzzle(int(puzzle_id))]

    def _recalculate_and_store(self, puzzle_id: int) -> None:
        puzzle = self.puzzle_repo.get_by_id(int(puzzle_id))
        if not puzzle:
            return

        ratings = self.rating_repo.list_by_puzzle(int(puzzle_id))
        puzzle.rating_count = len(ratings)

        # Creator vs non-creator split
        creator_id = int(puzzle.creator_user_id)
        creator_r = next((x for x in ratings if int(x.user_id) == creator_id), None)
        user_rs = [x for x in ratings if int(x.user_id) != creator_id]
        user_count = len(user_rs)

        # Difficulty weighting: until 10 user ratings collected -> 80% creator, 20% users; after -> 40% creator, 60% users
        if user_count > 0:
            users_difficulty_avg = sum(x.difficulty for x in user_rs) / user_count
        else:
            users_difficulty_avg = 0.0

        if creator_r is not None:
            alpha = 0.8 if user_count < 10 else 0.4
            puzzle.avg_difficulty = alpha * float(creator_r.difficulty) + (1 - alpha) * float(users_difficulty_avg)
        else:
            puzzle.avg_difficulty = float(users_difficulty_avg)

        # Fun & clearness undecided until 10 USER ratings (excluding creator)
        if user_count < 10:
            puzzle.fun_decided = False
            puzzle.clearness_decided = False
            puzzle.avg_fun = 0.0
            puzzle.avg_clearness = 0.0
        else:
            puzzle.fun_decided = True
            puzzle.clearness_decided = True
            puzzle.avg_fun = float(sum(x.fun for x in user_rs) / user_count)
            puzzle.avg_clearness = float(sum(x.clearness for x in user_rs) / user_count)

        # Experienced-only aggregates (ratings snapshot already stored)
        exp_rs = [x for x in ratings if bool(x.is_experienced_at_rating)]
        puzzle.rating_count_exp = len(exp_rs)
        if exp_rs:
            puzzle.avg_difficulty_exp = float(sum(x.difficulty for x in exp_rs) / len(exp_rs))
            if user_count >= 10:
                # still gate "decided" by the global 10-user rule
                puzzle.fun_decided_exp = True
                puzzle.clearness_decided_exp = True
                puzzle.avg_fun_exp = float(sum(x.fun for x in exp_rs) / len(exp_rs))
                puzzle.avg_clearness_exp = float(sum(x.clearness for x in exp_rs) / len(exp_rs))
            else:
                puzzle.fun_decided_exp = False
                puzzle.clearness_decided_exp = False
                puzzle.avg_fun_exp = 0.0
                puzzle.avg_clearness_exp = 0.0
        else:
            puzzle.avg_difficulty_exp = 0.0
            puzzle.avg_fun_exp = 0.0
            puzzle.avg_clearness_exp = 0.0
            puzzle.fun_decided_exp = False
            puzzle.clearness_decided_exp = False

        self.puzzle_repo.update(puzzle)
