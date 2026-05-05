import pytest
import time
import threading
from unittest.mock import Mock, patch
from typing import Dict, Any

from Backend.ServiceLayer.AuthService import AuthService, SessionInfo
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.UserRepo import UserRepo


class TestSessionInfo:
    def test_session_info_creation(self):
        now = time.time()
        session = SessionInfo(user_id=1, created_at=now, last_seen=now)

        assert session.user_id == 1
        assert session.created_at == now
        assert session.last_seen == now

    def test_session_info_is_frozen(self):
        now = time.time()
        session = SessionInfo(user_id=1, created_at=now, last_seen=now)

        with pytest.raises(AttributeError):
            session.user_id = 2


class TestAuthServiceCreation:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        # Mock conn for password verification
        mock_conn = Mock()
        mock_row = {"pw_salt": b"salt", "pw_hash": UserRepo._hash_password("password123", b"salt")}
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        self.mock_user_repo.conn = mock_conn
        self.service = AuthService(self.mock_user_repo)

    def test_auth_service_initialization(self):
        assert self.service.user_repo == self.mock_user_repo
        assert self.service.session_ttl_seconds == 24 * 60 * 60
        assert self.service._sessions == {}

    def test_auth_service_custom_ttl(self):
        service = AuthService(self.mock_user_repo, session_ttl_seconds=3600)
        assert service.session_ttl_seconds == 3600


