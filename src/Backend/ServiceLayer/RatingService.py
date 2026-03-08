from datetime import datetime, timezone
from typing import List

from Backend import settings

def _parse_iso(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

from Backend.DomainLayer.Rating import Rating
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer._db import transaction
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
        rating = self.create_rating(token, puzzle_id, payload)
        if hasattr(rating, "to_dict"):
            return rating.to_dict()
        return dict(rating)

    def update_rating(self, token: str, puzzle_id: int, payload: dict) -> dict:
        rating = self.edit_rating(
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
        return effective_time >= settings.RATING_MIN_ATTEMPT_SECONDS

    def _store_rating(
        self,
        token: str,
        puzzle_id: int,
        difficulty: int,
        fun: int,
        clearness: int,
        client_elapsed: int | None = None,
        *,
        allow_existing: bool,
    ) -> Rating:
        user_id = self.auth.require_user_id(token)
        puzzle = self.puzzle_repo.get_by_id(int(puzzle_id))
        if not puzzle:
            raise ValidationError("puzzle not found")

        existing = self.rating_repo.get_by_puzzle_user(int(puzzle_id), int(user_id))
        if existing and not allow_existing:
            raise ValidationError("You already rated this puzzle. Use the edit flow instead.")
        if not existing and allow_existing:
            raise ValidationError("rating not found")

        if not self._can_rate(user_id, int(puzzle_id), client_elapsed=int(client_elapsed or 0)):
            raise ValidationError("You must solve the puzzle or attempt it for at least 5 minutes to rate.")

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

        # Wrap upsert + recalc + XP award in a single IMMEDIATE transaction.
        # This prevents concurrent raters from computing stale aggregates (C3)
        # and ensures XP-mark + XP-award are atomic (H3).
        with transaction(self.rating_repo.conn) as conn:
            saved = self.rating_repo.upsert(r, commit=False)
            self._recalculate_and_store(puzzle.id)
            first_time_rating = self.rating_repo.try_mark_xp_awarded(int(puzzle_id), int(user_id))
            if first_time_rating:
                self.xp_service.award_rating_xp(
                    rater_user_id=int(user_id),
                    creator_user_id=int(puzzle.creator_user_id),
                    first_time_rating=True,
                )
            # COMMIT happens here at context-manager exit

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

    def rate_puzzle(self, token: str, puzzle_id: int, difficulty: int, fun: int, clearness: int, client_elapsed: int | None = None) -> Rating:
        return self._store_rating(
            token,
            puzzle_id,
            difficulty,
            fun,
            clearness,
            client_elapsed=client_elapsed,
            allow_existing=True,
        )

    def create_rating(self, token: str, puzzle_id: int, payload: dict) -> Rating:
        return self._store_rating(
            token,
            puzzle_id,
            payload["difficulty"],
            payload["fun"],
            payload["clearness"],
            client_elapsed=payload.get("elapsed_seconds"),
            allow_existing=False,
        )

    def edit_rating(self, token: str, puzzle_id: int, difficulty: int, fun: int, clearness: int, client_elapsed: int | None = None) -> Rating:
        return self._store_rating(
            token,
            puzzle_id,
            difficulty,
            fun,
            clearness,
            client_elapsed=client_elapsed,
            allow_existing=True,
        )

    def remove_rating(self, token: str, puzzle_id: int) -> bool:
        user_id = self.auth.require_user_id(token)
        with transaction(self.rating_repo.conn) as conn:
            cur = conn.execute(
                "DELETE FROM ratings WHERE puzzle_id=? AND user_id=?",
                (int(puzzle_id), int(user_id)),
            )
            ok = cur.rowcount > 0
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

    _DIFFICULTY_MAP = settings.RATING_DIFFICULTY_MAP

    @staticmethod
    def _exp_weight(rating: Rating) -> int:
        return 2 if rating.is_experienced_at_rating else 1

    @staticmethod
    def _weighted_avg(values: list[float], weights: list[int]) -> float | None:
        total_weight = sum(weights)
        if total_weight <= 0:
            return None
        return sum(v * w for v, w in zip(values, weights)) / total_weight

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

        # General averages use experienced double-weighting.
        weights = [self._exp_weight(r) for r in ratings]
        avg_difficulty = self._weighted_avg([float(r.difficulty) for r in ratings], weights)
        weighted_avg_fun = self._weighted_avg([float(r.fun) for r in ratings], weights)
        weighted_avg_clearness = self._weighted_avg([float(r.clearness) for r in ratings], weights)

        # Weighted difficulty (blends creator label with user ratings)
        weighted_user_avg_difficulty = avg_difficulty if avg_difficulty is not None else 0.0
        _w_few  = settings.RATING_DIFF_WEIGHT_FEW_RATINGS
        _w_many = settings.RATING_DIFF_WEIGHT_MANY_RATINGS
        if count < settings.RATING_USER_COUNT_THRESHOLD:
            weighted_difficulty = (_w_few[0] * creator_diff) + (_w_few[1] * weighted_user_avg_difficulty)
        else:
            weighted_difficulty = (_w_many[0] * creator_diff) + (_w_many[1] * weighted_user_avg_difficulty)

        # Keep UI behavior: expose fun/clearness as soon as ratings exist.
        if count > 0:
            avg_fun = weighted_avg_fun
            avg_clearness = weighted_avg_clearness
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

        experienced_metrics = {
            "count": exp_count,
            "experienced_avg_difficulty": round(exp_avg_difficulty, 2) if exp_avg_difficulty is not None else None,
            "experienced_avg_fun": round(exp_avg_fun, 2) if exp_avg_fun is not None else None,
            "experienced_avg_clearness": round(exp_avg_clearness, 2) if exp_avg_clearness is not None else None,
        }

        return {
            "puzzle_id": int(puzzle_id),
            "count": count,
            "avg_difficulty": round(avg_difficulty, 2) if avg_difficulty is not None else None,
            "weighted_difficulty": round(weighted_difficulty, 1),
            "avg_fun": round(avg_fun, 2) if avg_fun is not None else None,
            "avg_clearness": round(avg_clearness, 2) if avg_clearness is not None else None,
            "experienced_metrics": experienced_metrics,
            # Backward-compatible alias retained for existing clients.
            "experienced": {
                "count": experienced_metrics["count"],
                "avg_difficulty": experienced_metrics["experienced_avg_difficulty"],
                "avg_fun": experienced_metrics["experienced_avg_fun"],
                "avg_clearness": experienced_metrics["experienced_avg_clearness"],
            },
        }

    def _recalculate_and_store(self, puzzle_id: int) -> None:
        puzzle = self.puzzle_repo.get_by_id(int(puzzle_id))
        if not puzzle:
            return

        ratings = self.rating_repo.list_by_puzzle(int(puzzle_id))
        rating_count = len(ratings)

        # Keep zero aggregates when no ratings exist.
        if rating_count == 0:
            avg_difficulty = 0.0
            avg_fun = 0.0
            avg_clearness = 0.0
        else:
            creator_diff_str = puzzle.difficulty.value if hasattr(puzzle.difficulty, 'value') else str(puzzle.difficulty)
            creator_diff = float(self._DIFFICULTY_MAP.get(creator_diff_str, 1))

            weights = [self._exp_weight(r) for r in ratings]
            weighted_user_avg_difficulty = self._weighted_avg([float(r.difficulty) for r in ratings], weights) or 0.0
            weighted_avg_fun = self._weighted_avg([float(r.fun) for r in ratings], weights) or 0.0
            weighted_avg_clearness = self._weighted_avg([float(r.clearness) for r in ratings], weights) or 0.0

            _w = (
                settings.RATING_DIFF_WEIGHT_FEW_RATINGS
                if rating_count < settings.RATING_USER_COUNT_THRESHOLD
                else settings.RATING_DIFF_WEIGHT_MANY_RATINGS
            )
            avg_difficulty = (_w[0] * creator_diff) + (_w[1] * weighted_user_avg_difficulty)

            # Undecided status for persisted aggregates remains 0.0 until enough raw ratings exist.
            if rating_count < settings.RATING_USER_COUNT_THRESHOLD:
                avg_fun = 0.0
                avg_clearness = 0.0
            else:
                avg_fun = weighted_avg_fun
                avg_clearness = weighted_avg_clearness

        # Use targeted update — only writes rating columns, won't clobber
        # concurrent changes to name, status, description, budget, etc.
        self.puzzle_repo.update_rating_aggregates(
            puzzle_id,
            rating_count=rating_count,
            avg_difficulty=avg_difficulty,
            avg_fun=avg_fun,
            avg_clearness=avg_clearness,
        )
