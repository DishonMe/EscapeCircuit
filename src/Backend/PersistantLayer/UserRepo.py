import os
import sqlite3
import hashlib
from typing import Optional, List

from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole
from Backend.DomainLayer.Exceptions import ValidationError


class UserRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL,
            bio TEXT NOT NULL DEFAULT '',
            xp INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            pw_salt BLOB,
            pw_hash BLOB,
            puzzle_limit_published INTEGER DEFAULT NULL,
            puzzle_limit_unpublished INTEGER DEFAULT NULL
        );
        """)
        # Migration: add columns to existing databases that pre-date these fields
        for col in ("puzzle_limit_published", "puzzle_limit_unpublished"):
            try:
                self.conn.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT NULL")
            except Exception:
                pass  # Column already exists

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)

    def create(self, user: User, password: Optional[str] = None) -> User:
        salt = None
        pw_hash = None
        if password is not None:
            salt = os.urandom(16)
            pw_hash = self._hash_password(password, salt)

        cur = self.conn.execute(
            "INSERT INTO users(username, email, role, bio, xp, created_at, pw_salt, pw_hash) VALUES(?,?,?,?,?,?,?,?)",
            (user.username, user.email, user.role.value, user.bio, user.xp, user.created_at.isoformat(), salt, pw_hash),
        )
        new_id = int(cur.lastrowid)
        return User(id=new_id, username=user.username, email=user.email, role=user.role, bio=user.bio, xp=user.xp, created_at=user.created_at)

    def get_by_id(self, user_id: int) -> Optional[User]:
        row = self.conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return User.from_dict({
            "id": int(row["id"]),
            "username": row["username"],
            "email": row["email"],
            "role": row["role"],
            "bio": row["bio"],
            "xp": int(row["xp"]),
            "created_at": row["created_at"],
            "puzzle_limit_published": row["puzzle_limit_published"],
            "puzzle_limit_unpublished": row["puzzle_limit_unpublished"],
        }) if row else None

    def get_by_username(self, username: str) -> Optional[User]:
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return User.from_dict({
            "id": int(row["id"]),
            "username": row["username"],
            "email": row["email"],
            "role": row["role"],
            "bio": row["bio"],
            "xp": int(row["xp"]),
            "created_at": row["created_at"],
            "puzzle_limit_published": row["puzzle_limit_published"],
            "puzzle_limit_unpublished": row["puzzle_limit_unpublished"],
        }) if row else None

    def verify_login(self, username: str, password: str) -> Optional[User]:
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not row or row["pw_salt"] is None or row["pw_hash"] is None:
            return None
        got = self._hash_password(password, row["pw_salt"])
        if got != row["pw_hash"]:
            return None
        return User.from_dict({
            "id": int(row["id"]),
            "username": row["username"],
            "email": row["email"],
            "role": row["role"],
            "bio": row["bio"],
            "xp": int(row["xp"]),
            "created_at": row["created_at"],
            "puzzle_limit_published": row["puzzle_limit_published"],
            "puzzle_limit_unpublished": row["puzzle_limit_unpublished"],
        })

    def update_xp(self, user_id: int, xp: int) -> None:
        if xp < 0:
            raise ValidationError("xp cannot be negative")
        self.conn.execute("UPDATE users SET xp=? WHERE id=?", (int(xp), int(user_id)))

    def update_role(self, user_id: int, role: UserRole) -> None:
        self.conn.execute("UPDATE users SET role=? WHERE id=?", (role.value, int(user_id)))

    def update_puzzle_limits(
        self, user_id: int,
        max_published: Optional[int],
        max_unpublished: Optional[int],
    ) -> None:
        """Set admin-configurable puzzle capacity overrides for a user.

        Pass ``None`` to reset a limit back to the level-based default.
        """
        self.conn.execute(
            "UPDATE users SET puzzle_limit_published=?, puzzle_limit_unpublished=? WHERE id=?",
            (
                int(max_published) if max_published is not None else None,
                int(max_unpublished) if max_unpublished is not None else None,
                int(user_id),
            ),
        )

    def list_all(self, limit: int = 200, offset: int = 0) -> List[User]:
        rows = self.conn.execute(
            "SELECT * FROM users ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return [
            User.from_dict({
                "id": int(r["id"]),
                "username": r["username"],
                "email": r["email"],
                "role": r["role"],
                "bio": r["bio"],
                "xp": int(r["xp"]),
                "created_at": r["created_at"],
                "puzzle_limit_published": r["puzzle_limit_published"],
                "puzzle_limit_unpublished": r["puzzle_limit_unpublished"],
            })
            for r in rows
        ]
