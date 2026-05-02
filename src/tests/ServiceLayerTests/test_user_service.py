import os
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from Backend.ServiceLayer.UserService import UserService
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole, AuditActionType
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService


class TestUserServiceCreation:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.service = UserService(self.mock_user_repo, self.mock_auth, self.mock_xp)

    def test_user_service_initialization(self):
        assert self.service.user_repo == self.mock_user_repo
        assert self.service.auth == self.mock_auth
        assert self.service.xp == self.mock_xp


class TestUserServiceRegister:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_user_repo.conn = Mock()  # register() calls conn.commit()
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.service = UserService(self.mock_user_repo, self.mock_auth, self.mock_xp)

    def test_register_success(self):
        payload = {
            "username": "newuser",
            "password": "secure123",
            "email": "newuser@example.com",
            "avatar_name": "Dinosaur",
            "avatar_color": "#38bdf8",
        }

        # Mock the User creation to avoid validation issues with id=0
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.username = "newuser"
        mock_user.role = UserRole.SOLVER
        mock_user.xp = 0
        mock_user.to_dict.return_value = {
            "id": 1,
            "username": "newuser",
            "role": "solver",
            "xp": 0,
            "created_at": "2024-01-01T00:00:00",
        }

        self.mock_user_repo.get_by_username.return_value = None
        self.mock_user_repo.get_by_email.return_value = None
        self.mock_user_repo.create.return_value = mock_user
        self.mock_xp.calculate_level.return_value = 1
        self.mock_xp.is_experienced.return_value = False

        # Mock auth login for auto-login (returns (token, user) tuple)
        self.mock_auth.login.return_value = ("auto_login_token", mock_user)

        # Patch User constructor to avoid id=0 validation error
        with patch('Backend.ServiceLayer.UserService.User', return_value=mock_user):
            result = self.service.register(payload)

        # Updated assertions for nested structure
        assert result["token"] == "auto_login_token"
        assert result["user"]["username"] == "newuser"
        assert result["user"]["role"] == "solver"
        assert result["user"]["level"] == 1
        assert result["user"]["is_experienced"] is False
        self.mock_user_repo.create.assert_called_once()


    def test_register_missing_username(self):
        payload = {"username": "", "password": "secure123"}

        with pytest.raises(ValidationError) as exc_info:
            self.service.register(payload)
        assert "username and password required" in str(exc_info.value)

    def test_register_missing_password(self):
        payload = {"username": "newuser", "password": ""}

        with pytest.raises(ValidationError) as exc_info:
            self.service.register(payload)
        assert "username and password required" in str(exc_info.value)

    def test_register_username_already_exists(self):
        payload = {
            "username": "existing",
            "password": "secure123",
            "email": "test@example.com",
            "avatar_name": "Dinosaur",
        }
        existing_user = User(id=1, username="existing")

        self.mock_user_repo.get_by_username.return_value = existing_user

        with pytest.raises(ValidationError) as exc_info:
            self.service.register(payload)
        assert "username already exists" in str(exc_info.value)

    def test_register_whitespace_username(self):
        payload = {"username": "   ", "password": "secure123"}

        with pytest.raises(ValidationError):
            self.service.register(payload)


class TestUserServiceLogin:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.service = UserService(self.mock_user_repo, self.mock_auth, self.mock_xp)

    def test_login_success(self):
        payload = {"username": "testuser", "password": "secure123"}

        user_mock = Mock(spec=User)
        user_mock.xp = 100
        # to_dict must return a REAL dictionary so we can assign to it
        user_mock.to_dict.return_value = {"username": "testuser", "xp": 100}

        # auth.login now returns (token, user) tuple
        self.mock_auth.login.return_value = ("session_token_xyz", user_mock)
        self.mock_xp.calculate_level.return_value = 2
        self.mock_xp.is_experienced.return_value = False

        result = self.service.login(payload)

        assert result["token"] == "session_token_xyz"
        assert result["user"]["username"] == "testuser"
        assert result["user"]["level"] == 2
        self.mock_auth.login.assert_called_once_with("testuser", "secure123")

    def test_login_invalid_credentials(self):
        payload = {"username": "testuser", "password": "wrongpass"}
        self.mock_auth.login.side_effect = ValidationError("invalid credentials")

        with pytest.raises(ValidationError) as exc_info:
            self.service.login(payload)
        assert "invalid credentials" in str(exc_info.value)

    def test_login_missing_username(self):
        payload = {"username": "", "password": "secure123"}
        self.mock_auth.login.side_effect = ValidationError("username and password required")

        with pytest.raises(ValidationError):
            self.service.login(payload)


