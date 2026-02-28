import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from Backend.ServiceLayer.XPService import XPService
from Backend.DomainLayer.Enums import PuzzleDifficulty, Medal
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.UserRepo import UserRepo


class TestXPServiceCreation:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_xp_service_initialization(self):
        assert self.service.user_repo == self.mock_user_repo
        assert self.service.BASE_XP[PuzzleDifficulty.EASY] == 50
        assert self.service.BASE_XP[PuzzleDifficulty.MEDIUM] == 100
        assert self.service.BASE_XP[PuzzleDifficulty.HARD] == 200
        assert self.service.SOLVE_REWARD_CREATOR == 10

    def test_medal_bonus_values(self):
        assert self.service.MEDAL_BONUS[Medal.NONE] == 0
        assert self.service.MEDAL_BONUS[Medal.BRONZE] == 0
        assert self.service.MEDAL_BONUS[Medal.SILVER] == 25
        assert self.service.MEDAL_BONUS[Medal.GOLD] == 50


class TestXPServiceCalculateLevel:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_calculate_level_0_xp(self):
        # floor(sqrt(0/100)) + 1 = 1
        level = self.service.calculate_level(0)
        assert level == 1

    def test_calculate_level_below_first_threshold(self):
        # floor(sqrt(99/100)) + 1 = floor(0.99) + 1 = 1
        level = self.service.calculate_level(99)
        assert level == 1

    def test_calculate_level_at_level_2(self):
        # floor(sqrt(100/100)) + 1 = 1 + 1 = 2
        level = self.service.calculate_level(100)
        assert level == 2

    def test_calculate_level_at_level_3(self):
        # floor(sqrt(400/100)) + 1 = 2 + 1 = 3
        level = self.service.calculate_level(400)
        assert level == 3

    def test_calculate_level_between_levels(self):
        # floor(sqrt(350/100)) + 1 = floor(1.87) + 1 = 1 + 1 = 2
        level = self.service.calculate_level(350)
        assert level == 2

    def test_calculate_level_at_level_5(self):
        # floor(sqrt(1600/100)) + 1 = 4 + 1 = 5
        level = self.service.calculate_level(1600)
        assert level == 5

    def test_calculate_level_high_xp(self):
        # floor(sqrt(10000/100)) + 1 = 10 + 1 = 11
        level = self.service.calculate_level(10000)
        assert level == 11

    def test_calculate_level_negative_xp_treated_as_zero(self):
        level = self.service.calculate_level(-100)
        assert level == 1

    def test_calculate_level_progression(self):
        # Level thresholds: (L-1)^2 * 100
        # L=1: 0, L=2: 100, L=3: 400, L=4: 900, L=5: 1600, L=6: 2500
        assert self.service.calculate_level(0) == 1
        assert self.service.calculate_level(100) == 2
        assert self.service.calculate_level(400) == 3
        assert self.service.calculate_level(900) == 4
        assert self.service.calculate_level(1600) == 5
        assert self.service.calculate_level(2500) == 6


class TestXPServiceIsExperienced:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_is_experienced_at_level_5(self):
        # Level 5 requires 1600 XP: floor(sqrt(1600/100)) + 1 = 5
        assert self.service.is_experienced(1600) is True

    def test_is_experienced_above_level_5(self):
        assert self.service.is_experienced(5000) is True

    def test_is_experienced_below_level_5(self):
        # 1599 XP -> level 4
        assert self.service.is_experienced(1599) is False

    def test_is_experienced_level_1(self):
        assert self.service.is_experienced(0) is False

    def test_is_experienced_level_4(self):
        # Level 4 requires 900 XP
        assert self.service.is_experienced(900) is False


class TestXPServiceApplyXP:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_apply_xp_success(self):
        delta = self.service._apply_xp(1, 50)

        assert delta == 50
        self.mock_user_repo.increment_xp.assert_called_once_with(1, 50)

    def test_apply_xp_zero(self):
        delta = self.service._apply_xp(1, 0)

        assert delta == 0
        self.mock_user_repo.increment_xp.assert_not_called()

    def test_apply_xp_negative(self):
        delta = self.service._apply_xp(1, -10)

        assert delta == 0
        self.mock_user_repo.increment_xp.assert_not_called()

    def test_apply_xp_user_not_found(self):
        # increment_xp is a no-op for non-existent users (UPDATE affects 0 rows)
        delta = self.service._apply_xp(999, 50)
        assert delta == 50
        self.mock_user_repo.increment_xp.assert_called_once_with(999, 50)


