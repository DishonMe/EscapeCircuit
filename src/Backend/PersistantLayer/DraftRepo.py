import sqlite3
import time

from Backend import settings
from typing import Optional

from Backend.PersistantLayer._db import transaction


class DraftRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS puzzle_drafts (
            user_id INTEGER NOT NULL,
            puzzle_id INTEGER NOT NULL,
            state_json TEXT NOT NULL,
            updated_at REAL NOT NULL,
            PRIMARY KEY (user_id, puzzle_id)
        );
        """)
        self.conn.commit()

    def upsert(self, user_id: int, puzzle_id: int, state_json: str,
               expected_updated_at: Optional[float] = None) -> dict:
        """Upsert a draft. If expected_updated_at is provided and doesn't match,
        raises ValueError (optimistic concurrency conflict).
        Returns {"updated_at": <new_timestamp>}."""
        now = time.time()

        with transaction(self.conn):
            if expected_updated_at is not None:
                # Optimistic concurrency: only update if timestamp matches
                cur = self.conn.execute("""
                    UPDATE puzzle_drafts SET state_json = ?, updated_at = ?
                    WHERE user_id = ? AND puzzle_id = ? AND abs(updated_at - ?) < ?
                """, (state_json, now, user_id, puzzle_id, expected_updated_at,
                      settings.DRAFT_TIMESTAMP_TOLERANCE_S))
                if cur.rowcount == 0:
                    # Either row doesn't exist (first save) or timestamp mismatch
                    existing = self.conn.execute(
                        "SELECT updated_at FROM puzzle_drafts WHERE user_id=? AND puzzle_id=?",
                        (user_id, puzzle_id),
                    ).fetchone()
                    if existing:
                        # Conflict: someone else (or another tab) saved since we loaded
                        raise ValueError("conflict")
                    # Row doesn't exist — fall through to INSERT
                    self.conn.execute("""
                        INSERT INTO puzzle_drafts (user_id, puzzle_id, state_json, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, puzzle_id, state_json, now))
            else:
                # No version check — blind upsert (backwards compatible)
                self.conn.execute("""
                    INSERT INTO puzzle_drafts (user_id, puzzle_id, state_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, puzzle_id) DO UPDATE SET
                        state_json = excluded.state_json,
                        updated_at = excluded.updated_at
                """, (user_id, puzzle_id, state_json, now))

        return {"updated_at": now}

    def get(self, user_id: int, puzzle_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT state_json, updated_at FROM puzzle_drafts WHERE user_id=? AND puzzle_id=?",
            (user_id, puzzle_id),
        ).fetchone()
        if not row:
            return None
        return {"state_json": row["state_json"], "updated_at": row["updated_at"]}

    def delete(self, user_id: int, puzzle_id: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM puzzle_drafts WHERE user_id=? AND puzzle_id=?",
            (user_id, puzzle_id),
        )
        self.conn.commit()
        return cur.rowcount > 0
