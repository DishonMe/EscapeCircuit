"""Tests for AdminService"""
import pytest
from unittest.mock import Mock, MagicMock
from Backend.ServiceLayer.AdminService import AdminService
from Backend.DomainLayer.Enums import UserRole, PuzzleStatus, AuditActionType
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Puzzle import Puzzle


class TestAdminServiceInit:
    def setup_method(self):
        self.mock_user_repo = Mock()
        self.mock_puzzle_repo = Mock()
        self.mock_solve_repo = Mock()
        self.mock_rating_repo = Mock()
        self.mock_audit_log = Mock()
        self.mock_notification_repo = Mock()
        self.mock_auth = Mock()
        
        self.service = AdminService(
            self.mock_user_repo,
            self.mock_puzzle_repo,
            self.mock_solve_repo,
            self.mock_rating_repo,
            self.mock_audit_log,
            self.mock_notification_repo,
            self.mock_auth,
        )

    def test_initialization(self):
        assert self.service.user_repo == self.mock_user_repo
        assert self.service.puzzle_repo == self.mock_puzzle_repo
        assert self.service.solve_repo == self.mock_solve_repo
        assert self.service.rating_repo == self.mock_rating_repo
        assert self.service.audit_log == self.mock_audit_log
        assert self.service.notification_repo == self.mock_notification_repo
        assert self.service.auth == self.mock_auth


class TestAdminServiceRequireAdmin:
    def setup_method(self):
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_puzzle_repo = Mock()
        self.mock_solve_repo = Mock()
        self.mock_rating_repo = Mock()
        self.mock_audit_log = Mock()
        self.mock_notification_repo = Mock()
        
        self.service = AdminService(
            self.mock_user_repo,
            self.mock_puzzle_repo,
            self.mock_solve_repo,
            self.mock_rating_repo,
            self.mock_audit_log,
            self.mock_notification_repo,
            self.mock_auth,
        )

    def test_require_admin_success(self):
        admin_id = 1
        token = "valid_token"
        admin_user = Mock(spec=User)
        admin_user.role = UserRole.ADMIN
        
        self.mock_auth.require_user_id.return_value = admin_id
        self.mock_user_repo.get_by_id.return_value = admin_user
        
        result = self.service._require_admin(token)
        assert result == admin_id
        self.mock_auth.require_user_id.assert_called_once_with(token)
        self.mock_user_repo.get_by_id.assert_called_once_with(admin_id)

    def test_require_admin_not_admin(self):
        admin_id = 1
        token = "valid_token"
        user = Mock(spec=User)
        user.role = UserRole.SOLVER
        
        self.mock_auth.require_user_id.return_value = admin_id
        self.mock_user_repo.get_by_id.return_value = user
        
        with pytest.raises(ValidationError):
            self.service._require_admin(token)

    def test_require_admin_user_not_found(self):
        admin_id = 1
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = admin_id
        self.mock_user_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError):
            self.service._require_admin(token)


class TestAdminServiceRequireAdminOrCreator:
    def setup_method(self):
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_puzzle_repo = Mock()
        self.mock_solve_repo = Mock()
        self.mock_rating_repo = Mock()
        self.mock_audit_log = Mock()
        self.mock_notification_repo = Mock()
        
        self.service = AdminService(
            self.mock_user_repo,
            self.mock_puzzle_repo,
            self.mock_solve_repo,
            self.mock_rating_repo,
            self.mock_audit_log,
            self.mock_notification_repo,
            self.mock_auth,
        )

    def test_require_admin_or_creator_admin(self):
        user_id = 1
        token = "valid_token"
        user = Mock(spec=User)
        user.role = UserRole.ADMIN
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_user_repo.get_by_id.return_value = user
        
        result = self.service._require_admin_or_creator(token)
        assert result == user_id

    def test_require_admin_or_creator_creator(self):
        user_id = 1
        token = "valid_token"
        user = Mock(spec=User)
        user.role = UserRole.CREATOR
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_user_repo.get_by_id.return_value = user
        
        result = self.service._require_admin_or_creator(token)
        assert result == user_id

    def test_require_admin_or_creator_pending_creator(self):
        user_id = 1
        token = "valid_token"
        user = Mock(spec=User)
        user.role = UserRole.PENDING_CREATOR
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_user_repo.get_by_id.return_value = user
        
        result = self.service._require_admin_or_creator(token)
        assert result == user_id

    def test_require_admin_or_creator_solver_fails(self):
        user_id = 1
        token = "valid_token"
        user = Mock(spec=User)
        user.role = UserRole.SOLVER
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_user_repo.get_by_id.return_value = user
        
        with pytest.raises(ValidationError):
            self.service._require_admin_or_creator(token)