class TestUserServiceLogout:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.service = UserService(self.mock_user_repo, self.mock_auth, self.mock_xp)

    def test_logout_success(self):
        self.mock_auth.require_user_id.return_value = 1

        result = self.service.logout("valid_token")

        assert result["ok"] is True
        self.mock_auth.require_user_id.assert_called_once_with("valid_token")
        self.mock_auth.logout.assert_called_once_with("valid_token")

    def test_logout_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        with pytest.raises(ValidationError):
            self.service.logout("invalid_token")


class TestUserServiceMe:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_user_repo.conn = Mock()  # me() uses conn for medal/arsenal queries
        self.mock_user_repo.conn.execute.return_value.fetchall.return_value = []
        self.mock_user_repo.conn.execute.return_value.fetchone.return_value = None
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.service = UserService(self.mock_user_repo, self.mock_auth, self.mock_xp)

    def test_me_success(self):
        user = User(id=1, username="testuser", role=UserRole.SOLVER, xp=100)
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = user
        self.mock_xp.calculate_level.return_value = 2
        self.mock_xp.is_experienced.return_value = False

        result = self.service.me("valid_token")

        assert result["username"] == "testuser"
        assert result["level"] == 2
        assert result["is_experienced"] is False
        self.mock_auth.require_user_id.assert_called_once_with("valid_token")

    def test_me_user_not_found(self):
        self.mock_auth.require_user_id.return_value = 999
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.me("valid_token")
        assert "user not found" in str(exc_info.value)

    def test_me_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        with pytest.raises(ValidationError):
            self.service.me("invalid_token")


