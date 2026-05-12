"""Coverage tests for AdminService — focus on uncovered behavior:
get_user_profile aggregation, list_solving_attempts, list_auth_attempts,
_get_online_user_ids paths, _delete_riddle_files paths, and the
race-condition branch in assign_creator."""

import pathlib
import threading
from unittest.mock import Mock, patch

import pytest

from Backend.ServiceLayer.AdminService import AdminService
from Backend.DomainLayer.Enums import UserRole
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.User import User


def _make_service():
    user_repo = Mock()
    user_repo.conn = Mock()
    puzzle_repo = Mock()
    solve_repo = Mock()
    rating_repo = Mock()
    audit_log = Mock()
    notification_repo = Mock()
    auth = Mock()
    circuit_repo = Mock()
    svc = AdminService(
        user_repo, puzzle_repo, solve_repo, rating_repo,
        audit_log, notification_repo, auth,
        circuit_repo=circuit_repo,
    )
    return svc, user_repo, puzzle_repo, solve_repo, rating_repo, audit_log, notification_repo, auth, circuit_repo


def _admin(uid=99):
    return User(id=uid, username=f"admin{uid}", role=UserRole.ADMIN)


# ---------------------------------------------------------------------------
# _get_online_user_ids — all three paths
# ---------------------------------------------------------------------------

class TestGetOnlineUserIds:
    def test_no_sessions_attr(self):
        svc, *_ = _make_service()
        svc.auth = object()  # plain object lacks _sessions / _lock
        assert svc._get_online_user_ids() == set()

    def test_with_sessions(self):
        svc, _, _, _, _, _, _, auth, _ = _make_service()
        s1 = Mock(); s1.user_id = 1
        s2 = Mock(); s2.user_id = 2
        auth._sessions = {"a": s1, "b": s2}
        auth._lock = threading.Lock()
        assert svc._get_online_user_ids() == {1, 2}

    def test_exception_swallowed(self):
        svc, _, _, _, _, _, _, auth, _ = _make_service()
        auth._sessions = {"a": Mock()}
        lock = Mock()
        lock.__enter__ = Mock(side_effect=RuntimeError("locked"))
        lock.__exit__ = Mock(return_value=None)
        auth._lock = lock
        assert svc._get_online_user_ids() == set()


# ---------------------------------------------------------------------------
# _delete_riddle_files — covers missing-dir, existing-dir, legacy-pattern paths
# ---------------------------------------------------------------------------

class TestDeleteRiddleFiles:
    def test_riddles_dir_missing_returns(self, tmp_path):
        svc, *_ = _make_service()
        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "AdminService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            svc._delete_riddle_files(1, "foo")  # no riddles dir → silent return

    def test_deletes_exact_match(self, tmp_path):
        svc, *_ = _make_service()
        target = tmp_path / "riddles" / "riddle_5_my_puzzle"
        target.mkdir(parents=True)
        (target / "x.txt").write_text("x")
        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "AdminService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            svc._delete_riddle_files(5, "My Puzzle")
        assert not target.exists()

    def test_legacy_pattern_fallback(self, tmp_path):
        svc, *_ = _make_service()
        legacy = tmp_path / "riddles" / "riddle_99_my_puzzle"
        legacy.mkdir(parents=True)
        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "AdminService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            svc._delete_riddle_files(5, "My Puzzle")
        assert not legacy.exists()


# ---------------------------------------------------------------------------
# assign_creator — race-condition branch (update_role_if returns False)
# ---------------------------------------------------------------------------

class TestAssignCreatorRace:
    def test_role_change_race_raises(self):
        svc, user_repo, *_, auth, _ = _make_service()
        auth.require_user_id.return_value = 99
        user_repo.get_by_id.side_effect = lambda uid: (
            _admin() if uid == 99 else User(id=uid, username="target", role=UserRole.SOLVER)
        )
        user_repo.update_role_if.return_value = False
        with pytest.raises(ValidationError, match="changed by another admin"):
            svc.assign_creator("tok", 5)


# ---------------------------------------------------------------------------
# get_user_profile — medal aggregation, arsenal listing, online flag
# ---------------------------------------------------------------------------

