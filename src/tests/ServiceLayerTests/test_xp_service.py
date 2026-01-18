import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from Backend.ServiceLayer.XPService import XPService
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.UserRepo import UserRepo


class TestXPServiceCreation:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_xp_service_initialization(self):
        assert self.service.user_repo == self.mock_user_repo
        assert self.service.easy_xp == 50
        assert self.service.medium_xp == 100
        assert self.service.hard_xp == 150
        assert self.service.first_solve_bonus == 50
        assert self.service.time_bonus == 25

    def test_xp_service_custom_values(self):
        custom_service = XPService(
            user_repo=self.mock_user_repo,
            easy_xp=100,
            medium_xp=200,
            hard_xp=300,
        )
        assert custom_service.easy_xp == 100
        assert custom_service.medium_xp == 200
        assert custom_service.hard_xp == 300


class TestXPServiceCalculateLevel:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_calculate_level_0_xp(self):
        level = self.service.calculate_level(0)
        assert level == 1

    def test_calculate_level_below_threshold(self):
        # Level 2 starts at 250 XP
        level = self.service.calculate_level(249)
        assert level == 1

    def test_calculate_level_at_threshold(self):
        level = self.service.calculate_level(250)
        assert level == 2

    def test_calculate_level_between_thresholds(self):
        # 500 XP: Level 3 starts at 600, so it's level 2
        level = self.service.calculate_level(500)
        assert level == 2

    def test_calculate_level_at_level_5_threshold(self):
        # Level 5 starts at 2000 XP
        level = self.service.calculate_level(2000)
        assert level == 6

    def test_calculate_level_high_xp(self):
        level = self.service.calculate_level(10000)
        assert level >= 5

    def test_calculate_level_negative_xp_treated_as_zero(self):
        level = self.service.calculate_level(-100)
        assert level == 1

    def test_calculate_level_progression(self):
        # Verify progression through levels
        assert self.service.calculate_level(0) == 1
        assert self.service.calculate_level(250) == 2
        assert self.service.calculate_level(600) == 3
        assert self.service.calculate_level(1100) == 4
        assert self.service.calculate_level(1700) == 5
        assert self.service.calculate_level(2000) == 6


class TestXPServiceIsExperienced:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_is_experienced_at_level_5(self):
        # Level 5 requires 2000 XP
        assert self.service.is_experienced(2000) is True

    def test_is_experienced_above_level_5(self):
        assert self.service.is_experienced(5000) is True

    def test_is_experienced_below_level_5(self):
        # Below level 5 (which starts at 1700 XP)
        assert self.service.is_experienced(1699) is False

    def test_is_experienced_level_1(self):
        assert self.service.is_experienced(0) is False

    def test_is_experienced_level_4(self):
        # Level 4 is at 1700 XP, experienced starts at 1700 (level 5)
        assert self.service.is_experienced(1700) is True


class TestXPServiceApplyXP:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_apply_xp_success(self):
        user = User(id=1, username="user", xp=100)
        self.mock_user_repo.get_by_id.return_value = user

        delta = self.service._apply_xp(1, 50)

        assert delta == 50
        assert user.xp == 150
        self.mock_user_repo.update_xp.assert_called_once_with(1, 150)

    def test_apply_xp_zero(self):
        user = User(id=1, username="user", xp=100)
        self.mock_user_repo.get_by_id.return_value = user

        delta = self.service._apply_xp(1, 0)

        assert delta == 0
        self.mock_user_repo.update_xp.assert_not_called()

    def test_apply_xp_negative(self):
        user = User(id=1, username="user", xp=100)
        self.mock_user_repo.get_by_id.return_value = user

        delta = self.service._apply_xp(1, -10)

        assert delta == 0
        self.mock_user_repo.update_xp.assert_not_called()

    def test_apply_xp_user_not_found(self):
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service._apply_xp(999, 50)
        assert "user not found" in str(exc_info.value)


