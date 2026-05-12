"""Coverage tests for RatingService — focus on the submit/update wrappers,
_can_rate fallback time computation, edit-flow ("rating not found"),
notification of creator, get_puzzle_metrics edge cases, hall-of-fame
trigger, and remove_rating recalculation branch."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch

import pytest

from Backend.ServiceLayer.RatingService import RatingService
from Backend.DomainLayer.Rating import Rating
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Enums import PuzzleDifficulty


def _make_service():
    rating_repo = MagicMock()
    rating_repo.conn = MagicMock()
    puzzle_repo = MagicMock()
    solve_repo = MagicMock()
    auth = MagicMock()
    xp = MagicMock()
    notif = MagicMock()
    svc = RatingService(rating_repo, puzzle_repo, solve_repo, auth, xp, notification_service=notif)
    return svc, rating_repo, puzzle_repo, solve_repo, auth, xp, notif


def _puzzle(pid=1, creator_id=2, diff=PuzzleDifficulty.MEDIUM):
    p = Mock()
    p.id = pid
    p.creator_user_id = creator_id
    p.difficulty = diff
    p.name = "Test"
    return p


def _rating(rid=1, pid=1, uid=1, difficulty=3, fun=4, clearness=5, experienced=False):
    return Rating(
        id=rid, puzzle_id=pid, user_id=uid,
        difficulty=difficulty, fun=fun, clearness=clearness,
        is_experienced_at_rating=experienced,
    )


# ---------------------------------------------------------------------------
# submit_rating / update_rating wrappers — to_dict and dict fallback paths
# ---------------------------------------------------------------------------

class TestSubmitUpdateWrappers:
    def test_submit_rating_to_dict_path(self):
        svc, rating_repo, puzzle_repo, solve_repo, auth, xp, _ = _make_service()
        auth.require_user_id.return_value = 1
        puzzle_repo.get_by_id.return_value = _puzzle()
        rating_repo.get_by_puzzle_user.return_value = None  # first-time rating
        solve_repo.has_passed.return_value = True
        rating_repo.try_mark_xp_awarded.return_value = True
        auth.user_repo = Mock()
        auth.user_repo.get_by_id.return_value = Mock(xp=100)
        xp.is_experienced.return_value = False

        saved = _rating()
        rating_repo.upsert.return_value = saved
        result = svc.submit_rating("tok", 1, {"difficulty": 3, "fun": 4, "clearness": 5})
        assert isinstance(result, dict)
        assert result["difficulty"] == 3

    def test_update_rating_passes_elapsed_seconds(self):
        svc, rating_repo, puzzle_repo, solve_repo, auth, xp, _ = _make_service()
        auth.require_user_id.return_value = 1
        puzzle_repo.get_by_id.return_value = _puzzle()
        # Existing rating — allow_existing=True path
        rating_repo.get_by_puzzle_user.return_value = _rating()
        solve_repo.has_passed.return_value = True
        auth.user_repo = Mock()
        auth.user_repo.get_by_id.return_value = Mock(xp=100)
        xp.is_experienced.return_value = False
        rating_repo.upsert.return_value = _rating(difficulty=5, fun=5, clearness=5)
        rating_repo.try_mark_xp_awarded.return_value = False  # not first-time

        result = svc.update_rating("tok", 1, {
            "difficulty": 5, "fun": 5, "clearness": 5, "elapsed_seconds": 600
        })
        assert result["difficulty"] == 5

    def test_update_rating_not_found_raises(self):
        svc, rating_repo, puzzle_repo, *_, auth, _, _ = _make_service()
        auth.require_user_id.return_value = 1
        puzzle_repo.get_by_id.return_value = _puzzle()
        # No existing rating but allow_existing=True → "rating not found"
        rating_repo.get_by_puzzle_user.return_value = None
        with pytest.raises(ValidationError, match="rating not found"):
            svc.update_rating("tok", 1, {"difficulty": 3, "fun": 4, "clearness": 5})


# ---------------------------------------------------------------------------
# _can_rate — fallback elapsed paths
# ---------------------------------------------------------------------------

class TestCanRateFallbackPaths:
    def setup_method(self):
        (self.svc, self.rating_repo, _, self.solve_repo, *_) = _make_service()
        self.rating_repo.get_by_puzzle_user.return_value = None  # no existing rating
        self.solve_repo.has_passed.return_value = False

    def test_no_first_started_falls_through(self):
        # No total time, no first_started → check returns False
        self.solve_repo.get_total_time_on_puzzle.return_value = 0
        self.solve_repo.first_attempt_started_at.return_value = None
        assert self.svc._can_rate(1, 1, client_elapsed=0) is False

    def test_first_started_invalid_iso_swallowed(self):
        self.solve_repo.get_total_time_on_puzzle.return_value = 0
        self.solve_repo.first_attempt_started_at.return_value = "not-an-iso-date"
        assert self.svc._can_rate(1, 1, client_elapsed=0) is False

    def test_first_started_old_enough_passes(self):
        # Attempt started 10 minutes ago — should comfortably exceed threshold
        ten_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        self.solve_repo.get_total_time_on_puzzle.return_value = 0
        self.solve_repo.first_attempt_started_at.return_value = ten_min_ago
        assert self.svc._can_rate(1, 1, client_elapsed=0) is True

    def test_total_time_exceeds_threshold(self):
        self.solve_repo.get_total_time_on_puzzle.return_value = 999999
        self.solve_repo.first_attempt_started_at.return_value = None
        assert self.svc._can_rate(1, 1, client_elapsed=0) is True

    def test_client_elapsed_exceeds_threshold(self):
        self.solve_repo.get_total_time_on_puzzle.return_value = 0
        self.solve_repo.first_attempt_started_at.return_value = None
        assert self.svc._can_rate(1, 1, client_elapsed=999999) is True

    def test_existing_rating_always_allowed(self):
        self.rating_repo.get_by_puzzle_user.return_value = _rating()
        # Even with no solve and no time
        self.solve_repo.has_passed.return_value = False
        self.solve_repo.get_total_time_on_puzzle.return_value = 0
        assert self.svc._can_rate(1, 1, client_elapsed=0) is True


# ---------------------------------------------------------------------------
# _store_rating — notification path (success + exception swallowed)
# ---------------------------------------------------------------------------

class TestStoreRatingNotification:
    def _setup(self):
        svc, rating_repo, puzzle_repo, solve_repo, auth, xp, notif = _make_service()
        auth.require_user_id.return_value = 1
        puzzle_repo.get_by_id.return_value = _puzzle(creator_id=99)  # creator != rater
        rating_repo.get_by_puzzle_user.return_value = None
        solve_repo.has_passed.return_value = True
        rating_repo.try_mark_xp_awarded.return_value = True
        auth.user_repo = Mock()
        rater = Mock(xp=100, username="rater")
        auth.user_repo.get_by_id.return_value = rater
        xp.is_experienced.return_value = False
        rating_repo.upsert.return_value = _rating()
        return svc, notif

    def test_notify_creator_called_when_first_time_other_user(self):
        svc, notif = self._setup()
        svc.submit_rating("tok", 1, {"difficulty": 3, "fun": 4, "clearness": 5})
        notif.notify_creator_rating.assert_called_once()

    def test_notify_exception_swallowed(self):
        svc, notif = self._setup()
        notif.notify_creator_rating.side_effect = Exception("network down")
        # Should not raise
        svc.submit_rating("tok", 1, {"difficulty": 3, "fun": 4, "clearness": 5})

    def test_self_rating_no_notification(self):
        svc, rating_repo, puzzle_repo, solve_repo, auth, xp, notif = _make_service()
        auth.require_user_id.return_value = 99
        # creator == rater
        puzzle_repo.get_by_id.return_value = _puzzle(creator_id=99)
        rating_repo.get_by_puzzle_user.return_value = None
        solve_repo.has_passed.return_value = True
        rating_repo.try_mark_xp_awarded.return_value = True
        auth.user_repo = Mock()
        auth.user_repo.get_by_id.return_value = Mock(xp=100, username="self")
        xp.is_experienced.return_value = False
        rating_repo.upsert.return_value = _rating()
        svc.submit_rating("tok", 1, {"difficulty": 3, "fun": 4, "clearness": 5})
        notif.notify_creator_rating.assert_not_called()


# ---------------------------------------------------------------------------
# get_puzzle_metrics — no puzzle, distribution out-of-range, exp metrics
# ---------------------------------------------------------------------------

class TestPuzzleMetricsEdgeCases:
    def test_no_puzzle_returns_empty(self):
        svc, _, puzzle_repo, *_ = _make_service()
        puzzle_repo.get_by_id.return_value = None
        assert svc.get_puzzle_metrics(1) == {}

    def test_distribution_skips_out_of_range_values(self):
        # Distribution histogram should ignore values outside [1,5].
        # The Rating domain object enforces that range, so we use Mock objects
        # to simulate corrupted/legacy data that bypasses domain validation.
        svc, rating_repo, puzzle_repo, *_ = _make_service()
        puzzle_repo.get_by_id.return_value = _puzzle()
        bad = Mock(difficulty=6, fun=7, clearness=0, is_experienced_at_rating=False)
        good = Mock(difficulty=3, fun=4, clearness=5, is_experienced_at_rating=False)
        rating_repo.list_by_puzzle.return_value = [bad, good]
        result = svc.get_puzzle_metrics(1)
        assert result["rating_distribution"]["difficulty"] == [0, 0, 1, 0, 0]
        assert result["rating_distribution"]["fun"] == [0, 0, 0, 1, 0]
        assert result["rating_distribution"]["clearness"] == [0, 0, 0, 0, 1]

    def test_experienced_metrics_when_present(self):
        svc, rating_repo, puzzle_repo, *_ = _make_service()
        puzzle_repo.get_by_id.return_value = _puzzle()
        rating_repo.list_by_puzzle.return_value = [
            _rating(difficulty=4, fun=5, clearness=5, experienced=True),
            _rating(difficulty=2, fun=3, clearness=3, experienced=False),
        ]
        result = svc.get_puzzle_metrics(1)
        # Only the experienced rating goes into experienced_metrics
        assert result["experienced_metrics"]["count"] == 1
        assert result["experienced_metrics"]["experienced_avg_fun"] == 5

    def test_no_ratings_yields_none_metrics(self):
        svc, rating_repo, puzzle_repo, *_ = _make_service()
        puzzle_repo.get_by_id.return_value = _puzzle()
        rating_repo.list_by_puzzle.return_value = []
        result = svc.get_puzzle_metrics(1)
        assert result["count"] == 0
        assert result["avg_fun"] is None
        assert result["experienced_metrics"]["count"] == 0
        assert result["experienced_metrics"]["experienced_avg_fun"] is None


# ---------------------------------------------------------------------------
# _recalculate_and_store — many-ratings averages + hall-of-fame trigger
# ---------------------------------------------------------------------------

class TestRecalculateAndStore:
    def test_skips_when_puzzle_missing(self):
        svc, _, puzzle_repo, *_ = _make_service()
        puzzle_repo.get_by_id.return_value = None
        svc._recalculate_and_store(1)  # Should not raise; update_rating_aggregates not called
        puzzle_repo.update_rating_aggregates.assert_not_called()

    def test_zero_ratings_writes_zero(self):
        svc, rating_repo, puzzle_repo, *_ = _make_service()
        puzzle_repo.get_by_id.return_value = _puzzle()
        rating_repo.list_by_puzzle.return_value = []
        svc._recalculate_and_store(1)
        puzzle_repo.update_rating_aggregates.assert_called_once_with(
            1, rating_count=0, avg_difficulty=0.0, avg_fun=0.0, avg_clearness=0.0
        )

    def test_hall_of_fame_triggered_at_20_ratings_above_3_5(self):
        svc, rating_repo, puzzle_repo, *_ = _make_service()
        puzzle_repo.get_by_id.return_value = _puzzle()
        # 20 ratings all fun=5 → avg_fun=5 > 3.5 and count >= 20
        rating_repo.list_by_puzzle.return_value = [_rating(fun=5) for _ in range(20)]
        svc._recalculate_and_store(1)
        puzzle_repo.mark_hall_of_fame.assert_called_once_with(1)

    def test_no_hall_of_fame_below_threshold(self):
        svc, rating_repo, puzzle_repo, *_ = _make_service()
        puzzle_repo.get_by_id.return_value = _puzzle()
        # Only 19 ratings → don't enter hall of fame
        rating_repo.list_by_puzzle.return_value = [_rating(fun=5) for _ in range(19)]
        svc._recalculate_and_store(1)
        puzzle_repo.mark_hall_of_fame.assert_not_called()


# ---------------------------------------------------------------------------
# remove_rating — found & not-found paths
# ---------------------------------------------------------------------------

class TestRemoveRatingPaths:
    def test_remove_recalculates_when_deletion_succeeds(self):
        svc, rating_repo, puzzle_repo, *_, auth, _, _ = _make_service()
        auth.require_user_id.return_value = 1
        puzzle_repo.get_by_id.return_value = _puzzle()
        rating_repo.list_by_puzzle.return_value = []
        cursor = Mock()
        cursor.rowcount = 1
        rating_repo.conn.execute.return_value = cursor
        assert svc.remove_rating("tok", 1) is True
        puzzle_repo.update_rating_aggregates.assert_called_once()

    def test_remove_skip_recalculate_when_nothing_deleted(self):
        svc, rating_repo, puzzle_repo, *_, auth, _, _ = _make_service()
        auth.require_user_id.return_value = 1
        cursor = Mock()
        cursor.rowcount = 0
        rating_repo.conn.execute.return_value = cursor
        assert svc.remove_rating("tok", 1) is False
        puzzle_repo.update_rating_aggregates.assert_not_called()


# ---------------------------------------------------------------------------
# _weighted_avg & _exp_weight pure helpers
# ---------------------------------------------------------------------------

class TestPureHelpers:
    def test_weighted_avg_zero_weight(self):
        assert RatingService._weighted_avg([], []) is None

    def test_weighted_avg_basic(self):
        # All weight 1 → simple mean
        assert RatingService._weighted_avg([2.0, 4.0], [1, 1]) == 3.0

    def test_weighted_avg_experienced_doubles_influence(self):
        # value 5 with weight 2, value 1 with weight 1 → (5*2 + 1*1)/3 = 11/3
        result = RatingService._weighted_avg([5.0, 1.0], [2, 1])
        assert abs(result - 11 / 3) < 1e-9

    def test_exp_weight_experienced(self):
        assert RatingService._exp_weight(_rating(experienced=True)) == 2
        assert RatingService._exp_weight(_rating(experienced=False)) == 1


# ---------------------------------------------------------------------------
# _parse_iso — both tz-aware and tz-naive paths
# ---------------------------------------------------------------------------

class TestParseIsoEdgeCases:
    def test_tz_naive_assumed_utc(self):
        from Backend.ServiceLayer.RatingService import _parse_iso
        result = _parse_iso("2026-05-12T07:00:00")
        assert result.tzinfo is timezone.utc

    def test_tz_aware_preserved(self):
        from Backend.ServiceLayer.RatingService import _parse_iso
        result = _parse_iso("2026-05-12T07:00:00+02:00")
        assert result.utcoffset() == timedelta(hours=2)