class TestXPServiceAwardSolveXP:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_calculate_solve_xp_easy_bronze(self):
        # BASE_XP[EASY]=50 + MEDAL_BONUS[BRONZE]=0 = 50, prev=0 -> delta=50
        xp = self.service.calculate_solve_xp(PuzzleDifficulty.EASY, Medal.BRONZE, previous_best_xp=0)
        assert xp == 50

    def test_calculate_solve_xp_medium_silver(self):
        # BASE_XP[MEDIUM]=100 + MEDAL_BONUS[SILVER]=25 = 125, prev=0 -> delta=125
        xp = self.service.calculate_solve_xp(PuzzleDifficulty.MEDIUM, Medal.SILVER, previous_best_xp=0)
        assert xp == 125

    def test_calculate_solve_xp_hard_gold(self):
        # BASE_XP[HARD]=200 + MEDAL_BONUS[GOLD]=50 = 250, prev=0 -> delta=250
        xp = self.service.calculate_solve_xp(PuzzleDifficulty.HARD, Medal.GOLD, previous_best_xp=0)
        assert xp == 250

    def test_calculate_solve_xp_delta_improvement(self):
        # Had bronze (50), now got silver (50+25=75), delta = 75-50 = 25
        xp = self.service.calculate_solve_xp(PuzzleDifficulty.EASY, Medal.SILVER, previous_best_xp=50)
        assert xp == 25

    def test_calculate_solve_xp_no_improvement(self):
        # Had gold (250), same gold again -> delta = 0
        xp = self.service.calculate_solve_xp(PuzzleDifficulty.HARD, Medal.GOLD, previous_best_xp=250)
        assert xp == 0

    def test_calculate_solve_xp_downgrade_no_negative(self):
        # Had gold (250), now bronze (200) -> delta = max(0, 200-250) = 0
        xp = self.service.calculate_solve_xp(PuzzleDifficulty.HARD, Medal.BRONZE, previous_best_xp=250)
        assert xp == 0

    def test_award_creator_solve_xp(self):
        creator = User(id=2, username="creator", xp=0)
        self.mock_user_repo.get_by_id.return_value = creator

        xp = self.service.award_creator_solve_xp(creator_user_id=2, solver_user_id=1)
        assert xp == 10  # SOLVE_REWARD_CREATOR

    def test_award_creator_solve_xp_same_user(self):
        # Creator solving own puzzle gets no creator bonus
        xp = self.service.award_creator_solve_xp(creator_user_id=1, solver_user_id=1)
        assert xp == 0


class TestXPServiceAwardRatingXP:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_award_rating_xp_first_time(self):
        xp_awarded = self.service.award_rating_xp(rater_user_id=1, creator_user_id=2, first_time_rating=True)

        assert xp_awarded == 6  # 5 for rater, 1 for creator
        # Verify atomic increments were called
        self.mock_user_repo.increment_xp.assert_any_call(1, 5)  # rater
        self.mock_user_repo.increment_xp.assert_any_call(2, 1)  # creator

    def test_award_rating_xp_not_first_time(self):
        rater = User(id=1, username="user", xp=100)
        creator = User(id=2, username="creator", xp=50)
        def get_by_id_side_effect(uid):
            if uid == 1:
                return rater
            elif uid == 2:
                return creator
            return None
        self.mock_user_repo.get_by_id.side_effect = get_by_id_side_effect

        xp_awarded = self.service.award_rating_xp(rater_user_id=1, creator_user_id=2, first_time_rating=False)

        assert xp_awarded == 0
        assert rater.xp == 100  # No change
        assert creator.xp == 50  # No change
        self.mock_user_repo.update_xp.assert_not_called()


class TestXPServiceLevelFormula:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_level_formula_consistency(self):
        # Verify floor(sqrt(xp/100)) + 1 at boundary values
        # Level L requires (L-1)^2 * 100 XP 
        for L in range(1, 15):
            threshold = (L - 1) ** 2 * 100
            assert self.service.calculate_level(threshold) == L

    def test_level_5_is_experienced(self):
        # Level 5 requires (5-1)^2 * 100 = 1600 XP
        assert self.service.calculate_level(1600) == 5
        assert self.service.is_experienced(1600) is True
        assert self.service.is_experienced(1599) is False


class TestXPServiceMedalCalculation:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_medal_not_passed(self):
        medal = self.service.calculate_medal(passed=False, time_taken=10, time_limit=60, cost_used=5, budget=10)
        assert medal == Medal.NONE

    def test_medal_bronze_no_conditions(self):
        # Solved but neither timer beaten nor budget met
        medal = self.service.calculate_medal(passed=True, time_taken=100, time_limit=60, cost_used=15, budget=10)
        assert medal == Medal.BRONZE

    def test_medal_silver_timer_only(self):
        # Beats timer but over budget
        medal = self.service.calculate_medal(passed=True, time_taken=30, time_limit=60, cost_used=15, budget=10)
        assert medal == Medal.SILVER

    def test_medal_silver_budget_only(self):
        # Under budget but over timer
        medal = self.service.calculate_medal(passed=True, time_taken=100, time_limit=60, cost_used=5, budget=10)
        assert medal == Medal.SILVER

    def test_medal_gold_both_conditions(self):
        # Both conditions met
        medal = self.service.calculate_medal(passed=True, time_taken=30, time_limit=60, cost_used=5, budget=10)
        assert medal == Medal.GOLD

    def test_medal_bronze_no_time_limit(self):
        # No time limit set, over budget -> only budget condition could count
        medal = self.service.calculate_medal(passed=True, time_taken=10, time_limit=None, cost_used=15, budget=10)
        assert medal == Medal.BRONZE

    def test_medal_silver_no_time_limit_but_under_budget(self):
        # No time limit, under budget -> 1 condition
        medal = self.service.calculate_medal(passed=True, time_taken=10, time_limit=None, cost_used=5, budget=10)
        assert medal == Medal.SILVER