class TestAdminServiceAssignCreator:
    def setup_method(self):
        self.mock_user_repo = Mock()
        self.mock_user_repo.conn = Mock()
        self.mock_puzzle_repo = Mock()
        self.mock_solve_repo = Mock()
        self.mock_rating_repo = Mock()
        self.mock_audit_log = Mock()
        self.mock_notification_repo = Mock()
        self.mock_auth = Mock()
        
        self.service = AdminService(
            self.mock_user_repo,
            self.mock_puzzle_repo,
            self.mock_solve_repo,
            self.mock_rating_repo,
            self.mock_audit_log,
            self.mock_notification_repo,
            self.mock_auth,
        )

    def test_assign_creator_success(self):
        admin_id = 1
        target_user_id = 2
        token = "admin_token"
        
        admin = Mock(spec=User)
        admin.role = UserRole.ADMIN
        admin.username = "admin_user"
        
        target = Mock(spec=User)
        target.role = UserRole.SOLVER
        
        self.mock_auth.require_user_id.return_value = admin_id
        self.mock_user_repo.get_by_id.side_effect = [admin, target, admin]
        self.mock_user_repo.update_role_if.return_value = True
        
        result = self.service.assign_creator(token, target_user_id)
        
        assert result["ok"] is True
        assert result["new_role"] == UserRole.PENDING_CREATOR.value
        self.mock_notification_repo.create.assert_called_once()
        self.mock_audit_log.create.assert_called_once()

    def test_assign_creator_target_not_found(self):
        admin_id = 1
        target_user_id = 999
        token = "admin_token"
        
        admin = Mock(spec=User)
        admin.role = UserRole.ADMIN
        
        self.mock_auth.require_user_id.return_value = admin_id
        self.mock_user_repo.get_by_id.side_effect = [admin, None]
        
        with pytest.raises(ValidationError):
            self.service.assign_creator(token, target_user_id)

    def test_assign_creator_target_is_admin(self):
        admin_id = 1
        target_user_id = 2
        token = "admin_token"
        
        admin = Mock(spec=User)
        admin.role = UserRole.ADMIN
        
        target = Mock(spec=User)
        target.role = UserRole.ADMIN
        
        self.mock_auth.require_user_id.return_value = admin_id
        self.mock_user_repo.get_by_id.side_effect = [admin, target]
        
        with pytest.raises(ValidationError):
            self.service.assign_creator(token, target_user_id)

    def test_assign_creator_already_creator(self):
        admin_id = 1
        target_user_id = 2
        token = "admin_token"
        
        admin = Mock(spec=User)
        admin.role = UserRole.ADMIN
        
        target = Mock(spec=User)
        target.role = UserRole.CREATOR
        
        self.mock_auth.require_user_id.return_value = admin_id
        self.mock_user_repo.get_by_id.side_effect = [admin, target]
        
        with pytest.raises(ValidationError):
            self.service.assign_creator(token, target_user_id)

    def test_assign_creator_already_pending(self):
        admin_id = 1
        target_user_id = 2
        token = "admin_token"
        
        admin = Mock(spec=User)
        admin.role = UserRole.ADMIN
        
        target = Mock(spec=User)
        target.role = UserRole.PENDING_CREATOR
        
        self.mock_auth.require_user_id.return_value = admin_id
        self.mock_user_repo.get_by_id.side_effect = [admin, target]
        
        with pytest.raises(ValidationError):
            self.service.assign_creator(token, target_user_id)


class TestAdminServiceModeration:
    def setup_method(self):
        self.mock_user_repo = Mock()
        self.mock_user_repo.conn = Mock()
        self.mock_puzzle_repo = Mock()
        self.mock_solve_repo = Mock()
        self.mock_rating_repo = Mock()
        self.mock_audit_log = Mock()
        self.mock_notification_repo = Mock()
        self.mock_auth = Mock()
        
        self.service = AdminService(
            self.mock_user_repo,
            self.mock_puzzle_repo,
            self.mock_solve_repo,
            self.mock_rating_repo,
            self.mock_audit_log,
            self.mock_notification_repo,
            self.mock_auth,
        )

    def test_delete_puzzle_not_found(self):
        admin_id = 1
        puzzle_id = 999
        token = "admin_token"
        
        admin = Mock(spec=User)
        admin.role = UserRole.ADMIN
        
        self.mock_auth.require_user_id.return_value = admin_id
        self.mock_user_repo.get_by_id.return_value = admin
        self.mock_puzzle_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError):
            self.service.delete_puzzle(token, puzzle_id)

    def test_list_audit_log_calls_repo(self):
        admin_id = 1
        token = "admin_token"
        
        admin = Mock(spec=User)
        admin.role = UserRole.ADMIN
        
        mock_audit_entries = [Mock(), Mock()]
        
        self.mock_auth.require_user_id.return_value = admin_id
        self.mock_user_repo.get_by_id.return_value = admin
        self.mock_audit_log.list_all.return_value = mock_audit_entries
        
        result = self.service.list_audit_log(token)
        
        assert result is not None