class TestGetUserProfile:
    def setup_method(self):
        (self.svc, self.user_repo, *_, self.auth, self.circuit_repo) = _make_service()
        self.auth.require_user_id.return_value = 99
        self.user_repo.get_by_id.side_effect = lambda uid: (
            _admin() if uid == 99 else User(id=uid, username=f"t{uid}", xp=0)
        )

    def _stub_execute_chain(self, medal_rows, saved_rows, created_rows):
        def execute(sql, params):
            cursor = Mock()
            if "puzzle_progress" in sql:
                cursor.fetchall.return_value = medal_rows
            elif "saved_puzzles" in sql:
                cursor.fetchall.return_value = saved_rows
            elif "creator_user_id" in sql:
                cursor.fetchall.return_value = created_rows
            return cursor
        self.user_repo.conn.execute.side_effect = execute

    def test_target_user_not_found(self):
        self.user_repo.get_by_id.side_effect = lambda uid: _admin() if uid == 99 else None
        with pytest.raises(ValidationError, match="target user not found"):
            self.svc.get_user_profile("tok", 7)

    def test_aggregates_medal_counts_and_arsenal(self):
        self._stub_execute_chain(
            medal_rows=[
                {"best_medal": 1, "count": 2},
                {"best_medal": 2, "count": 1},
                {"best_medal": 3, "count": 3},
                {"best_medal": 0, "count": 5},  # exercise no-match branch
            ],
            saved_rows=[{"id": 10, "name": "S", "status": "published", "created_at": "t"}],
            created_rows=[{"id": 20, "name": "C", "status": "draft", "created_at": "t"}],
        )
        piece = Mock(id=1, name="P", cost=5, is_arsenal=True, num_inputs=2,
                     num_outputs=1, basic_gates="[]", truth_table="{}",
                     structure_json="{}", description="d")
        self.circuit_repo.list_arsenal_by_user.return_value = [piece]

        d = self.svc.get_user_profile("tok", 7)
        assert d["medals"]["bronze"] == 2
        assert d["medals"]["silver"] == 1
        assert d["medals"]["gold"] == 3
        assert d["medals"]["total"] == 6
        assert d["saved_puzzles"][0]["id"] == "10"
        assert d["created_puzzles"][0]["id"] == "20"
        assert len(d["arsenal"]) == 1
        # is_online derived from _get_online_user_ids (no sessions → False)
        assert d["is_online"] is False

    def test_arsenal_empty_when_circuit_repo_missing(self):
        self.svc.circuit_repo = None
        self._stub_execute_chain([], [], [])
        d = self.svc.get_user_profile("tok", 7)
        assert d["arsenal"] == []


# ---------------------------------------------------------------------------
# list_solving_attempts / list_auth_attempts
# ---------------------------------------------------------------------------

class TestListAttempts:
    def test_list_solving_attempts(self):
        svc, user_repo, _, solve_repo, *_, auth, _ = _make_service()
        auth.require_user_id.return_value = 99
        user_repo.get_by_id.return_value = _admin()
        solve_repo.list_attempts_for_admin.return_value = [{"id": 1}]
        solve_repo.count_attempts_for_admin.return_value = 1
        result = svc.list_solving_attempts("tok", limit=10, offset=0, user_id=5, puzzle_id=2, passed=True)
        assert result["total"] == 1
        solve_repo.list_attempts_for_admin.assert_called_once_with(
            limit=10, offset=0, user_id=5, puzzle_id=2, passed=True
        )

    def test_list_solving_attempts_non_admin(self):
        svc, user_repo, *_, auth, _ = _make_service()
        auth.require_user_id.return_value = 1
        user_repo.get_by_id.return_value = User(id=1, username="u", role=UserRole.SOLVER)
        with pytest.raises(ValidationError, match="admin required"):
            svc.list_solving_attempts("tok")

    def test_list_auth_attempts(self):
        svc, user_repo, *_, auth, _ = _make_service()
        auth.require_user_id.return_value = 99
        user_repo.get_by_id.return_value = _admin()
        user_repo.list_auth_attempts.return_value = [{"id": 1}]
        result = svc.list_auth_attempts("tok", limit=10, offset=0, action="login", success=False)
        assert result == [{"id": 1}]


# ---------------------------------------------------------------------------
# list_audit_log — requires admin (covers branch for non-admin)
# ---------------------------------------------------------------------------

class TestListAuditLog:
    def test_admin_lists(self):
        svc, user_repo, *_, audit, _, auth, _ = _make_service()
        auth.require_user_id.return_value = 99
        user_repo.get_by_id.return_value = _admin()
        audit.list_all.return_value = []
        svc.list_audit_log("tok", action_type="UNPUBLISH_PUZZLE")
        audit.list_all.assert_called_once_with(limit=100, offset=0, action_type="UNPUBLISH_PUZZLE")

    def test_non_admin_raises(self):
        svc, user_repo, *_, auth, _ = _make_service()
        auth.require_user_id.return_value = 1
        user_repo.get_by_id.return_value = User(id=1, username="u", role=UserRole.SOLVER)
        with pytest.raises(ValidationError, match="admin required"):
            svc.list_audit_log("tok")


# ---------------------------------------------------------------------------
# update_creator_puzzle_limits — validation and revert-to-default
# ---------------------------------------------------------------------------

class TestUpdateCreatorLimits:
    def setup_method(self):
        (self.svc, self.user_repo, *_, self.auth, _) = _make_service()
        self.auth.require_user_id.return_value = 99

    def test_negative_published_rejected(self):
        self.user_repo.get_by_id.side_effect = lambda uid: (
            _admin() if uid == 99 else User(id=uid, username="c", role=UserRole.CREATOR)
        )
        with pytest.raises(ValidationError, match="max_published cannot be negative"):
            self.svc.update_creator_puzzle_limits("tok", 5, max_published=-1, max_unpublished=None)

    def test_negative_unpublished_rejected(self):
        self.user_repo.get_by_id.side_effect = lambda uid: (
            _admin() if uid == 99 else User(id=uid, username="c", role=UserRole.CREATOR)
        )
        with pytest.raises(ValidationError, match="max_unpublished cannot be negative"):
            self.svc.update_creator_puzzle_limits("tok", 5, max_published=None, max_unpublished=-2)

    def test_target_not_creator_rejected(self):
        self.user_repo.get_by_id.side_effect = lambda uid: (
            _admin() if uid == 99 else User(id=uid, username="s", role=UserRole.SOLVER)
        )
        with pytest.raises(ValidationError, match="not a creator"):
            self.svc.update_creator_puzzle_limits("tok", 5, max_published=5, max_unpublished=5)
