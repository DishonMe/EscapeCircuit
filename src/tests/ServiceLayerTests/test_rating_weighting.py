"""
Unit tests for the rating-weighting helpers on RatingService.

Fulfils the "Rating System Weighting" unit-test rows promised in ADD
Chapter 7.2.3 that target RatingService.py specifically:

    • "Weighted average calculation"  → _weighted_avg([2,3,5],[1,2,1]) == 3.25
    • "Creator dual-weight for experienced raters" → _exp_weight == 2 / 1
    • "Rating distribution counting"  → difficulty_dist over [2,3,3,4,5]

The two helpers are pure static methods, so they are tested in isolation.
The distribution counting lives inside get_puzzle_metrics, so we exercise it
with mocked repos (the established ServiceLayerTests pattern).
"""
from unittest.mock import Mock

import pytest

from Backend.ServiceLayer.RatingService import RatingService
from Backend.PersistantLayer.RatingRepo import RatingRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService
from Backend.DomainLayer.Rating import Rating
from Backend.DomainLayer.Puzzle import Puzzle


# ── _weighted_avg (pure static) ──────────────────────────────────────────────

def test_weighted_avg_matches_add_example():
    """ADD 7.2.3 — _weighted_avg([2,3,5],[1,2,1]) = (2*1+3*2+5*1)/4 = 3.25."""
    assert RatingService._weighted_avg([2, 3, 5], [1, 2, 1]) == 3.25


def test_weighted_avg_zero_weight_returns_none():
    """Guard branch: total weight 0 → None (avoids divide-by-zero)."""
    assert RatingService._weighted_avg([4, 5], [0, 0]) is None


# ── _exp_weight (pure static) ────────────────────────────────────────────────

@pytest.mark.parametrize("experienced,expected", [(True, 2), (False, 1)])
def test_exp_weight_dual_weighting(experienced, expected):
    """ADD 7.2.3 — experienced raters weigh 2, non-experienced weigh 1."""
    rating = Rating(
        id=1, puzzle_id=1, user_id=1, difficulty=3, fun=3, clearness=3,
        is_experienced_at_rating=experienced,
    )
    assert RatingService._exp_weight(rating) == expected


# ── difficulty distribution counting (via get_puzzle_metrics) ────────────────

def _service_with_ratings(ratings, creator_difficulty="EASY"):
    rating_repo = Mock(spec=RatingRepo)
    puzzle_repo = Mock(spec=PuzzleRepo)
    service = RatingService(
        rating_repo, puzzle_repo, Mock(spec=SolveRepo),
        Mock(spec=AuthService), Mock(spec=XPService),
    )
    puzzle_repo.get_by_id.return_value = Puzzle(
        id=1, name="P", creator_user_id=2, difficulty=creator_difficulty
    )
    rating_repo.list_by_puzzle.return_value = ratings
    return service


def test_rating_distribution_counting():
    """ADD 7.2.3 — 5 difficulty scores [2,3,3,4,5] → counts {2:1, 3:2, 4:1, 5:1}.

    rating_distribution['difficulty'] is the 1..5 slice, so indices map as
    [count(1), count(2), count(3), count(4), count(5)].
    """
    scores = [2, 3, 3, 4, 5]
    ratings = [
        Rating(id=i + 1, puzzle_id=1, user_id=100 + i, difficulty=s, fun=3, clearness=3)
        for i, s in enumerate(scores)
    ]
    service = _service_with_ratings(ratings)

    metrics = service.get_puzzle_metrics(1)
    dist = metrics["rating_distribution"]["difficulty"]  # [d1, d2, d3, d4, d5]

    assert metrics["count"] == 5
    assert dist == [0, 1, 2, 1, 1]
