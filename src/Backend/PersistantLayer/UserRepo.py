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
            pw_hash BLOB
        );
        """)

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
        return User.from_dict({
            "id": int(row["id"]),
            "username": row["username"],
            "email": row["email"],
            "role": row["role"],
            "bio": row["bio"],
            "xp": int(row["xp"]),
            "created_at": row["created_at"],
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
        }) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        row = self.conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return User.from_dict({
            "id": int(row["id"]),
            "username": row["username"],
            "email": row["email"],
            "role": row["role"],
            "bio": row["bio"],
            "xp": int(row["xp"]),
            "created_at": row["created_at"],
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
        })

    def update_xp(self, user_id: int, xp: int) -> None:
        if xp < 0:
            raise ValidationError("xp cannot be negative")
        self.conn.execute("UPDATE users SET xp=? WHERE id=?", (int(xp), int(user_id)))

    def update_role(self, user_id: int, role: UserRole) -> None:
        self.conn.execute("UPDATE users SET role=? WHERE id=?", (role.value, int(user_id)))

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
        """
        List all users with optional filters and ordering.
        
        Args:
            username_search: Partial username search
            experience_level: 'all' (default), 'experienced' (level >= 5 / xp >= 1600), 'inexperienced' (level < 5 / xp < 1600)
            order_by: 'created_at' (default), 'level' (via xp), or 'role'
            order_direction: 'DESC' (default) or 'ASC'
        """
        where_clauses = []
        params = []
        
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
        
        # Experience level filtering: experienced = level >= 5 (xp >= 1600), inexperienced = level < 5 (xp < 1600)
        if experience_level == "experienced":
            where_clauses.append("xp>=?")
            params.append(1600)
        elif experience_level == "inexperienced":
            where_clauses.append("xp<?")
            params.append(1600)
        # 'all' requires no additional filter
        
        # Build order by clause
        valid_order_fields = ["created_at", "level", "role", "xp"]
        if order_by not in valid_order_fields:
            order_by = "created_at"
        
        if order_by == "level":
            # Level is calculated from XP, so we order by xp
            order_clause = f"xp {order_direction}"
        elif order_by == "role":
            order_clause = f"role {order_direction}"
        elif order_by == "xp":
            order_clause = f"xp {order_direction}"
        else:
            order_clause = f"created_at {order_direction}"
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        query = f"SELECT * FROM users {where_sql} ORDER BY {order_clause} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = self.conn.execute(query, params).fetchall()
        return [
            User.from_dict({
                "id": int(r["id"]),
                "username": r["username"],
                "email": r["email"],
                "role": r["role"],
                "bio": r["bio"],
                "xp": int(r["xp"]),
                "created_at": r["created_at"],
            })
            for r in rows
        ]
    
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
        """Count all users with optional filters."""
        where_clauses = []
        params = []
        
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
        
        # Experience level filtering: experienced = level >= 5 (xp >= 1600), inexperienced = level < 5 (xp < 1600)
        if experience_level == "experienced":
            where_clauses.append("xp>=?")
            params.append(1600)
        elif experience_level == "inexperienced":
            where_clauses.append("xp<?")
            params.append(1600)
        # 'all' requires no additional filter
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        cur = self.conn.execute(f"SELECT COUNT(*) FROM users {where_sql}", params)
        row = cur.fetchone()
        return row[0] if row else 0