class TestAdminServiceDeletePuzzle:
    """Tests for AdminService.delete_puzzle with the published-puzzle restriction."""

    def _make_service(self):
        mock_user_repo = Mock()
        mock_user_repo.conn = Mock()
        mock_puzzle_repo = Mock()
        mock_puzzle_repo.conn = Mock()
        mock_solve_repo = Mock()
        mock_rating_repo = Mock()
        mock_audit_log = Mock()
        mock_notification_repo = Mock()
        mock_auth = Mock()

        service = AdminService(
            mock_user_repo,
            mock_puzzle_repo,
            mock_solve_repo,
            mock_rating_repo,
            mock_audit_log,
            mock_notification_repo,
            mock_auth,
        )
        return service, mock_user_repo, mock_puzzle_repo, mock_solve_repo, mock_rating_repo, mock_audit_log, mock_auth

    def test_delete_published_puzzle_raises(self):
        service, mock_user_repo, mock_puzzle_repo, *_ = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        puzzle = Mock(spec=Puzzle); puzzle.status = PuzzleStatus.PUBLISHED
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_puzzle_repo.get_by_id.return_value = puzzle

        with pytest.raises(ValidationError, match="Cannot delete a published puzzle"):
            service.delete_puzzle("token", 1)

    def test_delete_draft_puzzle_succeeds(self):
        service, mock_user_repo, mock_puzzle_repo, mock_solve_repo, mock_rating_repo, mock_audit_log, _ = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        puzzle = Mock(spec=Puzzle)
        puzzle.status = PuzzleStatus.DRAFT
        puzzle.name = "TestPuzzle"
        puzzle.creator_user_id = 2
        puzzle.id = 10

        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_puzzle_repo.get_by_id.return_value = puzzle
        mock_puzzle_repo.conn = Mock()
        mock_puzzle_repo.conn.__enter__ = Mock(return_value=None)
        mock_puzzle_repo.conn.__exit__ = Mock(return_value=False)

        # patch transaction context manager
        with pytest.MonkeyPatch().context() as mp:
            import Backend.PersistantLayer._db as db_mod
            mp.setattr(db_mod, "transaction", lambda conn: __import__("contextlib").nullcontext())
            result = service.delete_puzzle("token", 10)
        assert result["ok"] is True


class TestAdminServiceAdminUnpublish:
    """Tests for AdminService.admin_unpublish_puzzle."""

    def _make_service(self):
        mock_user_repo = Mock()
        mock_user_repo.conn = Mock()
        mock_puzzle_repo = Mock()
        mock_puzzle_repo.conn = Mock()
        mock_solve_repo = Mock()
        mock_rating_repo = Mock()
        mock_audit_log = Mock()
        mock_notification_repo = Mock()
        mock_auth = Mock()
        service = AdminService(
            mock_user_repo, mock_puzzle_repo, mock_solve_repo,
            mock_rating_repo, mock_audit_log, mock_notification_repo, mock_auth,
        )
        return service, mock_user_repo, mock_puzzle_repo, mock_audit_log

    def test_unpublish_non_published_raises(self):
        service, mock_user_repo, mock_puzzle_repo, _ = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        puzzle = Mock(spec=Puzzle); puzzle.status = PuzzleStatus.DRAFT
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_puzzle_repo.get_by_id.return_value = puzzle

        with pytest.raises(ValidationError, match="puzzle is not published"):
            service.admin_unpublish_puzzle("token", 1)

    def test_unpublish_not_found_raises(self):
        service, mock_user_repo, mock_puzzle_repo, _ = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_puzzle_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="puzzle not found"):
            service.admin_unpublish_puzzle("token", 99)

    def test_unpublish_published_succeeds(self):
        service, mock_user_repo, mock_puzzle_repo, mock_audit_log = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        puzzle = Mock(spec=Puzzle)
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.name = "MyPuzzle"
        puzzle.creator_user_id = 5

        service.auth.require_user_id.return_value = 1
        # get_by_id called twice: once for admin auth, once for creator notification
        mock_user_repo.get_by_id.side_effect = [admin, Mock(spec=User)]
        mock_puzzle_repo.get_by_id.return_value = puzzle
        mock_puzzle_repo.conn.execute = Mock()
        mock_puzzle_repo.conn.commit = Mock()

        result = service.admin_unpublish_puzzle("token", 42)
        assert result["ok"] is True
        mock_audit_log.create.assert_called_once()


class TestAdminServiceUpdatePuzzleLimits:
    """Tests for AdminService.update_creator_puzzle_limits."""

    def _make_service(self):
        mock_user_repo = Mock()
        mock_user_repo.conn = Mock()
        mock_puzzle_repo = Mock()
        mock_solve_repo = Mock()
        mock_rating_repo = Mock()
        mock_audit_log = Mock()
        mock_notification_repo = Mock()
        mock_auth = Mock()
        service = AdminService(
            mock_user_repo, mock_puzzle_repo, mock_solve_repo,
            mock_rating_repo, mock_audit_log, mock_notification_repo, mock_auth,
        )
        return service, mock_user_repo

    def test_update_limits_target_not_found(self):
        service, mock_user_repo = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, None]

        with pytest.raises(ValidationError, match="target user not found"):
            service.update_creator_puzzle_limits("token", 99, 10, 5)

    def test_update_limits_non_creator_raises(self):
        service, mock_user_repo = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User); target.role = UserRole.SOLVER
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]

        with pytest.raises(ValidationError, match="not a creator"):
            service.update_creator_puzzle_limits("token", 2, 10, 5)

    def test_update_limits_negative_raises(self):
        service, mock_user_repo = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User); target.role = UserRole.CREATOR
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]

        with pytest.raises(ValidationError, match="cannot be negative"):
            service.update_creator_puzzle_limits("token", 2, -1, 5)

    def test_update_limits_success(self):
        service, mock_user_repo = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User); target.role = UserRole.CREATOR

        updated_user = Mock(spec=User)
        updated_user.max_published_puzzles = 10
        updated_user.max_unpublished_puzzles = 5
        updated_user.get_puzzle_capacity = Mock(return_value=(10, 5))

        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target, updated_user]

        result = service.update_creator_puzzle_limits("token", 2, 10, 5)
        assert result["ok"] is True
        assert result["max_published_override"] == 10
        assert result["max_unpublished_override"] == 5
        mock_user_repo.update_puzzle_limits.assert_called_once_with(2, 10, 5)

    def test_update_limits_with_none_reverts_to_default(self):
        service, mock_user_repo = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User); target.role = UserRole.CREATOR

        updated_user = Mock(spec=User)
        updated_user.get_puzzle_capacity = Mock(return_value=(5, 5))

        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target, updated_user]

        result = service.update_creator_puzzle_limits("token", 2, None, None)
        assert result["ok"] is True
        mock_user_repo.update_puzzle_limits.assert_called_once_with(2, None, None)


