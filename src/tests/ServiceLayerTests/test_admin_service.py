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

