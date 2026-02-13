from datetime import datetime, timezone
from typing import List

def _parse_iso(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

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

    def submit_rating(self, token: str, puzzle_id: int, payload: dict) -> dict:
        # The test likely passes a dict payload with keys: difficulty, fun, clearness
        rating = self.rate_puzzle(
            token,
            puzzle_id,
            payload["difficulty"],
            payload["fun"],
            payload["clearness"],
            client_elapsed=payload.get("elapsed_seconds"),
        )
        # Return as dict for test compatibility
        if hasattr(rating, "to_dict"):
            return rating.to_dict()
        return dict(rating)
    def __init__(self, rating_repo: RatingRepo, puzzle_repo: PuzzleRepo, solve_repo: SolveRepo, auth: AuthService, xp_service: XPService, notification_service=None):
        self.rating_repo = rating_repo
        self.puzzle_repo = puzzle_repo
        self.solve_repo = solve_repo
        self.auth = auth
        self.xp_service = xp_service
        self.notification_service = notification_service

    @property
    def xp(self):
        return self.xp_service

    def _can_rate(self, user_id: int, puzzle_id: int, client_elapsed: int = 0) -> bool:
        # Always allow if user already has a rating (they can update it)
        if self.rating_repo.get_by_puzzle_user(int(puzzle_id), int(user_id)):
            return True

        # Rule: allowed if user solved OR total time on puzzle >= 300s (5 mins)
        if self.solve_repo.has_passed(user_id, puzzle_id):
            return True

        total_time = self.solve_repo.get_total_time_on_puzzle(user_id, puzzle_id)
        effective_time = max(total_time, client_elapsed)
        return effective_time >= 300  # 5 minutes

    def rate_puzzle(self, token: str, puzzle_id: int, difficulty: int, fun: int, clearness: int, client_elapsed: int | None = None) -> Rating:
        user_id = self.auth.require_user_id(token)
        puzzle = self.puzzle_repo.get_by_id(int(puzzle_id))
        if not puzzle:
            raise ValidationError("puzzle not found")

        if not self._can_rate(user_id, int(puzzle_id), client_elapsed=int(client_elapsed or 0)):
            raise ValidationError("You must solve the puzzle or attempt it for at least 5 minutes to rate.")

        # Check if first-time rating BEFORE upsert (for XP logic)
        existing_rating = self.rating_repo.get_by_puzzle_user(int(puzzle_id), int(user_id))
        first_time_rating = existing_rating is None

        # Snapshot experienced status at rating time
        user = self.auth.user_repo.get_by_id(user_id)
        is_experienced = self.xp_service.is_experienced(user.xp if user else 0)

        r = Rating(
            id=1,
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

        # XP: only award on first-time rating
        self.xp_service.award_rating_xp(
            rater_user_id=int(user_id),
            creator_user_id=int(puzzle.creator_user_id),
            first_time_rating=first_time_rating,
        )

        # Notify creator about the rating (only first time, only if creator != rater)
        if first_time_rating and int(puzzle.creator_user_id) != int(user_id) and self.notification_service:
            try:
                rater = self.auth.user_repo.get_by_id(user_id)
                rater_name = rater.username if rater else f"User #{user_id}"
                self.notification_service.notify_creator_rating(
                    creator_user_id=int(puzzle.creator_user_id),
                    rater_username=rater_name,
                    puzzle_name=puzzle.name,
                    xp_amount=self.xp_service.rating_creator_xp,
                )
            except Exception:
                pass  # notification is best-effort

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

    def get_my_rating(self, token: str, puzzle_id: int) -> dict | None:
        user_id = self.auth.require_user_id(token)
        r = self.rating_repo.get_by_puzzle_user(int(puzzle_id), int(user_id))
        return r.to_dict() if r else None

    _DIFFICULTY_MAP = {"EASY": 1, "MEDIUM": 3, "HARD": 5}

    def get_puzzle_metrics(self, puzzle_id: int) -> dict:
        """Compute aggregated rating metrics for a puzzle."""
        puzzle = self.puzzle_repo.get_by_id(int(puzzle_id))
        if not puzzle:
            return {}

        ratings = self.rating_repo.list_by_puzzle(int(puzzle_id))
        count = len(ratings)

        # Creator difficulty mapping
        creator_diff_str = puzzle.difficulty.value if hasattr(puzzle.difficulty, 'value') else str(puzzle.difficulty)
        creator_diff = self._DIFFICULTY_MAP.get(creator_diff_str, 1)

        # Pure user average difficulty
        avg_difficulty = sum(r.difficulty for r in ratings) / count if count > 0 else None

        # Weighted difficulty (blends creator label with user ratings)
        users_avg = avg_difficulty if avg_difficulty is not None else 0.0
        if count < 10:
            weighted_difficulty = (0.8 * creator_diff) + (0.2 * users_avg)
        else:
            weighted_difficulty = (0.4 * creator_diff) + (0.6 * users_avg)

        # Fun & clearness: always compute when ratings exist
        if count > 0:
            avg_fun = sum(r.fun for r in ratings) / count
            avg_clearness = sum(r.clearness for r in ratings) / count
        else:
            avg_fun = None
            avg_clearness = None

        # Experienced-only metrics
        exp_ratings = [r for r in ratings if r.is_experienced_at_rating]
        exp_count = len(exp_ratings)
        if exp_count > 0:
            exp_avg_difficulty = sum(r.difficulty for r in exp_ratings) / exp_count
            exp_avg_fun = sum(r.fun for r in exp_ratings) / exp_count
            exp_avg_clearness = sum(r.clearness for r in exp_ratings) / exp_count
        else:
            exp_avg_difficulty = None
            exp_avg_fun = None
            exp_avg_clearness = None

        return {
            "puzzle_id": int(puzzle_id),
            "count": count,
            "avg_difficulty": round(avg_difficulty, 2) if avg_difficulty is not None else None,
            "weighted_difficulty": round(weighted_difficulty, 1),
            "avg_fun": round(avg_fun, 2) if avg_fun is not None else None,
            "avg_clearness": round(avg_clearness, 2) if avg_clearness is not None else None,
            "experienced": {
                "count": exp_count,
                "avg_difficulty": round(exp_avg_difficulty, 2) if exp_avg_difficulty is not None else None,
                "avg_fun": round(exp_avg_fun, 2) if exp_avg_fun is not None else None,
                "avg_clearness": round(exp_avg_clearness, 2) if exp_avg_clearness is not None else None,
            },
        }

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
