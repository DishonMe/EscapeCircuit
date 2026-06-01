"""
Unit tests that pin the configuration constants ADD Chapter 7.2 references.

Several rows in ADD 7.2 are "settings.py / Reference <CONSTANT> / Check value /
Equals <X>" assertions, plus the XPService BASE_XP / MEDAL_BONUS / reward
mappings.  This file proves those documented values actually live in the code,
so the design document and the implementation cannot silently drift apart.

Target module: Backend/settings.py  (+ XPService mappings derived from it).
"""
from unittest.mock import Mock

from Backend import settings
from Backend.ServiceLayer.XPService import XPService
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.DomainLayer.Enums import PuzzleDifficulty, Medal


# ── 7.2.1 Circuit Cost and Board Constraints (settings rows) ──────────────────

def test_puzzle_name_max_length():
    """ADD 7.2.1 — PUZZLE_NAME_MAX_LENGTH equals 100."""
    assert settings.PUZZLE_NAME_MAX_LENGTH == 100


def test_puzzle_description_max_length():
    """ADD 7.2.1 — PUZZLE_DESCRIPTION_MAX_LENGTH equals 2000.

    NOTE: this is the authoritative value. The UC4 prose (ADD p.16) saying
    'description <= 500' is outdated — see TEST_PLAN_ADD_MAP.txt for the
    documented correction.
    """
    assert settings.PUZZLE_DESCRIPTION_MAX_LENGTH == 2000


# ── 7.2.2 XP and Rewards Calculation (XPService + settings) ───────────────────

def test_base_xp_per_difficulty():
    """ADD 7.2.2 — BASE_XP: EASY=50, MEDIUM=100, HARD=200."""
    xp = XPService(Mock(spec=UserRepo))
    assert xp.BASE_XP[PuzzleDifficulty.EASY] == 50
    assert xp.BASE_XP[PuzzleDifficulty.MEDIUM] == 100
    assert xp.BASE_XP[PuzzleDifficulty.HARD] == 200


def test_medal_bonus_values():
    """ADD 7.2.2 — MEDAL_BONUS: SILVER=25, GOLD=50 (NONE/BRONZE=0)."""
    xp = XPService(Mock(spec=UserRepo))
    assert xp.MEDAL_BONUS[Medal.NONE] == 0
    assert xp.MEDAL_BONUS[Medal.BRONZE] == 0
    assert xp.MEDAL_BONUS[Medal.SILVER] == 25
    assert xp.MEDAL_BONUS[Medal.GOLD] == 50


def test_creator_solve_reward():
    """ADD 7.2.2 — SOLVE_REWARD_CREATOR (XP_SOLVE_REWARD_CREATOR) equals 10."""
    assert settings.XP_SOLVE_REWARD_CREATOR == 10


def test_rating_xp_rewards():
    """ADD 7.2.3 — first-time rating awards rater 5 XP, creator 1 XP."""
    assert settings.XP_RATING_RATER == 5
    assert settings.XP_RATING_CREATOR == 1


def test_level_formula_constants():
    """ADD 7.2.2 — LEVEL_XP_DIVISOR=100 and the real worked examples.

    level = floor(sqrt(xp / 100)) + 1  →  400 XP = level 3 (ADD example is
    correct).

    CORRECTION: the ADD's "experienced" example row is off by one (it dropped
    the '+1' in the formula). The real mapping is 900 XP = level 4 (NOT
    experienced) and 1600 XP = level 5 (experienced) — NOT 1600=level4 /
    2500=level5 as the ADD states. See TEST_PLAN_ADD_MAP.txt. The code is the
    source of truth; this test pins the real behaviour.
    """
    assert settings.LEVEL_XP_DIVISOR == 100
    xp = XPService(Mock(spec=UserRepo))
    assert xp.calculate_level(400) == 3
    assert xp.calculate_level(900) == 4
    assert xp.calculate_level(1600) == 5
    assert xp.calculate_level(2500) == 6
    # EXPERIENCED_LEVEL_MIN == 5: level 4 is not experienced, level 5 is.
    assert xp.is_experienced(900) is False     # level 4
    assert xp.is_experienced(1600) is True      # level 5


def test_experienced_level_min():
    """ADD 7.2.2 — EXPERIENCED_LEVEL_MIN equals 5."""
    assert settings.EXPERIENCED_LEVEL_MIN == 5


# ── 7.2.3 Rating System Weighting (settings rows) ─────────────────────────────

def test_rating_user_count_threshold():
    """ADD 7.2.3 — RATING_USER_COUNT_THRESHOLD equals 10."""
    assert settings.RATING_USER_COUNT_THRESHOLD == 10


def test_rating_diff_weight_few_ratings():
    """ADD 7.2.3 — RATING_DIFF_WEIGHT_FEW_RATINGS equals (0.8, 0.2)."""
    assert settings.RATING_DIFF_WEIGHT_FEW_RATINGS == (0.8, 0.2)


def test_rating_diff_weight_many_ratings():
    """ADD 7.2.3 — RATING_DIFF_WEIGHT_MANY_RATINGS equals (0.4, 0.6)."""
    assert settings.RATING_DIFF_WEIGHT_MANY_RATINGS == (0.4, 0.6)


def test_rating_difficulty_map():
    """ADD 7.2.3 — RATING_DIFFICULTY_MAP equals {EASY:1, MEDIUM:3, HARD:5}."""
    assert settings.RATING_DIFFICULTY_MAP == {"EASY": 1, "MEDIUM": 3, "HARD": 5}


def test_rating_min_attempt_seconds():
    """ADD 7.2.3 — _can_rate threshold (RATING_MIN_ATTEMPT_SECONDS) equals 300."""
    assert settings.RATING_MIN_ATTEMPT_SECONDS == 300
