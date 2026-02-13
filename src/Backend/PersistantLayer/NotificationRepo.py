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
               actor_username: str = "") -> int:
        """Insert a notification and return its id."""
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            """INSERT INTO creator_notifications
               (user_id, type, message, xp_amount, puzzle_name, actor_username, created_at, is_read)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
            (int(user_id), notif_type, message, int(xp_amount),
             puzzle_name, actor_username, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_unread(self, user_id: int) -> List[dict]:
        """Return all unread notifications for a user, newest first."""
        rows = self.conn.execute(
            """SELECT id, type, message, xp_amount, puzzle_name,
                      actor_username, created_at
               FROM creator_notifications
               WHERE user_id = ? AND is_read = 0
               ORDER BY created_at DESC""",
            (int(user_id),),
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_all_read(self, user_id: int) -> int:
        """Mark all unread notifications as read. Return count updated."""
        cur = self.conn.execute(
            "UPDATE creator_notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
            (int(user_id),),
        )
        self.conn.commit()
        return cur.rowcount
