import sqlite3
from typing import Optional, List, Dict

from Backend.DomainLayer.Utils import utcnow


class ReportRepo:
    """Handles content reports for discussions and replies."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS content_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL REFERENCES users(id),
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            UNIQUE(reporter_id, target_type, target_id)
        );
        """)

    def create(self, reporter_id: int, target_type: str, target_id: int, reason: str, details: str = "") -> Dict:
        now = utcnow().isoformat()
        cur = self.conn.execute("""
            INSERT INTO content_reports(reporter_id, target_type, target_id, reason, details, status, created_at)
            VALUES(?,?,?,?,?,?,?)
        """, (int(reporter_id), target_type, int(target_id), reason, details, "pending", now))
        self.conn.commit()
        return {
            "id": cur.lastrowid,
            "reporter_id": reporter_id,
            "target_type": target_type,
            "target_id": target_id,
            "reason": reason,
            "details": details,
            "status": "pending",
            "created_at": now,
        }

    def get_by_id(self, report_id: int) -> Optional[Dict]:
        row = self.conn.execute(
            "SELECT * FROM content_reports WHERE id=?", (int(report_id),)
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_all(self, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        where_clauses = []
        params: list = []
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        params.extend([limit, offset])
        rows = self.conn.execute(
            f"SELECT * FROM content_reports {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def count(self, status: Optional[str] = None) -> int:
        if status:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM content_reports WHERE status=?", (status,)
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) FROM content_reports").fetchone()
        return row[0] if row else 0

    def update_status(self, report_id: int, status: str) -> Optional[Dict]:
        self.conn.execute(
            "UPDATE content_reports SET status=? WHERE id=?",
            (status, int(report_id)),
        )
        self.conn.commit()
        return self.get_by_id(report_id)

    def has_reported(self, reporter_id: int, target_type: str, target_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM content_reports WHERE reporter_id=? AND target_type=? AND target_id=?",
            (int(reporter_id), target_type, int(target_id)),
        ).fetchone()
        return row is not None

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict:
        return {
            "id": int(row["id"]),
            "reporter_id": int(row["reporter_id"]),
            "target_type": row["target_type"],
            "target_id": int(row["target_id"]),
            "reason": row["reason"],
            "details": row["details"],
            "status": row["status"],
            "created_at": row["created_at"],
        }
