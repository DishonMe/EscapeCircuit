from dataclasses import dataclass
from typing import Optional

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.UserRepo import UserRepo

# Base puzzle capacity for creators (levels 1-9)
_PUZZLE_CAPACITY_BASE = 5
# Each level from 10 to 15 adds +2; cap at level 15
_PUZZLE_CAPACITY_MAX_INCREMENTS = 6  # levels 10, 11, 12, 13, 14, 15


@dataclass(slots=True)
class XPService:
    """
    Implements the XP policy mentioned in ADD/ARD:
    - Levels derived from XP thresholds
    - Experienced user: Level >= 5
    - Abuse resistance: repeated solves do NOT re-grant bonuses
    """
    user_repo: UserRepo

    # core XP config
    easy_xp: int = 50
    medium_xp: int = 100
    hard_xp: int = 150

    first_solve_bonus: int = 50
    time_bonus: int = 25

    repeat_solve_xp: int = 10  # if user already solved puzzle before
    # Rating XP (ADD): rater gets 5 XP, puzzle creator gets 1 XP.
    rating_rater_xp: int = 5
    rating_creator_xp: int = 1

    # Level thresholds (index = level, value = min XP)
    # Level 1 starts at 0, Level 5 at 2000 -> matches ARD "Level 5 experienced"
    # Levels 11-15 are needed for the puzzle capacity scaling (increases by 2 per level from 10 to 15)
    level_thresholds = [0, 250, 600, 1100, 1700, 2000, 2600, 3400, 4500, 6000,
                        7800, 9800, 12000, 14500, 17000]

    def calculate_level(self, xp_total: int) -> int:
        xp_total = int(xp_total)
        if xp_total < 0:
            xp_total = 0
        lvl = 1
        for i, thr in enumerate(self.level_thresholds, start=1):
            if xp_total >= thr:
                lvl = i
        return lvl

    def is_experienced(self, xp_total: int) -> bool:
        return self.calculate_level(xp_total) >= 5

    def tier_from_avg_difficulty(self, avg_difficulty: float) -> str:
        """Map a numeric difficulty rating (1..5) to a tier string."""
        try:
            d = float(avg_difficulty)
        except Exception:
            d = 1.0
        if d >= 4.0:
            return "hard"
        if d >= 2.5:
            return "medium"
        return "easy"

    def get_arsenal_limit(self, xp_total: int) -> int:
        """Arsenal capacity based on level.

        This is intentionally simple and can be tuned later, but ensures:
        - early users have a small limit
        - progressing levels increases capacity
        """
        lvl = self.calculate_level(int(xp_total))
        if lvl <= 2:
            return 5
        if lvl <= 4:
            return 10
        if lvl <= 6:
            return 20
        if lvl <= 8:
            return 35
        return 50

    def get_puzzle_published_limit(self, xp_total: int, override: Optional[int] = None) -> int:
        """Max number of published puzzles a creator may have.

        Base is 5 for levels 1-9.  From level 10 to level 15 the limit
        grows by +2 per level (capped at level 15).
        An admin-set override supersedes the level-based calculation.
        """
        if override is not None:
            return max(0, override)
        lvl = self.calculate_level(int(xp_total))
        if lvl < 10:
            return _PUZZLE_CAPACITY_BASE
        increments = min(lvl - 9, _PUZZLE_CAPACITY_MAX_INCREMENTS)
        return _PUZZLE_CAPACITY_BASE + increments * 2

    def get_puzzle_unpublished_limit(self, xp_total: int, override: Optional[int] = None) -> int:
        """Max number of draft/unpublished puzzles a creator may have.

        Uses the same formula as published limit.  The admin-set override
        for unpublished is independent of the published one.
        """
        if override is not None:
            return max(0, override)
        return self.get_puzzle_published_limit(xp_total)

    def _apply_xp(self, user_id: int, delta: int) -> int:
        if delta <= 0:
            return 0
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")
        user.add_xp(delta)
        self.user_repo.update_xp(user_id, user.xp)
        return delta

    def award_solve_xp(
        self,
        user_id: int,
        difficulty_tier: str,
        is_first_solve: bool,
        timer_beaten: bool,
        already_solved_before: bool
    ) -> int:
        """
        Abuse resistance:
        - if already_solved_before => grant only repeat_solve_xp, NO bonuses.
        - otherwise base XP by tier + optional bonuses.
        """
        if already_solved_before:
            return self._apply_xp(user_id, self.repeat_solve_xp)

        tier = (difficulty_tier or "easy").strip().lower()
        if tier == "hard":
            base = self.hard_xp
        elif tier == "medium":
            base = self.medium_xp
        else:
            base = self.easy_xp

        bonus = 0
        if is_first_solve:
            bonus += self.first_solve_bonus
        if timer_beaten:
            bonus += self.time_bonus

        return self._apply_xp(user_id, base + bonus)

    def award_rating_xp(self, rater_user_id: int, creator_user_id: int, first_time_rating: bool) -> int:
        """Award rating XP.

        Only the first rating per (puzzle,user) grants XP.
        Returns total XP applied (rater + creator).
        """
        if not first_time_rating:
            return 0
        total = 0
        total += self._apply_xp(rater_user_id, self.rating_rater_xp)
        # creator also gets 1 XP (even if it's the same user, don't double-award)
        if int(creator_user_id) != int(rater_user_id):
            total += self._apply_xp(creator_user_id, self.rating_creator_xp)
        return total
