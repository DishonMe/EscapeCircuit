import sqlite3
from typing import Optional, List

from Backend.DomainLayer.SolveAttempt import SolveAttempt


class SolveRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS solve_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            puzzle_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            circuit_id INTEGER,
            started_at TEXT NOT NULL,
            submitted_at TEXT,
            passed INTEGER,
            fail_reason TEXT
        );
        """)

    def create_attempt(self, attempt: SolveAttempt) -> SolveAttempt:
        cur = self.conn.execute("""
            INSERT INTO solve_attempts(puzzle_id, user_id, circuit_id, started_at, submitted_at, passed, fail_reason)
            VALUES(?,?,?,?,?,?,?)
        """, (
            attempt.puzzle_id,
            attempt.user_id,
            attempt.circuit_id,
            attempt.started_at.isoformat(),
            attempt.submitted_at.isoformat() if attempt.submitted_at else None,
            None if attempt.passed is None else (1 if attempt.passed else 0),
            attempt.fail_reason,
        ))
        attempt.id = int(cur.lastrowid)
        return attempt

    def update_attempt(self, attempt: SolveAttempt) -> None:
        self.conn.execute("""
            UPDATE solve_attempts SET
                circuit_id=?,
                submitted_at=?,
                passed=?,
                fail_reason=?
            WHERE id=?
        """, (
            attempt.circuit_id,
            attempt.submitted_at.isoformat() if attempt.submitted_at else None,
            None if attempt.passed is None else (1 if attempt.passed else 0),
            attempt.fail_reason,
            attempt.id,
        ))

    def get_open_attempt(self, user_id: int, puzzle_id: int) -> Optional[SolveAttempt]:
        row = self.conn.execute("""
            SELECT * FROM solve_attempts
            WHERE user_id=? AND puzzle_id=? AND submitted_at IS NULL
            ORDER BY id DESC LIMIT 1
        """, (user_id, puzzle_id)).fetchone()
        return SolveAttempt.from_dict({
            "id": int(row["id"]),
            "puzzle_id": int(row["puzzle_id"]),
            "user_id": int(row["user_id"]),
            "circuit_id": row["circuit_id"],
            "started_at": row["started_at"],
            "submitted_at": row["submitted_at"],
            "passed": None if row["passed"] is None else bool(int(row["passed"])),
            "fail_reason": row["fail_reason"],
        }) if row else None

    def has_passed(self, user_id: int, puzzle_id: int) -> bool:
        row = self.conn.execute("""
            SELECT 1 FROM solve_attempts
            WHERE user_id=? AND puzzle_id=? AND passed=1
            LIMIT 1
        """, (user_id, puzzle_id)).fetchone()
        return row is not None

    def has_passed_before_attempt(self, user_id: int, puzzle_id: int, attempt_id: int) -> bool:
        row = self.conn.execute("""
            SELECT 1 FROM solve_attempts
            WHERE user_id=? AND puzzle_id=? AND passed=1 AND id < ?
            LIMIT 1
        """, (user_id, puzzle_id, attempt_id)).fetchone()
        return row is not None

    def first_attempt_started_at(self, user_id: int, puzzle_id: int) -> Optional[str]:
        row = self.conn.execute("""
            SELECT started_at FROM solve_attempts
            WHERE user_id=? AND puzzle_id=?
            ORDER BY id ASC LIMIT 1
        """, (user_id, puzzle_id)).fetchone()
        return row["started_at"] if row else None
