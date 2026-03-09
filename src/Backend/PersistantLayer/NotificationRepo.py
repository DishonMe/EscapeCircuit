import sqlite3
from typing import List, Optional
from datetime import datetime, timezone


class NotificationRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS creator_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            xp_amount INTEGER NOT NULL DEFAULT 0,
            puzzle_name TEXT NOT NULL DEFAULT '',
            actor_username TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0
        );
        """)
        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_notif_user_unread
        ON creator_notifications(user_id, is_read);
        """)

    def create(self, user_id: int, notif_type: str, message: str,
               xp_amount: int = 0, puzzle_name: str = "",
               actor_username: str = "", commit: bool = True) -> int:
        """Insert a notification and return its id."""
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            """INSERT INTO creator_notifications
               (user_id, type, message, xp_amount, puzzle_name, actor_username, created_at, is_read)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
            (int(user_id), notif_type, message, int(xp_amount),
             puzzle_name, actor_username, now),
        )
        if commit:
            self.conn.commit()
        return cur.lastrowid

    def get_unread(
        self, 
        user_id: int,
        notif_type: Optional[str] = None,
        puzzle_name: Optional[str] = None,
        actor_username: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[dict]:
        """Return unread notifications for a user with optional filters."""
        where_clauses = ["user_id = ?", "is_read = 0"]
        params = [int(user_id)]
        
        if notif_type is not None:
            where_clauses.append("type = ?")
            params.append(notif_type)
        
        if puzzle_name is not None:
            where_clauses.append("puzzle_name LIKE ?")
            params.append(f"%{puzzle_name}%")
        
        if actor_username is not None:
            where_clauses.append("actor_username LIKE ?")
            params.append(f"%{actor_username}%")
        
        if date_from is not None:
            where_clauses.append("created_at >= ?")
            params.append(date_from)
        
        if date_to is not None:
            where_clauses.append("created_at <= ?")
            params.append(date_to)
        
        # Build order by clause
        if order_by == "xp_amount":
            order_clause = f"xp_amount {order_direction}"
        else:
            order_clause = f"created_at {order_direction}"
        
        where_sql = " AND ".join(where_clauses)
        query = f"""SELECT id, type, message, xp_amount, puzzle_name,
                           actor_username, created_at
                    FROM creator_notifications
                    WHERE {where_sql}
                    ORDER BY {order_clause}"""
        
        if limit is not None:
            query += f" LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_all(
        self, 
        user_id: int,
        notif_type: Optional[str] = None,
        puzzle_name: Optional[str] = None,
        actor_username: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[dict]:
        """Return all notifications for a user (both read and unread) with optional filters."""
        where_clauses = ["user_id = ?"]
        params = [int(user_id)]
        
        if notif_type is not None:
            where_clauses.append("type = ?")
            params.append(notif_type)
        
        if puzzle_name is not None:
            where_clauses.append("puzzle_name LIKE ?")
            params.append(f"%{puzzle_name}%")
        
        if actor_username is not None:
            where_clauses.append("actor_username LIKE ?")
            params.append(f"%{actor_username}%")
        
        if date_from is not None:
            where_clauses.append("created_at >= ?")
            params.append(date_from)
        
        if date_to is not None:
            where_clauses.append("created_at <= ?")
            params.append(date_to)
        
        # Build order by clause
        if order_by == "xp_amount":
            order_clause = f"xp_amount {order_direction}"
        else:
            order_clause = f"created_at {order_direction}"
        
        where_sql = " AND ".join(where_clauses)
        query = f"""SELECT id, type, message, xp_amount, puzzle_name,
                           actor_username, created_at
                    FROM creator_notifications
                    WHERE {where_sql}
                    ORDER BY {order_clause}"""
        
        if limit is not None:
            query += f" LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    
    def count_notifications(
        self,
        user_id: int,
        notif_type: Optional[str] = None,
        puzzle_name: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        only_unread: bool = False
    ) -> int:
        """Count notifications with optional filters."""
        where_clauses = ["user_id = ?"]
        params = [int(user_id)]
        
        if only_unread:
            where_clauses.append("is_read = 0")
        
        if notif_type is not None:
            where_clauses.append("type = ?")
            params.append(notif_type)
        
        if puzzle_name is not None:
            where_clauses.append("puzzle_name LIKE ?")
            params.append(f"%{puzzle_name}%")
        
        if date_from is not None:
            where_clauses.append("created_at >= ?")
            params.append(date_from)
        
        if date_to is not None:
            where_clauses.append("created_at <= ?")
            params.append(date_to)
        
        where_sql = " AND ".join(where_clauses)
        cur = self.conn.execute(f"SELECT COUNT(*) FROM creator_notifications WHERE {where_sql}", params)
        row = cur.fetchone()
        return row[0] if row else 0

    def mark_all_read(self, user_id: int) -> int:
        """Mark all unread notifications as read. Return count updated."""
        cur = self.conn.execute(
            "UPDATE creator_notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
            (int(user_id),),
        )
        self.conn.commit()
        return cur.rowcount