class TestAuthServiceLogin:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        # Mock conn for password verificat ion
        mock_conn = Mock()
        mock_row = {"pw_salt": b"salt", "pw_hash": UserRepo._hash_password("password123", b"salt")}
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        self.mock_user_repo.conn = mock_conn
        self.service = AuthService(self.mock_user_repo)

    def test_login_success(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user

        token, _ = self.service.login("testuser", "password123")

        assert isinstance(token, str)
        assert len(token) > 0
        assert token in self.service._sessions
        assert self.service._sessions[token].user_id == 1

    def test_login_invalid_credentials(self):
        self.mock_user_repo.get_by_username.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.login("testuser", "wrongpassword")
        assert "Invalid username/email or password" in str(exc_info.value)

    def test_login_missing_username(self):
        with pytest.raises(ValidationError) as exc_info:
            self.service.login("", "password123")
        assert "password are required" in str(exc_info.value)

    def test_login_missing_password(self):
        with pytest.raises(ValidationError) as exc_info:
            self.service.login("testuser", "")
        assert "password are required" in str(exc_info.value)

    def test_login_whitespace_username(self):
        with pytest.raises(ValidationError) as exc_info:
            self.service.login("   ", "password123")
        assert "password are required" in str(exc_info.value)

    def test_login_multiple_sessions(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user

        token1, _ = self.service.login("testuser", "password123")
        token2, _ = self.service.login("testuser", "password123")

        assert token1 != token2
        assert len(self.service._sessions) == 2


class TestAuthServiceLogout:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        # Mock conn for password verification
        mock_conn = Mock()
        mock_row = {"pw_salt": b"salt", "pw_hash": UserRepo._hash_password("password123", b"salt")}
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        self.mock_user_repo.conn = mock_conn
        self.service = AuthService(self.mock_user_repo)

    def test_logout_success(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user

        token, _ = self.service.login("testuser", "password123")
        assert token in self.service._sessions

        self.service.logout(token)

        assert token not in self.service._sessions

    def test_logout_nonexistent_token(self):
        # Should not raise, just be a no-op
        self.service.logout("nonexistent_token")
        assert "nonexistent_token" not in self.service._sessions

    def test_logout_empty_token(self):
        # Should not raise
        self.service.logout("")
        self.service.logout(None)

    def test_logout_already_expired(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user

        token, _ = self.service.login("testuser", "password123")
        del self.service._sessions[token]

        self.service.logout(token)
        assert token not in self.service._sessions


class TestAuthServiceRequireUserID:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        # Mock conn for password verification
        mock_conn = Mock()
        mock_row = {"pw_salt": b"salt", "pw_hash": UserRepo._hash_password("password123", b"salt")}
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        self.mock_user_repo.conn = mock_conn
        self.service = AuthService(self.mock_user_repo, session_ttl_seconds=3600)

    def test_require_user_id_valid_token(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user
        self.mock_user_repo.get_by_id.return_value = user

        token, _ = self.service.login("testuser", "password123")

        user_id = self.service.require_user_id(token)

        assert user_id == 1
        # Verify sliding expiration updated last_seen or kept same time
        # (they might be the same if called quickly)
        assert self.service._sessions[token].last_seen >= self.service._sessions[token].created_at

    def test_require_user_id_invalid_token(self):
        with pytest.raises(ValidationError) as exc_info:
            self.service.require_user_id("invalid_token")
        assert "unauthorized" in str(exc_info.value)

    def test_require_user_id_empty_token(self):
        with pytest.raises(ValidationError) as exc_info:
            self.service.require_user_id("")
        assert "unauthorized" in str(exc_info.value)

    def test_require_user_id_expired_session(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user

        token, _ = self.service.login("testuser", "password123")

        # Manually expire the session
        session = self.service._sessions[token]
        self.service._sessions[token] = SessionInfo(
            user_id=session.user_id,
            created_at=session.created_at,
            last_seen=time.time() - 7200,  # 2 hours ago
        )

        with pytest.raises(ValidationError):
            self.service.require_user_id(token)

        # Verify token was removed
        assert token not in self.service._sessions

    def test_require_user_id_user_deleted(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user

        token, _ = self.service.login("testuser", "password123")

        # User is deleted from repo
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.require_user_id(token)
        assert "unauthorized" in str(exc_info.value)

    def test_require_user_id_sliding_expiration(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user
        self.mock_user_repo.get_by_id.return_value = user

        token, _ = self.service.login("testuser", "password123")
        initial_last_seen = self.service._sessions[token].last_seen

        # Wait a bit and check again
        time.sleep(0.1)
        self.service.require_user_id(token)

        updated_last_seen = self.service._sessions[token].last_seen

        assert updated_last_seen > initial_last_seen


class TestAuthServiceCleanupExpired:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        # Mock conn for password verification
        mock_conn = Mock()
        mock_row = {"pw_salt": b"salt", "pw_hash": UserRepo._hash_password("password123", b"salt")}
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        self.mock_user_repo.conn = mock_conn
        # Short TTL for testing
        self.service = AuthService(self.mock_user_repo, session_ttl_seconds=1)

    def test_cleanup_removes_expired_sessions(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user

        token, _ = self.service.login("testuser", "password123")

        # Manually set session as expired
        session = self.service._sessions[token]
        self.service._sessions[token] = SessionInfo(
            user_id=session.user_id,
            created_at=session.created_at,
            last_seen=time.time() - 10,  # 10 seconds ago (expired with TTL=1)
        )

        # Cleanup should be called on next login attempt
        user2 = User(id=2, username="testuser2")
        self.mock_user_repo.get_by_username.return_value = user2
        self.service.login("testuser2", "password123")

        # Old expired token should be removed
        assert token not in self.service._sessions


class TestAuthServiceThreadSafety:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        # Mock conn for password verification
        mock_conn = Mock()
        mock_row = {"pw_salt": b"salt", "pw_hash": UserRepo._hash_password("password123", b"salt")}
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        self.mock_user_repo.conn = mock_conn
        self.service = AuthService(self.mock_user_repo)

    def test_concurrent_logins(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user

        tokens = []

        def login_task():
            token, _ = self.service.login("testuser", "password123")
            tokens.append(token)

        threads = [threading.Thread(target=login_task) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All tokens should be unique
        assert len(tokens) == 5
        assert len(set(tokens)) == 5

        # All should be in sessions
        for token in tokens:
            assert token in self.service._sessions

    def test_concurrent_logouts(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user

        tokens = [self.service.login("testuser", "password123")[0] for _ in range(5)]

        def logout_task(token):
            self.service.logout(token)

        threads = [threading.Thread(target=logout_task, args=(t,)) for t in tokens]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All should be removed
        for token in tokens:
            assert token not in self.service._sessions

class TestAuthServiceCleanupDuringLogout:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        # Mock conn for password verification
        mock_conn = Mock()
        mock_row = {"pw_salt": b"salt", "pw_hash": UserRepo._hash_password("password123", b"salt")}
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        self.mock_user_repo.conn = mock_conn
        # Use short TTL to easily expire sessions
        self.service = AuthService(self.mock_user_repo, session_ttl_seconds=1)

    def test_logout_triggers_cleanup_of_expired_sessions(self):
        """Test that require_user_id cleans up expired sessions"""
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user
        self.mock_user_repo.get_by_id.return_value = user

        # Create a token
        token1, _ = self.service.login("testuser", "password123")

        assert len(self.service._sessions) == 1

        # Manually expire the token
        session = self.service._sessions[token1]
        self.service._sessions[token1] = SessionInfo(
            user_id=session.user_id,
            created_at=session.created_at,
            last_seen=time.time() - 10,  # 10 seconds ago (expired)
        )

        # Require user ID on the expired session should clean it up
        with pytest.raises(ValidationError):
            self.service.require_user_id(token1)

        # Token should be gone
        assert token1 not in self.service._sessions


class TestAuthServiceNoneInputs:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        # Mock conn for password verification
        mock_conn = Mock()
        mock_row = {"pw_salt": b"salt", "pw_hash": UserRepo._hash_password("password123", b"salt")}
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        self.mock_user_repo.conn = mock_conn
        # Mock conn for password verification
        mock_conn = Mock()
        mock_row = {"pw_salt": b"salt", "pw_hash": UserRepo._hash_password("password123", b"salt")}
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        self.mock_user_repo.conn = mock_conn
        self.service = AuthService(self.mock_user_repo)

    def test_login_with_none_password(self):
        """Test login with None password"""
        with pytest.raises(ValidationError) as exc_info:
            self.service.login("testuser", None)
        assert "password are required" in str(exc_info.value)

    def test_login_with_none_username(self):
        """Test login with None username"""
        with pytest.raises(ValidationError) as exc_info:
            self.service.login(None, "password")
        assert "password are required" in str(exc_info.value)

    def test_logout_with_whitespace_token(self):
        """Test logout with only whitespace token"""
        # Should not raise, just be a no-op
        self.service.logout("   ")
        assert len(self.service._sessions) == 0

    def test_require_user_id_with_whitespace_token(self):
        """Test require_user_id with only whitespace token"""
        with pytest.raises(ValidationError) as exc_info:
            self.service.require_user_id("   ")
        assert "unauthorized" in str(exc_info.value)

    def test_require_user_id_with_none_token(self):
        """Test require_user_id with None token"""
        with pytest.raises(ValidationError) as exc_info:
            self.service.require_user_id(None)
        assert "unauthorized" in str(exc_info.value)

    def test_cleanup_expired_during_require_user_id(self):
        """Test that cleanup_expired_locked is called during require_user_id"""
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user
        self.mock_user_repo.get_by_id.return_value = user

        token1, _ = self.service.login("testuser", "password123")
        token2, _ = self.service.login("testuser", "password123")
        
        # Manually expire token1
        session = self.service._sessions[token1]
        self.service._sessions[token1] = SessionInfo(
            user_id=session.user_id,
            created_at=session.created_at,
            last_seen=time.time() - 100000  # Very old
        )

        # require_user_id triggers cleanup that removes token1
        user_id = self.service.require_user_id(token2)

        # token1 should be gone, token2 should still be there
        assert token1 not in self.service._sessions
        assert token2 in self.service._sessions
        assert user_id == 1

    def test_require_user_id_updates_session_last_seen(self):
        """Test that require_user_id updates the last_seen timestamp"""
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user
        self.mock_user_repo.get_by_id.return_value = user

        token, _ = self.service.login("testuser", "password123")
        
        # Get the original last_seen
        original_session = self.service._sessions[token]
        original_last_seen = original_session.last_seen
        
        # Wait a bit and call require_user_id
        time.sleep(0.01)
        user_id = self.service.require_user_id(token)

        # Verify the session was updated with a new last_seen
        updated_session = self.service._sessions[token]
        assert updated_session.last_seen > original_last_seen
        assert user_id == 1

class TestExpiration:
    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        # Mock conn for password verification
        mock_conn = Mock()
        mock_row = {"pw_salt": b"salt", "pw_hash": UserRepo._hash_password("password123", b"salt")}
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        self.mock_user_repo.conn = mock_conn
        # Use short TTL for testing
        self.service = AuthService(self.mock_user_repo, session_ttl_seconds=1)

    def test_session_expires_after_ttl(self):
        user = User(id=1, username="testuser")
        self.mock_user_repo.get_by_username.return_value = user
        self.mock_user_repo.get_by_id.return_value = user

        token, _ = self.service.login("testuser", "password123")
        with patch.object(self.service, '_cleanup_expired_locked'):
        # Initially valid
            user_id = self.service.require_user_id(token)
            assert user_id == 1

        # Wait for expiration (TTL is 1 second, sleep for 1.2 seconds)
        time.sleep(1.2)

        with pytest.raises(ValidationError) as exc_info:
            self.service.require_user_id(token)
        assert "unauthorized" in str(exc_info.value)

        # Token should be removed
        assert token not in self.service._sessions


class TestAuthServiceLoginWithEmail:
    """Test login() method with email identification"""

    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        # Mock conn for password verification
        mock_conn = Mock()
        mock_row = {"pw_salt": b"salt", "pw_hash": UserRepo._hash_password("password123", b"salt")}
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        self.mock_user_repo.conn = mock_conn
        self.service = AuthService(self.mock_user_repo)

    def test_login_with_email_address(self):
        """Test login using email address instead of username"""
        user = User(id=1, username="testuser", email="test@example.com")
        self.mock_user_repo.get_by_email.return_value = user

        token, returned_user = self.service.login("test@example.com", "password123")

        assert isinstance(token, str)
        assert len(token) > 0
        assert token in self.service._sessions
        assert self.service._sessions[token].user_id == 1
        # Verify get_by_email was called (not get_by_username)
        self.mock_user_repo.get_by_email.assert_called_once_with("test@example.com")
        self.mock_user_repo.get_by_username.assert_not_called()
        assert returned_user.id == 1

    def test_login_email_user_not_found(self):
        """Test login with email that doesn't exist"""
        self.mock_user_repo.get_by_email.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.login("nonexistent@example.com", "password123")
        assert "Invalid username/email or password" in str(exc_info.value)

    def test_login_email_invalid_password(self):
        """Test login with email but wrong password"""
        user = User(id=1, username="testuser", email="test@example.com")
        self.mock_user_repo.get_by_email.return_value = user

        with pytest.raises(ValidationError) as exc_info:
            self.service.login("test@example.com", "wrongpassword")
        assert "Invalid username/email or password" in str(exc_info.value)

    def test_login_email_with_whitespace(self):
        """Test login with email that has leading/trailing whitespace"""
        user = User(id=1, username="testuser", email="test@example.com")
        self.mock_user_repo.get_by_email.return_value = user

        token, _ = self.service.login("  test@example.com  ", "password123")

        assert token in self.service._sessions
        # Verify the email was stripped before lookup
        self.mock_user_repo.get_by_email.assert_called_once_with("test@example.com")


class TestAuthServiceLoginExternal:
    """Test login_external() method for OAuth/external auth"""

    def setup_method(self):
        self.mock_user_repo = Mock(spec=UserRepo)
        self.service = AuthService(self.mock_user_repo)

    def test_login_external_success(self):
        """Test external login for existing user"""
        user = User(id=42, username="oauth_user")
        self.mock_user_repo.get_by_id.return_value = user

        token = self.service.login_external(42)

        assert isinstance(token, str)
        assert len(token) > 0
        assert token in self.service._sessions
        assert self.service._sessions[token].user_id == 42
        self.mock_user_repo.get_by_id.assert_called_once_with(42)

    def test_login_external_user_not_found(self):
        """Test external login for non-existent user"""
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.login_external(999)
        assert "user not found" in str(exc_info.value)

    def test_login_external_creates_unique_tokens(self):
        """Test that multiple external logins create unique tokens"""
        user = User(id=42, username="oauth_user")
        self.mock_user_repo.get_by_id.return_value = user

        token1 = self.service.login_external(42)
        token2 = self.service.login_external(42)

        assert token1 != token2
        assert token1 in self.service._sessions
        assert token2 in self.service._sessions

    def test_login_external_session_has_correct_user_id(self):
        """Test that external login session contains correct user_id"""
        user = User(id=99, username="oauth_user")
        self.mock_user_repo.get_by_id.return_value = user

        token = self.service.login_external(99)

        session = self.service._sessions[token]
        assert session.user_id == 99
        assert session.created_at > 0
        assert session.last_seen > 0