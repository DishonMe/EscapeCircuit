import os
import sqlite3
import hashlib
from typing import Optional, List, Dict

from Backend import settings
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
            pw_hash BLOB
            puzzle_limit_published INTEGER DEFAULT NULL,
            puzzle_limit_unpublished INTEGER DEFAULT NULL
        );
        """)
        # Migration: add columns to existing databases that pre-date these fields
        cols = [row[1] for row in self.conn.execute("PRAGMA table_info(users)").fetchall()]
        if "is_discussion_banned" not in cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN is_discussion_banned INTEGER NOT NULL DEFAULT 0")
        for col in ("puzzle_limit_published", "puzzle_limit_unpublished"):
            if col not in cols:
                self.conn.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT NULL")

    @staticmethod
    def _row_to_user(row) -> User:
        keys = row.keys() if hasattr(row, "keys") else []
        return User.from_dict({
            "id": int(row["id"]),
            "username": row["username"],
            "email": row["email"],
            "role": row["role"],
            "bio": row["bio"],
            "xp": int(row["xp"]),
            "is_discussion_banned": bool(row["is_discussion_banned"]) if "is_discussion_banned" in keys else False,
            "created_at": row["created_at"],
            "puzzle_limit_published": row["puzzle_limit_published"] if "puzzle_limit_published" in keys else None,
            "puzzle_limit_unpublished": row["puzzle_limit_unpublished"] if "puzzle_limit_unpublished" in keys else None,
        })

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
        self.conn.commit()
        new_id = int(cur.lastrowid)
        return User(id=new_id, username=user.username, email=user.email, role=user.role, bio=user.bio, xp=user.xp, created_at=user.created_at)

    def get_by_id(self, user_id: int) -> Optional[User]:
        row = self.conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return self._row_to_user(row) if row else None

    def get_by_username(self, username: str) -> Optional[User]:
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return self._row_to_user(row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        row = self.conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return self._row_to_user(row) if row else None

    def get_by_ids(self, user_ids: List[int]) -> Dict[int, User]:
        """Fetch multiple users by ID in one query. Returns {id: User} dict."""
        if not user_ids:
            return {}
        unique_ids = list(set(int(uid) for uid in user_ids))
        result: Dict[int, User] = {}
        for i in range(0, len(unique_ids), 900):
            chunk = unique_ids[i:i + 900]
            placeholders = ",".join("?" for _ in chunk)
            rows = self.conn.execute(
                f"SELECT * FROM users WHERE id IN ({placeholders})", chunk
            ).fetchall()
            for row in rows:
                user = self._row_to_user(row)
                result[user.id] = user
        return result

    def verify_login(self, username: str, password: str) -> Optional[User]:
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not row or row["pw_salt"] is None or row["pw_hash"] is None:
            return None
        got = self._hash_password(password, row["pw_salt"])
        if got != row["pw_hash"]:
            return None
        return self._row_to_user(row)

    def update_xp(self, user_id: int, xp: int) -> None:
        if xp < 0:
            raise ValidationError("xp cannot be negative")
        self.conn.execute("UPDATE users SET xp=? WHERE id=?", (int(xp), int(user_id)))

    def increment_xp(self, user_id: int, delta: int) -> None:
        """Atomically increment user XP by delta. Uses SQL arithmetic to avoid read-modify-write races."""
        if delta <= 0:
            return
        self.conn.execute(
            "UPDATE users SET xp = xp + ? WHERE id = ?",
            (int(delta), int(user_id)),
        )

    def delete(self, user_id: int) -> bool:
        """Delete a user by ID. Returns True if a row was actually deleted."""
        cur = self.conn.execute("DELETE FROM users WHERE id=?", (int(user_id),))
        return cur.rowcount > 0

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

    def update_role_if(self, user_id: int, new_role: UserRole, expected_role: UserRole) -> bool:
        """Atomically update role only if current role matches expected_role.
        Returns True if the update happened (exactly one row changed)."""
        cur = self.conn.execute(
            "UPDATE users SET role=? WHERE id=? AND role=?",
            (new_role.value, int(user_id), expected_role.value),
        )
        return cur.rowcount > 0

    @staticmethod
    def _min_xp_for_level(level: int) -> int:
        lvl = max(1, int(level))
        return ((lvl - 1) ** 2) * settings.LEVEL_XP_DIVISOR

    @staticmethod
    def _build_where(
        username_search: Optional[str] = None,
        role: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_xp: Optional[int] = None,
        max_xp: Optional[int] = None,
        experience_level: str = "all",
    ) -> tuple:
        """Build WHERE clause and params shared by list_all() and count_all()."""
        where_clauses: list = []
        params: list = []
        experienced_xp_min = UserRepo._min_xp_for_level(settings.EXPERIENCED_LEVEL_MIN)
        if username_search is not None:
            where_clauses.append("username LIKE ?")
            params.append(f"%{username_search}%")
        if role is not None:
            where_clauses.append("role=?")
            params.append(role)
        if date_from is not None:
            where_clauses.append("created_at>=?")
            params.append(date_from)
        if date_to is not None:
            where_clauses.append("created_at<=?")
            params.append(date_to)
        if min_xp is not None:
            where_clauses.append("xp>=?")
            params.append(min_xp)
        if max_xp is not None:
            where_clauses.append("xp<=?")
            params.append(max_xp)
        if experience_level == "experienced":
            where_clauses.append("xp>=?")
            params.append(experienced_xp_min)
        elif experience_level == "inexperienced":
            where_clauses.append("xp<?")
            params.append(experienced_xp_min)
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        return where_sql, params

    def list_all(
        self,
        limit: int = 200,
        offset: int = 0,
        username_search: Optional[str] = None,
        role: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_xp: Optional[int] = None,
        max_xp: Optional[int] = None,
        experience_level: str = "all",
        order_by: str = "created_at",
        order_direction: str = "DESC"
    ) -> List[User]:
        where_sql, params = self._build_where(
            username_search=username_search, role=role, date_from=date_from,
            date_to=date_to, min_xp=min_xp, max_xp=max_xp,
            experience_level=experience_level,
        )

        valid_order_fields = ["created_at", "level", "role", "xp", "id", "experienced"]
        if order_by not in valid_order_fields:
            order_by = "created_at"

        if order_by == "level":
            order_clause = f"xp {order_direction}"
        elif order_by == "role":
            order_clause = f"role {order_direction}"
        elif order_by == "xp":
            order_clause = f"xp {order_direction}"
        elif order_by == "id":
            order_clause = f"id {order_direction}"
        elif order_by == "experienced":
            # DESC => experienced users first, ASC => inexperienced users first.
            # Secondary sort by XP keeps ordering stable within each group.
            experienced_xp_min = self._min_xp_for_level(settings.EXPERIENCED_LEVEL_MIN)
            order_clause = f"CASE WHEN xp >= {experienced_xp_min} THEN 1 ELSE 0 END {order_direction}, xp {order_direction}"
        else:
            order_clause = f"created_at {order_direction}"

        query = f"SELECT * FROM users {where_sql} ORDER BY {order_clause} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_user(r) for r in rows]

    def count_all(
        self,
        username_search: Optional[str] = None,
        role: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_xp: Optional[int] = None,
        max_xp: Optional[int] = None,
        experience_level: str = "all",
    ) -> int:
        where_sql, params = self._build_where(
            username_search=username_search, role=role, date_from=date_from,
            date_to=date_to, min_xp=min_xp, max_xp=max_xp,
            experience_level=experience_level,
        )
        row = self.conn.execute(f"SELECT COUNT(*) FROM users {where_sql}", params).fetchone()
        return row[0] if row else 0

    def ban_from_discussions(self, user_id: int) -> None:
        self.conn.execute("UPDATE users SET is_discussion_banned=1 WHERE id=?", (int(user_id),))
        self.conn.commit()

    def unban_from_discussions(self, user_id: int) -> None:
        self.conn.execute("UPDATE users SET is_discussion_banned=0 WHERE id=?", (int(user_id),))
        self.conn.commit()
