import sqlite3
from typing import Optional

from Backend.DomainLayer.Utils import utcnow


class CluesExhausted(Exception):
    """Raised by record_next_clue when all configured clues for a puzzle have been consumed."""


class CluesRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clue_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                puzzle_id INTEGER NOT NULL,
                clue_index INTEGER NOT NULL,
                penalty_seconds INTEGER NOT NULL,
                request_id TEXT,
                requested_at TEXT NOT NULL,
                UNIQUE(attempt_id, clue_index)
            );
            """
        )
        # Partial unique index for client-supplied idempotency keys.
        self.conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_clue_requests_request_id
                ON clue_requests(attempt_id, request_id)
                WHERE request_id IS NOT NULL;
            """
        )

    # --- reads ---
    def count_for_attempt(self, attempt_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS c FROM clue_requests WHERE attempt_id=?",
            (int(attempt_id),),
        ).fetchone()
        return int(row["c"]) if row else 0

    def total_penalty_for_attempt(self, attempt_id: int) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(penalty_seconds), 0) AS t FROM clue_requests WHERE attempt_id=?",
            (int(attempt_id),),
        ).fetchone()
        return int(row["t"]) if row else 0

    def list_for_attempt(self, attempt_id: int) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT clue_index, penalty_seconds, request_id, requested_at
            FROM clue_requests
            WHERE attempt_id=?
            ORDER BY clue_index ASC
            """,
            (int(attempt_id),),
        ).fetchall()
        return [
            {
                "clue_index": int(r["clue_index"]),
                "penalty_seconds": int(r["penalty_seconds"]),
                "request_id": r["request_id"],
                "requested_at": r["requested_at"],
            }
            for r in rows
        ]

    def find_by_request_id(self, attempt_id: int, request_id: str) -> Optional[dict]:
        if not request_id:
            return None
        row = self.conn.execute(
            """
            SELECT clue_index, penalty_seconds, request_id, requested_at
            FROM clue_requests
            WHERE attempt_id=? AND request_id=?
            LIMIT 1
            """,
            (int(attempt_id), str(request_id)),
        ).fetchone()
        if not row:
            return None
        return {
            "clue_index": int(row["clue_index"]),
            "penalty_seconds": int(row["penalty_seconds"]),
            "request_id": row["request_id"],
            "requested_at": row["requested_at"],
        }

    # --- writes ---
    def record_next_clue(
        self,
        attempt_id: int,
        user_id: int,
        puzzle_id: int,
        penalty_seconds: int,
        total_clues: int,
        request_id: Optional[str] = None,
    ) -> dict:
        """Record the next clue for this attempt.

        Idempotency:
          - If request_id matches an existing row for this attempt, returns the existing
            row with replayed=True; no new clue is consumed.
          - Otherwise inserts a new row at the next available clue_index. On UNIQUE
            collision (concurrent reveal), retries by re-reading the count.
        Raises CluesExhausted if all clues for the puzzle have been used.
        """
        if request_id:
            existing = self.find_by_request_id(attempt_id, request_id)
            if existing is not None:
                return {
                    "clue_index": existing["clue_index"],
                    "penalty_seconds": existing["penalty_seconds"],
                    "replayed": True,
                }

        for _ in range(2):
            current = self.count_for_attempt(attempt_id)
            if current >= int(total_clues):
                raise CluesExhausted()
            try:
                self.conn.execute(
                    """
                    INSERT INTO clue_requests(attempt_id, user_id, puzzle_id, clue_index, penalty_seconds, request_id, requested_at)
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        int(attempt_id),
                        int(user_id),
                        int(puzzle_id),
                        int(current),
                        int(penalty_seconds),
                        request_id,
                        utcnow().isoformat(),
                    ),
                )
                return {
                    "clue_index": int(current),
                    "penalty_seconds": int(penalty_seconds),
                    "replayed": False,
                }
            except sqlite3.IntegrityError:
                # A concurrent reveal won the race for this clue_index, or a duplicate
                # request_id slipped past the earlier lookup. Re-check on next loop.
                if request_id:
                    existing = self.find_by_request_id(attempt_id, request_id)
                    if existing is not None:
                        return {
                            "clue_index": existing["clue_index"],
                            "penalty_seconds": existing["penalty_seconds"],
                            "replayed": True,
                        }
                continue
        raise CluesExhausted()

    def delete_for_puzzle(self, puzzle_id: int) -> None:
        self.conn.execute("DELETE FROM clue_requests WHERE puzzle_id=?", (int(puzzle_id),))