# ============================================================================
#  NEW TESTS: RemoveCreator, ConfirmRemoveCreator, ListPuzzles, ListAuditLog
# ============================================================================


class TestAdminServiceRemoveCreator:
    """Tests for AdminService.remove_creator (REQ 7.3)."""

    def _make_service(self):
        mock_user_repo = Mock()
        mock_user_repo.conn = Mock()
        mock_puzzle_repo = Mock()
        mock_solve_repo = Mock()
        mock_rating_repo = Mock()
        mock_audit_log = Mock()
        mock_notification_repo = Mock()
        mock_auth = Mock()
        service = AdminService(
            mock_user_repo, mock_puzzle_repo, mock_solve_repo,
            mock_rating_repo, mock_audit_log, mock_notification_repo, mock_auth,
        )
        return service, mock_user_repo, mock_puzzle_repo, mock_solve_repo, mock_rating_repo, mock_audit_log, mock_notification_repo, mock_auth

    def test_remove_creator_target_not_found(self):
        """Error when target user not found."""
        service, mock_user_repo, *_ = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, None]

        with pytest.raises(ValidationError, match="target user not found"):
            service.remove_creator("token", 999)

    def test_remove_creator_not_creator(self):
        """Error when target user is not a creator or pending creator."""
        service, mock_user_repo, *_ = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User); target.role = UserRole.SOLVER
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]

        with pytest.raises(ValidationError, match="not a creator or pending creator"):
            service.remove_creator("token", 2)

    def test_remove_pending_creator_success(self):
        """Successfully remove a PENDING_CREATOR, transition to SOLVER."""
        service, mock_user_repo, *_, mock_notification_repo, mock_auth = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User)
        target.role = UserRole.PENDING_CREATOR
        target.username = "pending_creator"
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]
        mock_user_repo.update_role_if.return_value = True
        
        result = service.remove_creator("token", 2)
        
        assert result["ok"] is True
        assert result["new_role"] == UserRole.SOLVER.value
        assert result["was_pending"] is True
        
        # Verify role update
        mock_user_repo.update_role_if.assert_called_once_with(2, UserRole.SOLVER, UserRole.PENDING_CREATOR)
        
        # Verify notification created
        mock_notification_repo.create.assert_called_once()
        call_kwargs = mock_notification_repo.create.call_args[1]
        assert call_kwargs["user_id"] == 2
        assert call_kwargs["notif_type"] == "role_change"
        assert "pending Creator role has been cancelled" in call_kwargs["message"]

    def test_remove_creator_with_no_puzzles(self):
        """Remove a CREATOR with no published/draft puzzles."""
        service, mock_user_repo, mock_puzzle_repo, *_, mock_notification_repo, mock_audit_log, mock_auth = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User)
        target.role = UserRole.CREATOR
        target.username = "active_creator"
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]
        mock_puzzle_repo.get_by_creator_and_status.side_effect = [[], []]  # No published, no draft
        
        result = service.remove_creator("token", 2)
        
        assert result["ok"] is True
        assert result["user_id"] == 2
        assert result["username"] == "active_creator"
        assert result["published_count"] == 0
        assert result["draft_count"] == 0
        assert result["admin_action_required"] is False

    def test_remove_creator_with_published_puzzles(self):
        """Remove a CREATOR with published puzzles—return counts, no immediate action."""
        service, mock_user_repo, mock_puzzle_repo, *_, mock_audit_log, mock_notification_repo, mock_auth = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User)
        target.role = UserRole.CREATOR
        target.username = "prolific_creator"
        
        # Mock published puzzles
        pub_puzzle1 = Mock(spec=Puzzle); pub_puzzle1.id = 10; pub_puzzle1.name = "Puzzle A"
        pub_puzzle2 = Mock(spec=Puzzle); pub_puzzle2.id = 11; pub_puzzle2.name = "Puzzle B"
        draft_puzzle1 = Mock(spec=Puzzle); draft_puzzle1.id = 20; draft_puzzle1.name = "Draft A"
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]
        mock_puzzle_repo.get_by_creator_and_status.side_effect = [
            [pub_puzzle1, pub_puzzle2],  # published
            [draft_puzzle1],              # draft
        ]
        
        result = service.remove_creator("token", 2)
        
        assert result["ok"] is True
        assert result["published_count"] == 2
        assert result["draft_count"] == 1
        assert result["admin_action_required"] is True
        assert len(result["published_puzzles"]) == 2
        assert result["published_puzzles"][0]["id"] == 10
        assert result["published_puzzles"][0]["name"] == "Puzzle A"

    def test_remove_creator_role_change_race_condition(self):
        """Error when user role changes during operation (race condition)."""
        service, mock_user_repo, mock_puzzle_repo, *_, mock_audit_log, mock_notification_repo, mock_auth = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User); target.role = UserRole.PENDING_CREATOR
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]
        mock_user_repo.update_role_if.return_value = False  # Race condition: role changed
        
        with pytest.raises(ValidationError, match="user role was changed by another admin"):
            service.remove_creator("token", 2)