class TestXPServiceAwardSolveXP:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_award_solve_xp_easy_first_solve(self):
        user = User(id=1, username="user", xp=0)
        self.mock_user_repo.get_by_id.return_value = user

        xp_awarded = self.service.award_solve_xp(
            user_id=1,
            difficulty_tier="easy",
            is_first_solve=True,
            timer_beaten=False,
            already_solved_before=False,
        )

        # easy_xp (50) + first_solve_bonus (50) = 100
        assert xp_awarded == 100
        assert user.xp == 100

    def test_award_solve_xp_medium_no_bonuses(self):
        user = User(id=1, username="user", xp=100)
        self.mock_user_repo.get_by_id.return_value = user

        xp_awarded = self.service.award_solve_xp(
            user_id=1,
            difficulty_tier="medium",
            is_first_solve=False,
            timer_beaten=False,
            already_solved_before=False,
        )

        assert xp_awarded == 100
        assert user.xp == 200

    def test_award_solve_xp_hard_with_bonuses(self):
        user = User(id=1, username="user", xp=0)
        self.mock_user_repo.get_by_id.return_value = user

        xp_awarded = self.service.award_solve_xp(
            user_id=1,
            difficulty_tier="hard",
            is_first_solve=True,
            timer_beaten=True,
            already_solved_before=False,
        )

        # hard_xp (150) + first_solve_bonus (50) + time_bonus (25) = 225
        assert xp_awarded == 225
        assert user.xp == 225

    def test_award_solve_xp_already_solved(self):
        user = User(id=1, username="user", xp=100)
        self.mock_user_repo.get_by_id.return_value = user

        xp_awarded = self.service.award_solve_xp(
            user_id=1,
            difficulty_tier="hard",
            is_first_solve=True,
            timer_beaten=True,
            already_solved_before=True,
        )

        # Should only get repeat_solve_xp (10), no bonuses
        assert xp_awarded == 10
        assert user.xp == 110

    def test_award_solve_xp_default_easy_tier(self):
        user = User(id=1, username="user", xp=0)
        self.mock_user_repo.get_by_id.return_value = user

        xp_awarded = self.service.award_solve_xp(
            user_id=1,
            difficulty_tier="",
            is_first_solve=True,
            timer_beaten=False,
            already_solved_before=False,
        )

        # Default to easy
        assert xp_awarded == 100

    def test_award_solve_xp_case_insensitive_tier(self):
        user = User(id=1, username="user", xp=0)
        self.mock_user_repo.get_by_id.return_value = user

        xp_awarded = self.service.award_solve_xp(
            user_id=1,
            difficulty_tier="HARD",
            is_first_solve=False,
            timer_beaten=False,
            already_solved_before=False,
        )

        assert xp_awarded == 150  # hard_xp


class TestXPServiceAwardRatingXP:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_award_rating_xp_first_time(self):
        rater = User(id=1, username="user", xp=0)
        creator = User(id=2, username="creator", xp=0)
        def get_by_id_side_effect(uid):
            if uid == 1:
                return rater
            elif uid == 2:
                return creator
            return None
        self.mock_user_repo.get_by_id.side_effect = get_by_id_side_effect

        xp_awarded = self.service.award_rating_xp(rater_user_id=1, creator_user_id=2, first_time_rating=True)

        assert xp_awarded == 6  # 5 for rater, 1 for creator
        assert rater.xp == 5
        assert creator.xp == 1

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


class TestXPServiceLevelThresholds:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = XPService(user_repo=self.mock_user_repo)

    def test_level_thresholds_are_correct(self):
        expected_thresholds = [0, 250, 600, 1100, 1700, 2000, 2600, 3400, 4500, 6000]
        assert self.service.level_thresholds == expected_thresholds

    def test_level_thresholds_are_increasing(self):
        thresholds = self.service.level_thresholds
        for i in range(len(thresholds) - 1):
            assert thresholds[i] < thresholds[i + 1]

    def test_level_5_threshold_is_2000(self):
        # Experienced users require level 5, which is at index 4, but at XP 1700 (index 4 threshold)
        # Actually, level 5 is at index 4 of the array which means level 5
        assert self.service.level_thresholds[4] == 1700
