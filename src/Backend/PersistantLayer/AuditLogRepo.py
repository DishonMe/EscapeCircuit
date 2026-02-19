import json
import sqlite3
from typing import List, Optional
from datetime import datetime, timezone


class AuditLogRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            target_user_id INTEGER,
            target_puzzle_id INTEGER,
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        """)
        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_admin
        ON admin_audit_log(admin_user_id);
        """)
        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_created
        ON admin_audit_log(created_at);
        """)

    def create(
        self,
        admin_user_id: int,
        action_type: str,
        target_user_id: Optional[int] = None,
        target_puzzle_id: Optional[int] = None,
        details: Optional[dict] = None,
    ) -> int:
        """Insert an audit log entry and return its id."""
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            """INSERT INTO admin_audit_log
               (admin_user_id, action_type, target_user_id, target_puzzle_id, details_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                int(admin_user_id),
                action_type,
                int(target_user_id) if target_user_id else None,
                int(target_puzzle_id) if target_puzzle_id else None,
                json.dumps(details or {}),
                now,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        action_type: Optional[str] = None,
        admin_user_id: Optional[int] = None,
    ) -> List[dict]:
        """List audit log entries with optional filters."""
        where_clauses = []
        params = []
        if action_type:
            where_clauses.append("action_type = ?")
            params.append(action_type)
        if admin_user_id:
            where_clauses.append("admin_user_id = ?")
            params.append(int(admin_user_id))

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f"""SELECT * FROM admin_audit_log {where_sql}
                    ORDER BY created_at DESC LIMIT ? OFFSET ?"""
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        return [
            {
                "id": row["id"],
                "admin_user_id": row["admin_user_id"],
                "action_type": row["action_type"],
                "target_user_id": row["target_user_id"],
                "target_puzzle_id": row["target_puzzle_id"],
                "details": json.loads(row["details_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
