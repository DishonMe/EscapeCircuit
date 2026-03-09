import secrets
import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.UserRepo import UserRepo


@dataclass(frozen=True)
class SessionInfo:
    user_id: int
    created_at: float
    last_seen: float


class AuthService:
    """
    In-memory session tokens (NOT stored in DB).
    - login() returns a session token
    - require_user_id(token) validates token, updates last_seen, returns user_id
    """

    def __init__(self, user_repo: UserRepo, session_ttl_seconds: int = 24 * 60 * 60):
        self.user_repo = user_repo
        self.session_ttl_seconds = session_ttl_seconds

        self._lock = threading.Lock()
        self._sessions: Dict[str, SessionInfo] = {}

    def _is_expired(self, now: float, s: SessionInfo) -> bool:
        # Expire at TTL boundary as well (>=)
        return (now - s.last_seen) >= self.session_ttl_seconds

    def _cleanup_expired_locked(self) -> None:
        now = time.time()
        expired = [t for t, s in self._sessions.items() if now - s.last_seen > self.session_ttl_seconds]
        for t in expired:
            del self._sessions[t]

    def login(self, username: str, password: str):
        """Authenticate and return (token, user).  The caller gets the User
        object for free, avoiding a second DB lookup."""
        username = (username or "").strip()
        password = password or ""
        if not username or not password:
            raise ValidationError("Username and password are required for login.")

        user = self.user_repo.get_by_username(username)
        if not user:
            raise ValidationError("user not found")

        # Verify password
        row = self.user_repo.conn.execute("SELECT pw_salt, pw_hash FROM users WHERE id=?", (user.id,)).fetchone()
        if not row or row["pw_salt"] is None or row["pw_hash"] is None:
            raise ValidationError("invalid password")
        got = UserRepo._hash_password(password, row["pw_salt"])
        if got != row["pw_hash"]:
            raise ValidationError("invalid password")

        token = secrets.token_urlsafe(32)
        now = time.time()
        with self._lock:
            self._cleanup_expired_locked()
            self._sessions[token] = SessionInfo(user_id=user.id, created_at=now, last_seen=now)

        return token, user

    def login_external(self, user_id: int) -> str:
        """Create a session for a user verified by an external provider (e.g. Google).
        Skips password verification – caller is responsible for identity validation."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")

        token = secrets.token_urlsafe(32)
        now = time.time()
        with self._lock:
            self._cleanup_expired_locked()
            self._sessions[token] = SessionInfo(user_id=user.id, created_at=now, last_seen=now)
        return token

    def logout(self, token: str) -> None:
        token = (token or "").strip()
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def require_user_id(self, token: str) -> int:
        token = (token or "").strip()
        if not token:
            raise ValidationError("unauthorized")

        now = time.time()
        with self._lock:
            # Optional cleanup
            self._cleanup_expired_locked()

            s = self._sessions.get(token)
            if not s:
                raise ValidationError("unauthorized")

            # If expired, remove and raise *unauthorized* (matches your test)
            if self._is_expired(now, s):
                self._sessions.pop(token, None)
                raise ValidationError("unauthorized")

            # sliding expiration: refresh last_seen
            self._sessions[token] = SessionInfo(user_id=s.user_id, created_at=s.created_at, last_seen=now)

        # verify user still exists (outside lock)
        if not self.user_repo.get_by_id(s.user_id):
            # if user deleted, invalidate session too
            with self._lock:
                self._sessions.pop(token, None)
            raise ValidationError("unauthorized")

        return s.user_id
