from dataclasses import dataclass
from typing import Optional

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.UserRepo import UserRepo


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
    rating_xp: int = 10        # small XP reward for rating (first rating only)

    # Level thresholds (index = level, value = min XP)
    # Level 1 starts at 0, Level 5 at 2000 -> matches ARD "Level 5 experienced"
    level_thresholds = [0, 250, 600, 1100, 1700, 2000, 2600, 3400, 4500, 6000]

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

    def award_rating_xp(self, user_id: int, first_time_rating: bool) -> int:
        if not first_time_rating:
            return 0
        return self._apply_xp(user_id, self.rating_xp)
