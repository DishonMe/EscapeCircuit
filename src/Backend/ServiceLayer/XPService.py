from dataclasses import dataclass, field
from math import floor, sqrt
from typing import Optional

from Backend.DomainLayer.Enums import PuzzleDifficulty, Medal
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.UserRepo import UserRepo


@dataclass(slots=True)
class XPService:
    """
    Advanced XP & Medal system.
    - Difficulty-based base XP
    - Medal bonuses (Bronze/Silver/Gold)
    - Delta XP: only awards improvement over previous best
    - Creator reward when someone solves their puzzle
    - Level = floor(sqrt(xp / 100)) + 1
    """
    user_repo: UserRepo

    # --- Base XP per difficulty ---
    BASE_XP: dict = field(default_factory=lambda: {
        PuzzleDifficulty.EASY: 50,
        PuzzleDifficulty.MEDIUM: 100,
        PuzzleDifficulty.HARD: 200,
    })

    # --- Medal bonus (added on top of base) ---
    MEDAL_BONUS: dict = field(default_factory=lambda: {
        Medal.NONE: 0,
        Medal.BRONZE: 0,
        Medal.SILVER: 25,
        Medal.GOLD: 50,
    })

    # Creator gets this much XP each time someone solves their puzzle
    SOLVE_REWARD_CREATOR: int = 10

    # Rating XP (ADD): rater gets 5 XP, puzzle creator gets 1 XP.
    rating_rater_xp: int = 5
    rating_creator_xp: int = 1

    # ---- Level calculation ----
    def calculate_level(self, xp_total: int) -> int:
        xp_total = max(0, int(xp_total))
        return floor(sqrt(xp_total / 100)) + 1

    def is_experienced(self, xp_total: int) -> bool:
        return self.calculate_level(xp_total) >= 5

    # ---- Difficulty tier helpers ----
    def tier_from_avg_difficulty(self, avg_difficulty: float) -> PuzzleDifficulty:
        """Map a numeric difficulty rating to a PuzzleDifficulty enum."""
        try:
            d = float(avg_difficulty)
        except Exception:
            d = 1.0
        if d >= 7.0:
            return PuzzleDifficulty.HARD
        if d >= 4.0:
            return PuzzleDifficulty.MEDIUM
        return PuzzleDifficulty.EASY

    # ---- Medal calculation ----
    def calculate_medal(
        self,
        passed: bool,
        time_taken: int,
        time_limit: Optional[int],
        cost_used: int,
        budget: int,
    ) -> Medal:
        """
        Bronze = solved the puzzle.
        Silver = solved + 1 bonus condition (beats timer OR tight budget).
        Gold   = solved + both bonus conditions.
        """
        if not passed:
            return Medal.NONE

        bonus_count = 0

        # Condition 1: Beats the timer
        if time_limit is not None and time_limit > 0 and time_taken <= time_limit:
            bonus_count += 1

        # Condition 2: Tight budget (cost <= budget)
        if budget > 0 and cost_used <= budget:
            bonus_count += 1

        if bonus_count >= 2:
            return Medal.GOLD
        elif bonus_count >= 1:
            return Medal.SILVER
        else:
            return Medal.BRONZE

    # ---- XP for a solve (with delta logic) ----
    def calculate_solve_xp(
        self,
        difficulty: PuzzleDifficulty,
        medal: Medal,
        previous_best_xp: int,
    ) -> int:
        """
        Raw XP = base(difficulty) + medal_bonus(medal).
        Delta  = max(0, raw - previous_best_xp).
        """
        base = self.BASE_XP.get(difficulty, 50)
        bonus = self.MEDAL_BONUS.get(medal, 0)
        raw_xp = base + bonus
        return max(0, raw_xp - previous_best_xp)

    # ---- Arsenal capacity ----
    def get_arsenal_limit(self, xp_total: int) -> int:
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

    # ---- Internal: apply XP delta to user ----
    def _apply_xp(self, user_id: int, delta: int) -> int:
        if delta <= 0:
            return 0
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")
        user.add_xp(delta)
        self.user_repo.update_xp(user_id, user.xp)
        return delta

    # ---- Public award methods ----
    def award_solve_xp(
        self,
        user_id: int,
        difficulty_tier: str = "easy",
        is_first_solve: bool = False,
        timer_beaten: bool = False,
        already_solved_before: bool = False,
        **kwargs,
    ) -> int:
        """Legacy-compatible wrapper. New code should use calculate_solve_xp + _apply_xp directly."""
        diff = PuzzleDifficulty(difficulty_tier.upper()) if difficulty_tier else PuzzleDifficulty.EASY
        base = self.BASE_XP.get(diff, 50)
        return self._apply_xp(user_id, base)

    def award_creator_solve_xp(self, creator_user_id: int, solver_user_id: int) -> int:
        """Award creator XP when someone (other than them) solves their puzzle."""
        if int(creator_user_id) == int(solver_user_id):
            return 0
        return self._apply_xp(creator_user_id, self.SOLVE_REWARD_CREATOR)

    def award_rating_xp(self, rater_user_id: int, creator_user_id: int, first_time_rating: bool) -> int:
        """Award rating XP. Only the first rating per (puzzle,user) grants XP."""
        if not first_time_rating:
            return 0
        total = 0
        total += self._apply_xp(rater_user_id, self.rating_rater_xp)
        if int(creator_user_id) != int(rater_user_id):
            total += self._apply_xp(creator_user_id, self.rating_creator_xp)
        return total