class TestAdminServiceConfirmRemoveCreator:
    """Tests for AdminService.confirm_remove_creator (REQ 7.3.1 + 7.5)."""

    def _make_service(self):
        mock_user_repo = Mock()
        mock_user_repo.conn = Mock()
        mock_puzzle_repo = Mock()
        mock_puzzle_repo.conn = Mock()
        mock_solve_repo = Mock()
        mock_rating_repo = Mock()
        mock_audit_log = Mock()
        mock_notification_repo = Mock()
        mock_auth = Mock()
        
        service = AdminService(
            mock_user_repo, mock_puzzle_repo, mock_solve_repo,
            mock_rating_repo, mock_audit_log, mock_notification_repo, mock_auth,
        )
        return service, mock_user_repo, mock_puzzle_repo, mock_solve_repo, mock_rating_repo, mock_audit_log, mock_notification_repo, mock_auth

    def test_confirm_remove_creator_target_not_found(self):
        """Error when target user not found."""
        service, mock_user_repo, *_ = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, None]

        with pytest.raises(ValidationError, match="target user not found"):
            service.confirm_remove_creator("token", 999, "delete")

    def test_confirm_remove_creator_not_creator(self):
        """Error when target is not a CREATOR."""
        service, mock_user_repo, *_ = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User); target.role = UserRole.PENDING_CREATOR  # Not a full CREATOR
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]

        with pytest.raises(ValidationError, match="user is not a creator"):
            service.confirm_remove_creator("token", 2, "delete")

    def test_confirm_remove_creator_invalid_action(self):
        """Error with invalid action parameter."""
        service, mock_user_repo, *_ = self._make_service()
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User); target.role = UserRole.CREATOR
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]

        with pytest.raises(ValidationError, match="invalid action"):
            service.confirm_remove_creator("token", 2, "burn")

    def test_confirm_remove_creator_delete_action(self):
        """Delete action: delete all published and draft puzzles."""
        service, mock_user_repo, mock_puzzle_repo, mock_solve_repo, mock_rating_repo, mock_audit_log, mock_notification_repo, _ = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User)
        target.role = UserRole.CREATOR
        target.username = "creator_to_delete"
        
        # Mock puzzles
        draft_p1 = Mock(spec=Puzzle); draft_p1.id = 20; draft_p1.name = "draft1"
        draft_p2 = Mock(spec=Puzzle); draft_p2.id = 21; draft_p2.name = "draft2"
        pub_p1 = Mock(spec=Puzzle); pub_p1.id = 30; pub_p1.name = "pub1"
        pub_p2 = Mock(spec=Puzzle); pub_p2.id = 31; pub_p2.name = "pub2"
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]
        mock_puzzle_repo.get_by_creator_and_status.side_effect = [
            [draft_p1, draft_p2],  # drafts
            [pub_p1, pub_p2],      # published
        ]
        mock_user_repo.update_role_if.return_value = True
        
        # Mock transaction context manager
        mock_puzzle_repo.conn.__enter__ = Mock(return_value=None)
        mock_puzzle_repo.conn.__exit__ = Mock(return_value=False)
        
        result = service.confirm_remove_creator("token", 2, "delete")
        
        assert result["ok"] is True
        assert result["new_role"] == UserRole.SOLVER.value
        assert result["action"] == "delete"
        assert result["draft_deleted"] == 2
        assert result["published_affected"] == 2
        
        # Verify puzzle deletions occurred
        mock_solve_repo.delete_by_puzzle_ids.assert_called()
        mock_rating_repo.delete_by_puzzle.assert_called()
        mock_puzzle_repo.track_user_deletion.assert_any_call("draft1")
        mock_puzzle_repo.track_admin_deletion.assert_any_call("pub1")
        mock_puzzle_repo.delete_by_ids.assert_called()
        
        # Verify audit log
        mock_audit_log.create.assert_called_once()
        audit_call = mock_audit_log.create.call_args[1]
        assert audit_call["admin_user_id"] == 1
        assert audit_call["action_type"] == AuditActionType.REMOVE_CREATOR.value
        assert audit_call["target_user_id"] == 2
        assert audit_call["details"]["draft_puzzles_deleted"] == 2
        assert audit_call["details"]["published_puzzles_action"] == "delete"
        
        # Verify notification
        mock_notification_repo.create.assert_called_once()
        notif_call = mock_notification_repo.create.call_args[1]
        assert notif_call["user_id"] == 2
        assert "deleted" in notif_call["message"].lower()

    def test_confirm_remove_creator_unpublish_action(self):
        """Unpublish action: unpublish published, delete draft puzzles."""
        service, mock_user_repo, mock_puzzle_repo, mock_solve_repo, mock_rating_repo, mock_audit_log, mock_notification_repo, _ = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User)
        target.role = UserRole.CREATOR
        
        draft_p1 = Mock(spec=Puzzle); draft_p1.id = 20; draft_p1.name = "draft1"
        pub_p1 = Mock(spec=Puzzle); pub_p1.id = 30; pub_p1.name = "pub1"; pub_p1.status = PuzzleStatus.PUBLISHED
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]
        mock_puzzle_repo.get_by_creator_and_status.side_effect = [
            [draft_p1],   # drafts
            [pub_p1],     # published
        ]
        mock_user_repo.update_role_if.return_value = True
        
        mock_puzzle_repo.conn.__enter__ = Mock(return_value=None)
        mock_puzzle_repo.conn.__exit__ = Mock(return_value=False)
        
        result = service.confirm_remove_creator("token", 2, "unpublish")
        
        assert result["ok"] is True
        assert result["action"] == "unpublish"
        assert result["draft_deleted"] == 1
        assert result["published_affected"] == 1
        
        # Verify puzzles were updated (unpublish)
        mock_puzzle_repo.update.assert_called()
        
        # Verify notification mentions unpublish
        notif_call = mock_notification_repo.create.call_args[1]
        assert "unpublished" in notif_call["message"].lower()

    def test_confirm_remove_creator_leave_action(self):
        """Leave action: keep published puzzles, delete draft puzzles."""
        service, mock_user_repo, mock_puzzle_repo, mock_solve_repo, mock_rating_repo, mock_audit_log, mock_notification_repo, _ = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User); target.role = UserRole.CREATOR
        
        draft_p1 = Mock(spec=Puzzle); draft_p1.id = 20; draft_p1.name = "draft1"
        pub_p1 = Mock(spec=Puzzle); pub_p1.id = 30; pub_p1.name = "pub1"
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]
        mock_puzzle_repo.get_by_creator_and_status.side_effect = [
            [draft_p1],   # drafts
            [pub_p1],     # published
        ]
        mock_user_repo.update_role_if.return_value = True
        
        mock_puzzle_repo.conn.__enter__ = Mock(return_value=None)
        mock_puzzle_repo.conn.__exit__ = Mock(return_value=False)
        
        result = service.confirm_remove_creator("token", 2, "leave")
        
        assert result["ok"] is True
        assert result["action"] == "leave"
        
        # Published puzzles should not be updated
        mock_puzzle_repo.update.assert_not_called()
        
        # Verify notification mentions puzzles remain published
        notif_call = mock_notification_repo.create.call_args[1]
        assert "remain published" in notif_call["message"].lower()

    def test_confirm_remove_creator_no_puzzles_at_all(self):
        """Confirm removal when creator has no puzzles."""
        service, mock_user_repo, mock_puzzle_repo, mock_solve_repo, mock_rating_repo, mock_audit_log, mock_notification_repo, _ = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User); target.role = UserRole.CREATOR
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]
        mock_puzzle_repo.get_by_creator_and_status.side_effect = [[], []]  # No puzzles
        mock_user_repo.update_role_if.return_value = True
        
        mock_puzzle_repo.conn.__enter__ = Mock(return_value=None)
        mock_puzzle_repo.conn.__exit__ = Mock(return_value=False)
        
        result = service.confirm_remove_creator("token", 2, "delete")
        
        assert result["ok"] is True
        assert result["draft_deleted"] == 0
        assert result["published_affected"] == 0

    def test_confirm_remove_creator_race_condition(self):
        """Error on race condition when role changes during operation."""
        service, mock_user_repo, mock_puzzle_repo, mock_solve_repo, mock_rating_repo, mock_audit_log, mock_notification_repo, _ = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        target = Mock(spec=User); target.role = UserRole.CREATOR
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.side_effect = [admin, target]
        mock_puzzle_repo.get_by_creator_and_status.side_effect = [[], []]
        mock_user_repo.update_role_if.return_value = False  # Role changed by another admin
        
        mock_puzzle_repo.conn.__enter__ = Mock(return_value=None)
        mock_puzzle_repo.conn.__exit__ = Mock(return_value=False)
        
        with pytest.raises(ValidationError, match="user role was changed by another admin"):
            service.confirm_remove_creator("token", 2, "delete")


