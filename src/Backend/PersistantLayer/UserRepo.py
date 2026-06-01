import os
import sqlite3
import hashlib
from typing import Optional, List, Dict

from Backend import settings
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Utils import utcnow


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
            avatar_name TEXT NOT NULL DEFAULT 'Dinosaur',
            avatar_color TEXT NOT NULL DEFAULT '#38bdf8',
            tutorials_completed TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            pw_salt BLOB,
            pw_hash BLOB
        );
        """)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                username_or_email TEXT,
                success INTEGER NOT NULL,
                reason TEXT,
                user_id INTEGER,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_attempts_created_at
            ON auth_attempts(created_at DESC);
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_attempts_action
            ON auth_attempts(action);
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_attempts_success
            ON auth_attempts(success);
            """
        )
        # Migration: add is_discussion_banned column if missing
        cols = [row[1] for row in self.conn.execute("PRAGMA table_info(users)").fetchall()]
        if "is_discussion_banned" not in cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN is_discussion_banned INTEGER NOT NULL DEFAULT 0")
        # Migration: add puzzle capacity override columns if missing
        if "max_published_puzzles" not in cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN max_published_puzzles INTEGER")
        if "max_unpublished_puzzles" not in cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN max_unpublished_puzzles INTEGER")
        # Migration: add avatar_name column if missing
        if "avatar_name" not in cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN avatar_name TEXT NOT NULL DEFAULT 'Dinosaur'")
        # Migration: add avatar_color column if missing
        if "avatar_color" not in cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN avatar_color TEXT NOT NULL DEFAULT '#38bdf8'")
        # Migration: add tutorials_completed column if missing
        if "tutorials_completed" not in cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN tutorials_completed TEXT NOT NULL DEFAULT ''")
            # If old tutorial_completed column exists with some true values, migrate them
            if "tutorial_completed" in cols:
                # For users who completed the old single tutorial, mark browse-puzzles as completed
                self.conn.execute(
                    "UPDATE users SET tutorials_completed = 'browse-puzzles' WHERE tutorial_completed = 1"
                )
            self.conn.commit()

    @staticmethod
    def _row_to_user(row) -> User:
        # Backward compatibility: check new tutorials_completed column, fallback to old tutorial_completed
        tutorials_completed = ""
        if "tutorials_completed" in row.keys():
            # Use the value as-is (could be None or empty string from DB, both treated as empty)
            tutorials_completed = row["tutorials_completed"] or ""
        elif "tutorial_completed" in row.keys() and row["tutorial_completed"]:
            # Migrate old single-tutorial flag to new format
            tutorials_completed = "browse-puzzles"
        
        return User.from_dict({
            "id": int(row["id"]),
            "username": row["username"],
            "email": row["email"],
            "role": row["role"],
            "bio": row["bio"],
            "xp": int(row["xp"]),
            "avatar_name": row["avatar_name"] if "avatar_name" in row.keys() else "Dinosaur",
            "avatar_color": row["avatar_color"] if "avatar_color" in row.keys() else "#38bdf8",
            "is_discussion_banned": bool(row["is_discussion_banned"]) if "is_discussion_banned" in row.keys() else False,
            "tutorials_completed": tutorials_completed,
            "created_at": row["created_at"],
            "max_published_puzzles": row["max_published_puzzles"] if "max_published_puzzles" in row.keys() else None,
            "max_unpublished_puzzles": row["max_unpublished_puzzles"] if "max_unpublished_puzzles" in row.keys() else None,
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
            "INSERT INTO users(username, email, role, bio, xp, avatar_name, avatar_color, created_at, pw_salt, pw_hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (user.username, user.email, user.role.value, user.bio, user.xp, user.avatar_name, user.avatar_color, user.created_at.isoformat(), salt, pw_hash),
        )
        self.conn.commit()
        new_id = int(cur.lastrowid)
        return User(id=new_id, username=user.username, email=user.email, role=user.role, bio=user.bio, xp=user.xp, avatar_name=user.avatar_name, avatar_color=user.avatar_color, created_at=user.created_at)

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

    def complete_tutorial(self, user_id: int, tutorial_name: str) -> None:
        """Mark a specific tutorial as completed for a user.
        
        Args:
            user_id: The ID of the user
            tutorial_name: The name of the tutorial (e.g., 'browse-puzzles', 'arsenal')
        """
        try:
            # Get current tutorials_completed list
            row = self.conn.execute(
                "SELECT tutorials_completed FROM users WHERE id = ?",
                (int(user_id),)
            ).fetchone()
            
            if not row:
                print(f"DEBUG: User {user_id} not found in complete_tutorial")
                return
            
            current = row["tutorials_completed"] or ""
            print(f"DEBUG: complete_tutorial - user_id={user_id}, tutorial_name={tutorial_name}, current='{current}'")
            
            # Parse the comma-separated list
            completed_list = [t.strip() for t in current.split(",") if t.strip()]
            
            # Add tutorial if not already completed
            if tutorial_name not in completed_list:
                completed_list.append(tutorial_name)
                new_completed = ",".join(completed_list)
                print(f"DEBUG: Updating tutorials_completed to '{new_completed}'")
                self.conn.execute(
                    "UPDATE users SET tutorials_completed=? WHERE id=?",
                    (new_completed, int(user_id))
                )
            else:
                print(f"DEBUG: Tutorial {tutorial_name} already in completed_list: {completed_list}")
        except Exception as e:
            print(f"ERROR in complete_tutorial: {e}")
            import traceback
            traceback.print_exc()
            raise

    def has_completed_tutorial(self, user_id: int, tutorial_name: str) -> bool:
        """Check if a user has completed a specific tutorial.
        
        Args:
            user_id: The ID of the user
            tutorial_name: The name of the tutorial to check
            
        Returns:
            True if the tutorial has been completed, False otherwise
        """
        try:
            row = self.conn.execute(
                "SELECT tutorials_completed FROM users WHERE id = ?",
                (int(user_id),)
            ).fetchone()
            
            if not row:
                print(f"DEBUG: User {user_id} not found in has_completed_tutorial")
                return False
            
            completed = row["tutorials_completed"]
            print(f"DEBUG: has_completed_tutorial - user_id={user_id}, tutorial_name={tutorial_name}, completed='{completed}'")
            
            if not completed:
                print(f"DEBUG: tutorials_completed is empty, returning False")
                return False
            
            completed_list = [t.strip() for t in completed.split(",") if t.strip()]
            result = tutorial_name in completed_list
            print(f"DEBUG: completed_list={completed_list}, result={result}")
            return result
        except Exception as e:
            print(f"ERROR in has_completed_tutorial: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_remaining_tutorials(self, user_id: int) -> list[str]:
        """Get list of tutorials NOT yet completed by the user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of tutorial names that haven't been completed
        """
        all_tutorials = ["browse-puzzles", "solving-page", "arsenal", "my-puzzles", "arsenal-creator"]
        try:
            row = self.conn.execute(
                "SELECT tutorials_completed FROM users WHERE id = ?",
                (int(user_id),)
            ).fetchone()
            
            if not row:
                print(f"DEBUG: User {user_id} not found in get_remaining_tutorials")
                return all_tutorials
            
            completed = row["tutorials_completed"]
            print(f"DEBUG: get_remaining_tutorials - user_id={user_id}, completed='{completed}'")
            
            if not completed:
                print(f"DEBUG: tutorials_completed is empty, returning all tutorials")
                return all_tutorials
            
            completed_list = [t.strip() for t in completed.split(",") if t.strip()]
            remaining = [t for t in all_tutorials if t not in completed_list]
            print(f"DEBUG: completed_list={completed_list}, remaining={remaining}")
            return remaining
        except Exception as e:
            print(f"ERROR in get_remaining_tutorials: {e}")
            import traceback
            traceback.print_exc()
            return all_tutorials

    def delete(self, user_id: int) -> bool:
        """Delete a user by ID. Returns True if a row was actually deleted."""
        cur = self.conn.execute("DELETE FROM users WHERE id=?", (int(user_id),))
        return cur.rowcount > 0

    def update_role(self, user_id: int, role: UserRole) -> None:
        self.conn.execute("UPDATE users SET role=? WHERE id=?", (role.value, int(user_id)))

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

    def update_puzzle_limits(
        self,
        user_id: int,
        max_published: Optional[int],
        max_unpublished: Optional[int],
    ) -> None:
        """Set per-creator puzzle capacity overrides.  Pass None to revert to the
        level-based default for that field."""
        self.conn.execute(
            "UPDATE users SET max_published_puzzles=?, max_unpublished_puzzles=? WHERE id=?",
            (max_published, max_unpublished, int(user_id)),
        )
        self.conn.commit()

    def create_auth_attempt(
        self,
        action: str,
        username_or_email: Optional[str],
        success: bool,
        reason: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO auth_attempts(
                action,
                username_or_email,
                success,
                reason,
                user_id,
                created_at
            )
            VALUES(?,?,?,?,?,?)
            """,
            (
                str(action or "").strip() or "unknown",
                (username_or_email or "").strip() or None,
                1 if success else 0,
                (reason or "").strip() or None,
                int(user_id) if user_id is not None else None,
                utcnow().isoformat(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_auth_attempts(
        self,
        limit: int = 100,
        offset: int = 0,
        action: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> List[dict]:
        where = []
        params = []

        if action:
            where.append("action = ?")
            params.append(action)
        if success is not None:
            where.append("success = ?")
            params.append(1 if success else 0)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        rows = self.conn.execute(
            f"""
            SELECT *
            FROM auth_attempts
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, int(limit), int(offset)],
        ).fetchall()

        return [
            {
                "id": int(row["id"]),
                "action": row["action"],
                "username_or_email": row["username_or_email"],
                "success": bool(int(row["success"])),
                "reason": row["reason"],
                "user_id": int(row["user_id"]) if row["user_id"] is not None else None,
                "created_at": row["created_at"],
            }
            for row in rows
        ]
