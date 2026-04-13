from dataclasses import dataclass, field
from math import floor, sqrt
from typing import Optional

from Backend import settings
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
    - Level = floor(sqrt(xp / settings.LEVEL_XP_DIVISOR)) + 1
    """
    user_repo: UserRepo

    # --- Base XP per difficulty ---
    BASE_XP: dict = field(default_factory=lambda: {
        PuzzleDifficulty.EASY:   settings.XP_SOLVE_EASY,
        PuzzleDifficulty.MEDIUM: settings.XP_SOLVE_MEDIUM,
        PuzzleDifficulty.HARD:   settings.XP_SOLVE_HARD,
    })

    # --- Medal bonus (added on top of base) ---
    MEDAL_BONUS: dict = field(default_factory=lambda: {
        Medal.NONE:   settings.XP_MEDAL_BONUS_NONE,
        Medal.BRONZE: settings.XP_MEDAL_BONUS_BRONZE,
        Medal.SILVER: settings.XP_MEDAL_BONUS_SILVER,
        Medal.GOLD:   settings.XP_MEDAL_BONUS_GOLD,
    })

    # Creator gets this much XP each time someone solves their puzzle
    SOLVE_REWARD_CREATOR: int = settings.XP_SOLVE_REWARD_CREATOR

    # Rating XP: rater and puzzle creator each receive a small award
    rating_rater_xp: int = settings.XP_RATING_RATER
    rating_creator_xp: int = settings.XP_RATING_CREATOR

    # ---- Level calculation ----
    def calculate_level(self, xp_total: int) -> int:
        xp_total = max(0, int(xp_total))
        return floor(sqrt(xp_total / settings.LEVEL_XP_DIVISOR)) + 1

    def calculate_xp_for_level(self, level: int) -> int:
        """Return the minimum XP required to reach the given level."""
        lvl = max(1, int(level))
        return ((lvl - 1) ** 2) * settings.LEVEL_XP_DIVISOR

    def is_experienced(self, xp_total: int) -> bool:
        return self.calculate_level(xp_total) >= settings.EXPERIENCED_LEVEL_MIN

    # ---- Difficulty tier helpers ----
    def tier_from_avg_difficulty(self, avg_difficulty: float) -> PuzzleDifficulty:
        """Map a numeric difficulty rating to a PuzzleDifficulty enum."""
        try:
            d = float(avg_difficulty)
        except Exception:
            d = 1.0
        if d >= settings.DIFFICULTY_HARD_THRESHOLD:
            return PuzzleDifficulty.HARD
        if d >= settings.DIFFICULTY_MEDIUM_THRESHOLD:
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
        creator_budget: Optional[int] = None,
    ) -> Medal:
        """
        Bronze = solved the puzzle.
        Silver = solved + 1 bonus condition (beats timer OR matches/beats creator cost).
        Gold   = solved + both bonus conditions.

        creator_budget: the creator's solution cost. If set, the solver earns a bonus
                        by achieving cost <= creator_budget (beating the creator's cost).
        """
        if not passed:
            return Medal.NONE

        bonus_count = 0

        # Condition 1: Beats the timer (or no time limit exists)
        # When time_limit is None or 0, automatically award timer bonus (no time pressure)
        if time_limit is None or time_limit == 0 or time_taken <= time_limit:
            bonus_count += 1

        # Condition 2: Creator Budget (cost <= creator's solution cost)
        if creator_budget is not None and creator_budget > 0 and cost_used <= creator_budget:
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
        for max_level, slots in settings.ARSENAL_XP_LEVEL_TIERS:
            if lvl <= max_level:
                return slots
        return settings.ARSENAL_XP_MAX_SLOTS

    # ---- Internal: apply XP delta to user ----
    def _apply_xp(self, user_id: int, delta: int) -> int:
        if delta <= 0:
            return 0
        self.user_repo.increment_xp(user_id, delta)
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
