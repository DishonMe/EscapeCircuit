"""Coverage tests for UserService — register error paths, _log_auth_attempt's
silent error handler, _get_online_user_ids, _get_random_avatar, me() medal
aggregation, list_users level→xp conversion, and the under-tested
update_user_bio / update_user_avatar methods."""

import pytest
import threading
from unittest.mock import Mock, patch

from Backend.ServiceLayer.UserService import UserService
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole
from Backend.DomainLayer.Exceptions import ValidationError


def _make_service():
    user_repo = Mock()
    user_repo.conn = Mock()
    auth = Mock()
    xp = Mock()
    audit = Mock()
    svc = UserService(user_repo, auth, xp, audit_log_repo=audit)
    return svc, user_repo, auth, xp, audit


# ---------------------------------------------------------------------------
# _log_auth_attempt — exception path
# ---------------------------------------------------------------------------

class TestLogAuthAttempt:
    def test_exception_swallowed(self):
        svc, repo, *_ = _make_service()
        repo.create_auth_attempt.side_effect = Exception("db down")
        # Should not raise
        svc._log_auth_attempt("login", "u", False, "bad")


# ---------------------------------------------------------------------------
# _get_online_user_ids — three paths
# ---------------------------------------------------------------------------

class TestGetOnlineUserIds:
    def test_no_sessions_attr(self):
        svc, _, auth, *_ = _make_service()
        # plain Mock will satisfy hasattr(auth, "_sessions"); spec_set would not.
        # Replace auth with a bare object that lacks the attribute
        svc.auth = object()
        assert svc._get_online_user_ids() == set()

    def test_with_sessions(self):
        svc, _, auth, *_ = _make_service()
        session_a = Mock()
        session_a.user_id = 1
        session_b = Mock()
        session_b.user_id = 2
        auth._sessions = {"a": session_a, "b": session_b}
        auth._lock = threading.Lock()
        assert svc._get_online_user_ids() == {1, 2}

    def test_exception_returns_empty(self):
        svc, _, auth, *_ = _make_service()
        auth._sessions = {"a": Mock()}
        lock = Mock()
        # Raise on __enter__
        lock.__enter__ = Mock(side_effect=RuntimeError("locked"))
        lock.__exit__ = Mock(return_value=None)
        auth._lock = lock
        assert svc._get_online_user_ids() == set()


# ---------------------------------------------------------------------------
# _get_random_avatar
# ---------------------------------------------------------------------------

class TestRandomAvatar:
    def test_returns_valid_avatar(self):
        result = UserService._get_random_avatar()
        assert result in UserService.VALID_AVATARS


# ---------------------------------------------------------------------------
# register — error branch coverage
# ---------------------------------------------------------------------------

class TestRegisterErrorPaths:
    def setup_method(self):
        self.svc, self.repo, self.auth, self.xp, _ = _make_service()

    def test_missing_password(self):
        with pytest.raises(ValidationError, match="username and password"):
            self.svc.register({"username": "u", "password": "", "email": "e@x.y"})

    def test_missing_email(self):
        with pytest.raises(ValidationError, match="email is required"):
            self.svc.register({"username": "u", "password": "p"})

    def test_missing_avatar_name(self):
        with pytest.raises(ValidationError, match="avatar_name is required"):
            self.svc.register({"username": "u", "password": "p", "email": "e@x.y"})

    def test_invalid_avatar_name(self):
        with pytest.raises(ValidationError, match="invalid avatar_name"):
            self.svc.register({"username": "u", "password": "p", "email": "e@x.y", "avatar_name": "Robot"})

    def test_email_already_exists(self):
        self.repo.get_by_username.return_value = None
        self.repo.get_by_email.return_value = User(id=99, username="other", email="e@x.y")
        with pytest.raises(ValidationError, match="email already exists"):
            self.svc.register({
                "username": "u", "password": "p", "email": "e@x.y", "avatar_name": "Wolf",
            })

    def test_concurrent_integrity_error(self):
        import sqlite3
        self.repo.get_by_username.return_value = None
        self.repo.get_by_email.return_value = None
        self.repo.create.side_effect = sqlite3.IntegrityError("dup")
        with pytest.raises(ValidationError, match="already exists"):
            self.svc.register({
                "username": "u", "password": "p", "email": "e@x.y", "avatar_name": "Wolf",
            })


# ---------------------------------------------------------------------------
# me() — medal aggregation branches
# ---------------------------------------------------------------------------