class TestUserServiceListUsers:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.service = UserService(self.mock_user_repo, self.mock_auth, self.mock_xp)

    def test_list_users_success(self):
        self.mock_auth.require_user_id.return_value = 1
        users = [
            User(id=1, username="user1", xp=100),
            User(id=2, username="user2", xp=200),
        ]
        self.mock_user_repo.list_all.return_value = users
        self.mock_user_repo.count_all.return_value = 2
        self.mock_xp.calculate_level.side_effect = [2, 3]
        self.mock_xp.is_experienced.side_effect = [False, False]

        result = self.service.list_users("valid_token")

        assert len(result["data"]) == 2
        assert result["data"][0]["username"] == "user1"
        assert result["data"][1]["username"] == "user2"
        assert result["total"] == 2
        self.mock_user_repo.list_all.assert_called_once()

    def test_list_users_with_pagination(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.list_all.return_value = []
        self.mock_user_repo.count_all.return_value = 0

        result = self.service.list_users("valid_token", limit=50, offset=100)

        self.mock_user_repo.list_all.assert_called_once()
        assert result["total"] == 0
        assert result["limit"] == 50
        assert result["offset"] == 100

    def test_list_users_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        with pytest.raises(ValidationError):
            self.service.list_users("invalid_token")


class TestUserServiceSetRole:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_user_repo.conn = Mock()
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.service = UserService(self.mock_user_repo, self.mock_auth, self.mock_xp)

    def test_set_role_success(self):
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        payload = {"target_user_id": 2, "role": "creator"}

        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin_user

        result = self.service.set_role("valid_token", payload)

        assert result["ok"] is True
        self.mock_user_repo.update_role.assert_called_once()

    def test_set_role_not_admin(self):
        non_admin_user = User(id=2, username="user", role=UserRole.SOLVER)
        payload = {"target_user_id": 3, "role": "CREATOR"}

        self.mock_auth.require_user_id.return_value = 2
        self.mock_user_repo.get_by_id.return_value = non_admin_user

        with pytest.raises(ValidationError) as exc_info:
            self.service.set_role("valid_token", payload)
        assert "admin required" in str(exc_info.value)

    def test_set_role_missing_target_user_id(self):
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        payload = {"role": "creator"}

        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin_user

        with pytest.raises(ValidationError) as exc_info:
            self.service.set_role("valid_token", payload)
        assert "target_user_id required" in str(exc_info.value)

    def test_set_role_missing_role(self):
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        payload = {"target_user_id": 2}

        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin_user

        with pytest.raises(ValidationError) as exc_info:
            self.service.set_role("valid_token", payload)
        assert "role required" in str(exc_info.value)

    def test_set_role_admin_user_not_found(self):
        payload = {"target_user_id": 2, "role": "creator"}

        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.set_role("valid_token", payload)
        assert "user not found" in str(exc_info.value) or "admin required" in str(exc_info.value)


class TestUserServiceAcceptCreatorRole:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_user_repo.conn = Mock()
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.service = UserService(self.mock_user_repo, self.mock_auth, self.mock_xp)

    def test_accept_creator_role_success(self):
        pending_user = User(id=2, username="pending", role=UserRole.PENDING_CREATOR, xp=100)
        self.mock_auth.require_user_id.return_value = 2
        self.mock_user_repo.get_by_id.return_value = pending_user
        self.mock_user_repo.update_role_if.return_value = True
        self.mock_xp.calculate_level.return_value = 3
        self.mock_xp.is_experienced.return_value = False

        result = self.service.accept_creator_role("valid_token")

        assert result["ok"] is True
        assert result["new_role"] == "creator"
        self.mock_user_repo.update_role_if.assert_called_once_with(2, UserRole.CREATOR, UserRole.PENDING_CREATOR)

    def test_accept_creator_role_user_not_found(self):
        self.mock_auth.require_user_id.return_value = 2
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.accept_creator_role("valid_token")
        assert "user not found" in str(exc_info.value)

    def test_accept_creator_role_no_pending_invitation(self):
        solver_user = User(id=2, username="solver", role=UserRole.SOLVER, xp=100)
        self.mock_auth.require_user_id.return_value = 2
        self.mock_user_repo.get_by_id.return_value = solver_user

        with pytest.raises(ValidationError) as exc_info:
            self.service.accept_creator_role("valid_token")
        assert "no pending creator invitation" in str(exc_info.value)

    def test_accept_creator_role_atomic_check_failed(self):
        pending_user = User(id=2, username="pending", role=UserRole.PENDING_CREATOR, xp=100)
        self.mock_auth.require_user_id.return_value = 2
        self.mock_user_repo.get_by_id.return_value = pending_user
        self.mock_user_repo.update_role_if.return_value = False

        with pytest.raises(ValidationError) as exc_info:
            self.service.accept_creator_role("valid_token")
        assert "no pending creator invitation" in str(exc_info.value)


class TestUserServiceDeclineCreatorRole:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_user_repo.conn = Mock()
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.service = UserService(self.mock_user_repo, self.mock_auth, self.mock_xp)

    def test_decline_creator_role_success(self):
        pending_user = User(id=2, username="pending", role=UserRole.PENDING_CREATOR, xp=100)
        self.mock_auth.require_user_id.return_value = 2
        self.mock_user_repo.get_by_id.return_value = pending_user
        self.mock_user_repo.update_role_if.return_value = True
        self.mock_xp.calculate_level.return_value = 3
        self.mock_xp.is_experienced.return_value = False

        result = self.service.decline_creator_role("valid_token")

        assert result["ok"] is True
        assert result["new_role"] == "solver"
        self.mock_user_repo.update_role_if.assert_called_once_with(2, UserRole.SOLVER, UserRole.PENDING_CREATOR)

    def test_decline_creator_role_user_not_found(self):
        self.mock_auth.require_user_id.return_value = 2
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.decline_creator_role("valid_token")
        assert "user not found" in str(exc_info.value)

    def test_decline_creator_role_no_pending_invitation(self):
        creator_user = User(id=2, username="creator", role=UserRole.CREATOR, xp=100)
        self.mock_auth.require_user_id.return_value = 2
        self.mock_user_repo.get_by_id.return_value = creator_user

        with pytest.raises(ValidationError) as exc_info:
            self.service.decline_creator_role("valid_token")
        assert "no pending creator invitation" in str(exc_info.value)

    def test_decline_creator_role_atomic_check_failed(self):
        pending_user = User(id=2, username="pending", role=UserRole.PENDING_CREATOR, xp=100)
        self.mock_auth.require_user_id.return_value = 2
        self.mock_user_repo.get_by_id.return_value = pending_user
        self.mock_user_repo.update_role_if.return_value = False

        with pytest.raises(ValidationError) as exc_info:
            self.service.decline_creator_role("valid_token")
        assert "no pending creator invitation" in str(exc_info.value)


class TestUserServiceDeleteUser:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_user_repo.conn = Mock()
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.mock_audit_log = Mock()
        self.service = UserService(
            self.mock_user_repo,
            self.mock_auth,
            self.mock_xp,
            audit_log_repo=self.mock_audit_log,
        )

    def test_delete_user_success(self):
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        target_user = User(id=2, username="target", role=UserRole.SOLVER)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.side_effect = [admin_user, target_user]
        self.mock_user_repo.delete.return_value = True

        result = self.service.delete_user("valid_token", 2)

        assert result["ok"] is True
        self.mock_user_repo.delete.assert_called_once_with(2)
        self.mock_audit_log.create.assert_called_once()
        audit_call = self.mock_audit_log.create.call_args[1]
        assert audit_call["admin_user_id"] == 1
        assert audit_call["action_type"] == AuditActionType.DELETE_USER.value
        assert audit_call["target_user_id"] == 2
        assert audit_call["details"]["target_username"] == "target"

    def test_delete_user_non_admin(self):
        solver_user = User(id=1, username="solver", role=UserRole.SOLVER)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = solver_user

        with pytest.raises(ValidationError) as exc_info:
            self.service.delete_user("valid_token", 2)
        assert "admin required" in str(exc_info.value)

    def test_delete_user_cannot_delete_self(self):
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin_user

        with pytest.raises(ValidationError) as exc_info:
            self.service.delete_user("valid_token", 1)
        assert "cannot delete yourself" in str(exc_info.value)

    def test_delete_user_target_not_found(self):
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.side_effect = [admin_user, None]

        with pytest.raises(ValidationError) as exc_info:
            self.service.delete_user("valid_token", 99)
        assert "user not found" in str(exc_info.value)

    def test_delete_user_delete_failed(self):
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        target_user = User(id=2, username="target", role=UserRole.SOLVER)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.side_effect = [admin_user, target_user]
        self.mock_user_repo.delete.return_value = False

        with pytest.raises(ValidationError) as exc_info:
            self.service.delete_user("valid_token", 2)
        assert "user not found" in str(exc_info.value)


class TestUserServiceGoogleLogin:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.service = UserService(self.mock_user_repo, self.mock_auth, self.mock_xp)

    @patch.dict(os.environ, {}, clear=True)
    def test_google_login_disabled(self):
        with pytest.raises(ValidationError) as exc_info:
            self.service.google_login("some_token")
        assert "google_login_disabled" in str(exc_info.value)

    def test_google_login_missing_token(self):
        with pytest.raises(ValidationError) as exc_info:
            self.service.google_login("")
        assert "token is required" in str(exc_info.value)

    @patch("Backend.ServiceLayer.UserService.google_id_token.verify_oauth2_token")
    @patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test_client_id"})
    def test_google_login_invalid_token(self, mock_verify):
        mock_verify.side_effect = Exception("Invalid token")

        with pytest.raises(ValidationError) as exc_info:
            self.service.google_login("invalid_token")
        assert "invalid google token" in str(exc_info.value)

    @patch("Backend.ServiceLayer.UserService.google_id_token.verify_oauth2_token")
    @patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test_client_id"})
    def test_google_login_new_user(self, mock_verify):
        mock_verify.return_value = {
            "email": "newuser@example.com",
            "name": "New User"
        }
        self.mock_user_repo.get_by_email.return_value = None

        result = self.service.google_login("valid_token")

        assert result["requires_password"] is True
        assert result["email"] == "newuser@example.com"
        assert result["name"] == "New User"

    @patch("Backend.ServiceLayer.UserService.google_id_token.verify_oauth2_token")
    @patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test_client_id"})
    def test_google_login_existing_user(self, mock_verify):
        mock_verify.return_value = {
            "email": "existing@example.com",
            "name": "Existing User"
        }
        existing_user = User(id=1, username="existing", email="existing@example.com", xp=100)
        self.mock_user_repo.get_by_email.return_value = existing_user
        self.mock_auth.login_external.return_value = "session_token"
        self.mock_xp.calculate_level.return_value = 3
        self.mock_xp.is_experienced.return_value = True

        result = self.service.google_login("valid_token")

        assert "token" in result
        assert result["user"]["username"] == "existing"
        self.mock_auth.login_external.assert_called_once_with(1)


class TestUserServiceGoogleCompleteRegistration:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_user_repo.conn = Mock()
        self.mock_auth = Mock(spec=AuthService)
        self.mock_xp = Mock(spec=XPService)
        self.service = UserService(self.mock_user_repo, self.mock_auth, self.mock_xp)

    def test_google_complete_registration_missing_token(self):
        payload = {"username": "newuser", "password": "secure123"}

        with pytest.raises(ValidationError) as exc_info:
            self.service.google_complete_registration(payload)
        assert "token is required" in str(exc_info.value)

    def test_google_complete_registration_missing_credentials(self):
        payload = {"token": "valid_token", "username": ""}

        with pytest.raises(ValidationError) as exc_info:
            self.service.google_complete_registration(payload)
        assert "username and password required" in str(exc_info.value)

    @patch.dict(os.environ, {}, clear=True)
    def test_google_complete_registration_disabled(self):
        payload = {
            "token": "valid_token",
            "username": "newuser",
            "password": "secure123",
            "avatar_name": "Dinosaur",
            "avatar_color": "#38bdf8",
        }

        with pytest.raises(ValidationError) as exc_info:
            self.service.google_complete_registration(payload)
        assert "google_login_disabled" in str(exc_info.value)

    @patch("Backend.ServiceLayer.UserService.google_id_token.verify_oauth2_token")
    @patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test_client_id"})
    def test_google_complete_registration_invalid_token(self, mock_verify):
        mock_verify.side_effect = Exception("Invalid token")
        payload = {
            "token": "invalid_token",
            "username": "newuser",
            "password": "secure123",
            "avatar_name": "Dinosaur",
            "avatar_color": "#38bdf8",
        }

        with pytest.raises(ValidationError) as exc_info:
            self.service.google_complete_registration(payload)
        assert "invalid google token" in str(exc_info.value)

    @patch("Backend.ServiceLayer.UserService.google_id_token.verify_oauth2_token")
    @patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test_client_id"})
    def test_google_complete_registration_create_new_user(self, mock_verify):
        mock_verify.return_value = {
            "email": "newuser@example.com",
            "name": "New User"
        }
        created_user = User(id=5, username="newuser", email="newuser@example.com", xp=0, avatar_name="Dinosaur", avatar_color="#38bdf8")
        self.mock_user_repo.get_by_email.side_effect = [None, None]
        self.mock_user_repo.get_by_username.return_value = None
        self.mock_user_repo.create.return_value = created_user
        self.mock_auth.login_external.return_value = "session_token"
        self.mock_xp.calculate_level.return_value = 1
        self.mock_xp.is_experienced.return_value = False

        payload = {
            "token": "valid_token",
            "username": "newuser",
            "password": "secure123",
            "avatar_name": "Dinosaur",
            "avatar_color": "#38bdf8",
        }
        result = self.service.google_complete_registration(payload)

        assert "token" in result
        assert result["user"]["username"] == "newuser"
        self.mock_user_repo.create.assert_called_once()

    @patch("Backend.ServiceLayer.UserService.google_id_token.verify_oauth2_token")
    @patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test_client_id"})
    def test_google_complete_registration_link_existing_email(self, mock_verify):
        mock_verify.return_value = {
            "email": "existing@example.com",
            "name": "Existing User"
        }
        existing_user = User(id=1, username="existing", email="existing@example.com", xp=100)
        self.mock_user_repo.get_by_email.return_value = existing_user
        self.mock_auth.login_external.return_value = "session_token"
        self.mock_xp.calculate_level.return_value = 3
        self.mock_xp.is_experienced.return_value = True

        payload = {
            "token": "valid_token",
            "username": "anyusername",
            "password": "secure123",
            "avatar_name": "Dinosaur",
            "avatar_color": "#38bdf8",
        }
        result = self.service.google_complete_registration(payload)

        assert "token" in result
        assert result["user"]["username"] == "existing"
        self.mock_user_repo.create.assert_not_called()

    @patch("Backend.ServiceLayer.UserService.google_id_token.verify_oauth2_token")
    @patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test_client_id"})
    def test_google_complete_registration_username_exists(self, mock_verify):
        mock_verify.return_value = {
            "email": "newuser@example.com",
            "name": "New User"
        }
        self.mock_user_repo.get_by_email.return_value = None
        self.mock_user_repo.get_by_username.return_value = User(id=2, username="newuser")

        payload = {
            "token": "valid_token",
            "username": "newuser",
            "password": "secure123",
            "avatar_name": "Dinosaur",
            "avatar_color": "#38bdf8",
        }

        with pytest.raises(ValidationError) as exc_info:
            self.service.google_complete_registration(payload)
        assert "username already exists" in str(exc_info.value)