class TestAdminServiceListPuzzles:
    """Tests for AdminService.list_puzzles (admin puzzle listing/moderation view)."""

    def _make_service(self):
        mock_user_repo = Mock()
        mock_user_repo.conn = Mock()
        mock_puzzle_repo = Mock()
        mock_solve_repo = Mock()
        mock_rating_repo = Mock()
        mock_audit_log = Mock()
        mock_notification_repo = Mock()
        mock_auth = Mock()
        
        service = AdminService(
            mock_user_repo, mock_puzzle_repo, mock_solve_repo,
            mock_rating_repo, mock_audit_log, mock_notification_repo, mock_auth,
        )
        return service, mock_user_repo, mock_puzzle_repo

    def test_list_puzzles_default_pagination(self):
        """List all puzzles with default pagination (limit=50, offset=0)."""
        service, mock_user_repo, mock_puzzle_repo = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        # Create multiple puzzle mocks
        p1 = Mock(spec=Puzzle)
        p1.id = 1
        p1.name = "Puzzle 1"
        p1.creator_user_id = 10
        p1.status = PuzzleStatus.PUBLISHED
        p1.avg_fun = 3.5
        p1.avg_clearness = 4.5
        p1.rating_count = 5
        p1.to_dict = Mock(return_value={"id": "1", "name": "Puzzle 1"})
        
        p2 = Mock(spec=Puzzle)
        p2.id = 2
        p2.name = "Puzzle 2"
        p2.creator_user_id = 11
        p2.status = PuzzleStatus.DRAFT
        p2.avg_fun = 0
        p2.avg_clearness = 0
        p2.rating_count = 0
        p2.to_dict = Mock(return_value={"id": "2", "name": "Puzzle 2"})
        
        creator1 = Mock(spec=User); creator1.to_dict = Mock(return_value={"id": "10", "username": "creator1"})
        creator2 = Mock(spec=User); creator2.to_dict = Mock(return_value={"id": "11", "username": "creator2"})
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_puzzle_repo.list_all_for_admin.return_value = [p1, p2]
        mock_puzzle_repo.count_all_for_admin.return_value = 2
        mock_user_repo.get_by_ids.return_value = {10: creator1, 11: creator2}
        
        result = service.list_puzzles("token")
        
        assert result["meta"]["total"] == 2
        assert result["meta"]["page"] == 1
        assert len(result["data"]) == 2
        
        # Verify call to list_all_for_admin with defaults
        mock_puzzle_repo.list_all_for_admin.assert_called_once_with(
            limit=50, offset=0, search=None, status=None, creator_id=None,
            creator_username=None, date_from=None, date_to=None,
            order_by="created_at", order_direction="DESC"
        )

    def test_list_puzzles_custom_limit_and_offset(self):
        """List puzzles with custom pagination."""
        service, mock_user_repo, mock_puzzle_repo = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_puzzle_repo.list_all_for_admin.return_value = []
        mock_puzzle_repo.count_all_for_admin.return_value = 100
        mock_user_repo.get_by_ids.return_value = {}
        
        result = service.list_puzzles("token", limit=20, offset=40)
        
        mock_puzzle_repo.list_all_for_admin.assert_called_once()
        call_kwargs = mock_puzzle_repo.list_all_for_admin.call_args[1]
        assert call_kwargs["limit"] == 20
        assert call_kwargs["offset"] == 40

    def test_list_puzzles_empty_list(self):
        """List puzzles returns empty list when no puzzles exist."""
        service, mock_user_repo, mock_puzzle_repo = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_puzzle_repo.list_all_for_admin.return_value = []
        mock_puzzle_repo.count_all_for_admin.return_value = 0
        mock_user_repo.get_by_ids.return_value = {}
        
        result = service.list_puzzles("token")
        
        assert result["data"] == []
        assert result["meta"]["total"] == 0
        assert result["meta"]["page"] == 1

    def test_list_puzzles_with_search_filter(self):
        """List puzzles with search filter."""
        service, mock_user_repo, mock_puzzle_repo = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_puzzle_repo.list_all_for_admin.return_value = []
        mock_puzzle_repo.count_all_for_admin.return_value = 0
        mock_user_repo.get_by_ids.return_value = {}
        
        result = service.list_puzzles("token", search="test")
        
        mock_puzzle_repo.list_all_for_admin.assert_called_once()
        call_kwargs = mock_puzzle_repo.list_all_for_admin.call_args[1]
        assert call_kwargs["search"] == "test"

    def test_list_puzzles_with_status_filter(self):
        """List puzzles filtered by status."""
        service, mock_user_repo, mock_puzzle_repo = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_puzzle_repo.list_all_for_admin.return_value = []
        mock_puzzle_repo.count_all_for_admin.return_value = 0
        mock_user_repo.get_by_ids.return_value = {}
        
        result = service.list_puzzles("token", status="published")
        
        mock_puzzle_repo.list_all_for_admin.assert_called_once()
        call_kwargs = mock_puzzle_repo.list_all_for_admin.call_args[1]
        assert call_kwargs["status"] == "published"

    def test_list_puzzles_enriches_with_moderation_flags(self):
        """List puzzles includes moderation flags for low ratings."""
        service, mock_user_repo, mock_puzzle_repo = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        puzzle = Mock(spec=Puzzle)
        puzzle.id = 1
        puzzle.name = "LowRated"
        puzzle.creator_user_id = 10
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.avg_fun = 1.5  # Below threshold
        puzzle.avg_clearness = 4.5
        puzzle.rating_count = 5
        puzzle_dict = {"id": "1", "name": "LowRated"}
        puzzle.to_dict = Mock(return_value=puzzle_dict)
        
        creator = Mock(spec=User)
        creator.to_dict = Mock(return_value={"id": "10", "username": "creator1"})
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_puzzle_repo.list_all_for_admin.return_value = [puzzle]
        mock_puzzle_repo.count_all_for_admin.return_value = 1
        mock_user_repo.get_by_ids.return_value = {10: creator}
        
        # Mock settings with threshold
        import Backend.settings as settings_module
        original_threshold = getattr(settings_module, 'MODERATION_LOW_FUN_THRESHOLD', 3.0)
        
        result = service.list_puzzles("token")
        
        assert len(result["data"]) == 1
        data = result["data"][0]
        # Note: flags will be set based on settings thresholds
        # We just verify the structure is there
        assert "flags" in data
        assert "creator" in data

    def test_list_puzzles_pagination_calculation(self):
        """Test pagination metadata is calculated correctly."""
        service, mock_user_repo, mock_puzzle_repo = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        service.auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_puzzle_repo.list_all_for_admin.return_value = []
        mock_puzzle_repo.count_all_for_admin.return_value = 155  # 155 puzzles
        mock_user_repo.get_by_ids.return_value = {}
        
        # Request with limit=50 should have 4 pages (ceiling division)
        result = service.list_puzzles("token", limit=50, offset=100)  # Page 3
        
        assert result["meta"]["total"] == 155
        assert result["meta"]["totalPages"] == 4
        assert result["meta"]["page"] == 3  # (100 // 50) + 1