class TestMeMedalAggregation:
    def test_me_aggregates_medals_by_level(self):
        svc, repo, auth, xp, _ = _make_service()
        auth.require_user_id.return_value = 1
        user = User(id=1, username="u", xp=300, role=UserRole.SOLVER)
        repo.get_by_id.return_value = user
        xp.calculate_level.return_value = 4
        xp.is_experienced.return_value = False

        # Mock connection chains
        medal_rows = [
            {"best_medal": 1, "count": 2},
            {"best_medal": 2, "count": 1},
            {"best_medal": 3, "count": 3},
            {"best_medal": 0, "count": 5},  # exercises the no-match branch
        ]
        arsenal_row = {"count": 7}
        saved_rows = [{"id": 10, "name": "S", "status": "published", "created_at": "t"}]
        created_rows = [{"id": 20, "name": "C", "status": "draft", "created_at": "t"}]
        solved_rows = [{"puzzle_id": 30, "id": 30, "name": "Solved"}]

        # The me() function calls .execute(...).fetchall() / .fetchone() in sequence.
        # NOTE: both the medal-aggregation query and the solved-puzzles query
        # reference puzzle_progress, so the solved-puzzles query (which uses
        # "DISTINCT pp.puzzle_id") must be matched first.
        def execute_side_effect(sql, params=None):
            cursor = Mock()
            if "DISTINCT pp.puzzle_id" in sql:
                cursor.fetchall.return_value = solved_rows
            elif "puzzle_progress" in sql:
                cursor.fetchall.return_value = medal_rows
            elif "circuits" in sql:
                cursor.fetchone.return_value = arsenal_row
            elif "saved_puzzles" in sql:
                cursor.fetchall.return_value = saved_rows
            elif "creator_user_id" in sql:
                cursor.fetchall.return_value = created_rows
            elif "AS total" in sql:
                cursor.fetchone.return_value = {"total": 12}
            return cursor

        repo.conn.execute.side_effect = execute_side_effect
        result = svc.me("tok")
        assert result["medals"]["bronze"] == 2
        assert result["medals"]["silver"] == 1
        assert result["medals"]["gold"] == 3
        assert result["medals"]["total"] == 6
        assert result["arsenal_count"] == 7
        assert len(result["saved_puzzles"]) == 1
        assert len(result["created_puzzles"]) == 1
        assert len(result["solved_puzzles"]) == 1


# ---------------------------------------------------------------------------
# list_users — level→xp conversions with and without calculate_xp_for_level
# ---------------------------------------------------------------------------

class TestListUsersLevelConversion:
    def test_list_users_with_calculate_xp_helper(self):
        svc, repo, auth, xp, _ = _make_service()
        auth.require_user_id.return_value = 1
        xp.calculate_xp_for_level.return_value = 500
        repo.list_all.return_value = []
        repo.count_all.return_value = 0
        svc.list_users("tok", min_level=2, max_level=5)
        # Verify min_xp / max_xp computed using helper
        kwargs = repo.list_all.call_args.kwargs
        assert kwargs["min_xp"] == 500
        assert kwargs["max_xp"] == 500 - 1

    def test_list_users_without_calculate_xp_helper(self):
        svc, repo, auth, xp, _ = _make_service()
        auth.require_user_id.return_value = 1
        # Remove the calculate_xp_for_level attribute → fallback formula
        del xp.calculate_xp_for_level
        repo.list_all.return_value = []
        repo.count_all.return_value = 0
        svc.list_users("tok", min_level=2)
        kwargs = repo.list_all.call_args.kwargs
        # Fallback uses (min_level - 1) * LEVEL_XP_DIVISOR
        from Backend import settings
        assert kwargs["min_xp"] == 1 * settings.LEVEL_XP_DIVISOR


# ---------------------------------------------------------------------------
# update_user_bio
# ---------------------------------------------------------------------------

class TestUpdateUserBio:
    def setup_method(self):
        self.svc, self.repo, *_ = _make_service()

    def test_update_bio_success(self):
        self.repo.get_by_id.return_value = User(id=1, username="u")
        result = self.svc.update_user_bio(1, "Hello world")
        assert result["bio"] == "Hello world"
        self.repo.conn.execute.assert_called_once()

    def test_update_bio_user_not_found(self):
        self.repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="user not found"):
            self.svc.update_user_bio(1, "Hi")

    def test_update_bio_too_long(self):
        self.repo.get_by_id.return_value = User(id=1, username="u")
        with pytest.raises(ValidationError, match="500"):
            self.svc.update_user_bio(1, "x" * 501)


# ---------------------------------------------------------------------------
# update_user_avatar
# ---------------------------------------------------------------------------

class TestUpdateUserAvatar:
    def setup_method(self):
        self.svc, self.repo, *_ = _make_service()

    def test_update_avatar_success(self):
        u = User(id=1, username="u")
        # First call: validation; second call: re-read after update
        self.repo.get_by_id.side_effect = [u, u]
        result = self.svc.update_user_avatar(1, "Wolf", "#abcdef")
        assert result["username"] == "u"

    def test_update_avatar_user_not_found(self):
        self.repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="user not found"):
            self.svc.update_user_avatar(1, "Wolf", "#abcdef")

    def test_update_avatar_invalid_name(self):
        self.repo.get_by_id.return_value = User(id=1, username="u")
        with pytest.raises(ValidationError, match="invalid avatar_name"):
            self.svc.update_user_avatar(1, "Robot", "#abcdef")

    def test_update_avatar_invalid_color_format(self):
        self.repo.get_by_id.return_value = User(id=1, username="u")
        with pytest.raises(ValidationError, match="invalid avatar_color"):
            self.svc.update_user_avatar(1, "Wolf", "red")

    def test_update_avatar_empty_color(self):
        self.repo.get_by_id.return_value = User(id=1, username="u")
        with pytest.raises(ValidationError, match="invalid avatar_color"):
            self.svc.update_user_avatar(1, "Wolf", "")

    def test_update_avatar_refetch_fails(self):
        u = User(id=1, username="u")
        # First get_by_id returns user, second (after update) returns None
        self.repo.get_by_id.side_effect = [u, None]
        with pytest.raises(ValidationError, match="failed to retrieve"):
            self.svc.update_user_avatar(1, "Wolf", "#abcdef")
