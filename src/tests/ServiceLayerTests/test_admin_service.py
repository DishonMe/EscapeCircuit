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





class TestAdminServiceSetCreatorPuzzleLimits:
    """Tests for AdminService.set_creator_puzzle_limits."""

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

        self.mock_user_repo.conn = Mock()

    def _make_admin(self):
        a = Mock(spec=User)
        a.role = UserRole.ADMIN
        a.username = "admin"
        return a

    def _make_creator(self):
        from Backend.DomainLayer.User import User as RealUser
        return RealUser(id=2, username="creator", role=UserRole.CREATOR)

    def test_set_limits_success(self):
        admin = self._make_admin()
        creator = self._make_creator()

        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.side_effect = [admin, creator, creator]

        result = self.service.set_creator_puzzle_limits("token", 2, max_published=8, max_unpublished=6)

        assert result["ok"] is True
        assert result["max_published_puzzles"] == 8
        assert result["max_unpublished_puzzles"] == 6
        self.mock_user_repo.update_puzzle_limits.assert_called_once_with(2, 8, 6)
        self.mock_audit_log.create.assert_called_once()

    def test_set_limits_non_admin_rejected(self):
        solver = Mock(spec=User)
        solver.role = UserRole.SOLVER

        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = solver

        with pytest.raises(ValidationError) as exc:
            self.service.set_creator_puzzle_limits("token", 2, 5, 5)
        assert "admin required" in str(exc.value)

    def test_set_limits_target_not_found(self):
        admin = self._make_admin()
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.side_effect = [admin, None]

        with pytest.raises(ValidationError) as exc:
            self.service.set_creator_puzzle_limits("token", 99, 5, 5)
        assert "not found" in str(exc.value)

    def test_set_limits_target_not_creator(self):
        admin = self._make_admin()
        solver = Mock(spec=User)
        solver.role = UserRole.SOLVER

        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.side_effect = [admin, solver]

        with pytest.raises(ValidationError) as exc:
            self.service.set_creator_puzzle_limits("token", 2, 5, 5)
        assert "not a creator" in str(exc.value)  # "not a creator or pending creator"

    def test_set_limits_negative_values_rejected(self):
        admin = self._make_admin()
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin

        with pytest.raises(ValidationError) as exc:
            self.service.set_creator_puzzle_limits("token", 2, -1, 5)
        assert "negative" in str(exc.value)


class TestAdminServiceUnpublishPuzzle:
    """Tests for AdminService.unpublish_puzzle."""

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

        self.mock_puzzle_repo.conn = Mock()

    def _make_admin(self):
        a = Mock(spec=User)
        a.role = UserRole.ADMIN
        a.username = "admin"
        return a

    def test_unpublish_success(self):
        admin = self._make_admin()
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin

        puzzle = Puzzle(id=5, name="P", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        result = self.service.unpublish_puzzle("token", 5)

        assert result["ok"] is True
        assert result["new_status"] == PuzzleStatus.UNPUBLISHED.value
        self.mock_puzzle_repo.update.assert_called_once()
        self.mock_audit_log.create.assert_called_once()

    def test_unpublish_puzzle_not_found(self):
        admin = self._make_admin()
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin
        self.mock_puzzle_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc:
            self.service.unpublish_puzzle("token", 99)
        assert "not found" in str(exc.value)

    def test_unpublish_already_unpublished(self):
        admin = self._make_admin()
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin

        puzzle = Puzzle(id=5, name="P", creator_user_id=2, status=PuzzleStatus.UNPUBLISHED)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        with pytest.raises(ValidationError) as exc:
            self.service.unpublish_puzzle("token", 5)
        assert "not published" in str(exc.value)