class TestAdminServiceListAuditLog:
    """Tests for AdminService.list_audit_log (REQ 7.5)."""

    def _make_service(self):
        mock_user_repo = Mock()
        mock_user_repo.conn = Mock()
        mock_puzzle_repo = Mock()
        mock_solve_repo = Mock()
        mock_rating_repo = Mock()
        mock_audit_log = Mock()
        mock_notification_repo = Mock()
        mock_auth = Mock()
        
        service = AdminService(
            mock_user_repo, mock_puzzle_repo, mock_solve_repo,
            mock_rating_repo, mock_audit_log, mock_notification_repo, mock_auth,
        )
        return service, mock_user_repo, mock_audit_log, mock_auth

    def test_list_audit_log_default_pagination(self):
        """List audit log with default pagination."""
        service, mock_user_repo, mock_audit_log, mock_auth = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        audit_entry1 = {"id": 1, "action": "assign_creator", "target_user_id": 2}
        audit_entry2 = {"id": 2, "action": "remove_creator", "target_user_id": 3}
        
        mock_auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_audit_log.list_all.return_value = [audit_entry1, audit_entry2]
        
        result = service.list_audit_log("token")
        
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        
        # Verify call to list_all with defaults
        mock_audit_log.list_all.assert_called_once_with(
            limit=100, offset=0, action_type=None
        )

    def test_list_audit_log_custom_pagination(self):
        """List audit log with custom limit and offset."""
        service, mock_user_repo, mock_audit_log, mock_auth = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        mock_auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_audit_log.list_all.return_value = []
        
        result = service.list_audit_log("token", limit=50, offset=100)
        
        mock_audit_log.list_all.assert_called_once_with(
            limit=50, offset=100, action_type=None
        )

    def test_list_audit_log_filter_by_action_type(self):
        """List audit log filtered by action type."""
        service, mock_user_repo, mock_audit_log, mock_auth = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        mock_auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_audit_log.list_all.return_value = []
        
        result = service.list_audit_log("token", action_type="remove_creator")
        
        mock_audit_log.list_all.assert_called_once_with(
            limit=100, offset=0, action_type="remove_creator"
        )

    def test_list_audit_log_empty(self):
        """List audit log returns empty when no entries exist."""
        service, mock_user_repo, mock_audit_log, mock_auth = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        mock_auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_audit_log.list_all.return_value = []
        
        result = service.list_audit_log("token")
        
        assert result == []

    def test_list_audit_log_includes_action_details(self):
        """Verify audit log entries include action details."""
        service, mock_user_repo, mock_audit_log, mock_auth = self._make_service()
        
        admin = Mock(spec=User); admin.role = UserRole.ADMIN
        
        audit_entry = {
            "id": 1,
            "admin_user_id": 1,
            "action_type": "remove_creator",
            "target_user_id": 5,
            "details": {
                "previous_role": "creator",
                "draft_puzzles_deleted": 2,
                "published_puzzles_action": "delete",
                "published_count": 3,
            },
            "created_at": "2024-01-15T10:30:00",
        }
        
        mock_auth.require_user_id.return_value = 1
        mock_user_repo.get_by_id.return_value = admin
        mock_audit_log.list_all.return_value = [audit_entry]
        
        result = service.list_audit_log("token")
        
        assert len(result) == 1
        assert result[0]["admin_user_id"] == 1
        assert result[0]["target_user_id"] == 5
        assert result[0]["details"]["draft_puzzles_deleted"] == 2

