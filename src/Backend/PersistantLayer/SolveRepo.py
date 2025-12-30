import sqlite3
from dataclasses import dataclass
from typing import Optional

from Backend.DomainLayer.SolveAttempt import SolveAttempt


@dataclass(frozen=True)
class PuzzleProgress:
    user_id: int
    puzzle_id: int
    best_medal: int  # 0=none, 1=bronze, 2=silver, 3=gold
    timer_upgraded: bool
    tight_upgraded: bool
    first_solved_at: Optional[str]


class SolveRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._ensure_schema()

    def _table_columns(self, table: str) -> set[str]:
        rows = self.conn.execute(f"PRAGMA table_info({table});").fetchall()
        return {r[1] for r in rows}

    def _add_column_if_missing(self, table: str, coldef: str) -> None:
        col = coldef.split()[0]
        if col not in self._table_columns(table):
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {coldef};")

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
            fail_reason TEXT,
            time_used_seconds INTEGER,
            cost_used INTEGER
        );
        """)

        # Add columns if DB already exists from an older version
        for coldef in [
            "time_used_seconds INTEGER",
            "cost_used INTEGER",
        ]:
            self._add_column_if_missing("solve_attempts", coldef)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS puzzle_progress (
            user_id INTEGER NOT NULL,
            puzzle_id INTEGER NOT NULL,
            best_medal INTEGER NOT NULL DEFAULT 0,
            timer_upgraded INTEGER NOT NULL DEFAULT 0,
            tight_upgraded INTEGER NOT NULL DEFAULT 0,
            first_solved_at TEXT,
            PRIMARY KEY(user_id, puzzle_id)
        );
        """)

    # --- attempts ---
    def create_attempt(self, attempt: SolveAttempt) -> SolveAttempt:
        cur = self.conn.execute(
            """
            INSERT INTO solve_attempts(puzzle_id, user_id, circuit_id, started_at, submitted_at, passed, fail_reason, time_used_seconds, cost_used)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                int(attempt.puzzle_id),
                int(attempt.user_id),
                attempt.circuit_id,
                attempt.started_at.isoformat(),
                attempt.submitted_at.isoformat() if attempt.submitted_at else None,
                None if attempt.passed is None else (1 if attempt.passed else 0),
                attempt.fail_reason,
                attempt.time_used_seconds,
                attempt.cost_used,
            ),
        )
        attempt.id = int(cur.lastrowid)
        return attempt

    def update_attempt(self, attempt: SolveAttempt) -> None:
        self.conn.execute(
            """
            UPDATE solve_attempts SET
                circuit_id=?,
                submitted_at=?,
                passed=?,
                fail_reason=?,
                time_used_seconds=?,
                cost_used=?
            WHERE id=?
            """,
            (
                attempt.circuit_id,
                attempt.submitted_at.isoformat() if attempt.submitted_at else None,
                None if attempt.passed is None else (1 if attempt.passed else 0),
                attempt.fail_reason,
                attempt.time_used_seconds,
                attempt.cost_used,
                int(attempt.id),
            ),
        )

    def get_open_attempt(self, user_id: int, puzzle_id: int) -> Optional[SolveAttempt]:
        row = self.conn.execute(
            """
            SELECT * FROM solve_attempts
            WHERE user_id=? AND puzzle_id=? AND submitted_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (int(user_id), int(puzzle_id)),
        ).fetchone()
        if not row:
            return None
        return SolveAttempt.from_dict(
            {
                "id": int(row["id"]),
                "puzzle_id": int(row["puzzle_id"]),
                "user_id": int(row["user_id"]),
                "circuit_id": row["circuit_id"],
                "started_at": row["started_at"],
                "submitted_at": row["submitted_at"],
                "passed": None if row["passed"] is None else bool(int(row["passed"])),
                "fail_reason": row["fail_reason"],
                "time_used_seconds": row.get("time_used_seconds") if hasattr(row, "get") else row["time_used_seconds"],
                "cost_used": row.get("cost_used") if hasattr(row, "get") else row["cost_used"],
            }
        )

    def has_passed(self, user_id: int, puzzle_id: int) -> bool:
        row = self.conn.execute(
            """
            SELECT 1 FROM solve_attempts
            WHERE user_id=? AND puzzle_id=? AND passed=1
            LIMIT 1
            """,
            (int(user_id), int(puzzle_id)),
        ).fetchone()
        return row is not None

    def has_passed_before_attempt(self, user_id: int, puzzle_id: int, attempt_id: int) -> bool:
        row = self.conn.execute(
            """
            SELECT 1 FROM solve_attempts
            WHERE user_id=? AND puzzle_id=? AND passed=1 AND id < ?
            LIMIT 1
            """,
            (int(user_id), int(puzzle_id), int(attempt_id)),
        ).fetchone()
        return row is not None

    def first_attempt_started_at(self, user_id: int, puzzle_id: int) -> Optional[str]:
        row = self.conn.execute(
            """
            SELECT started_at FROM solve_attempts
            WHERE user_id=? AND puzzle_id=?
            ORDER BY id ASC LIMIT 1
            """,
            (int(user_id), int(puzzle_id)),
        ).fetchone()
        return row["started_at"] if row else None

    # --- progress (medals) ---
    def get_progress(self, user_id: int, puzzle_id: int) -> PuzzleProgress:
        row = self.conn.execute(
            "SELECT * FROM puzzle_progress WHERE user_id=? AND puzzle_id=?",
            (int(user_id), int(puzzle_id)),
        ).fetchone()
        if not row:
            return PuzzleProgress(int(user_id), int(puzzle_id), 0, False, False, None)
        return PuzzleProgress(
            user_id=int(row["user_id"]),
            puzzle_id=int(row["puzzle_id"]),
            best_medal=int(row["best_medal"]),
            timer_upgraded=bool(int(row["timer_upgraded"])),
            tight_upgraded=bool(int(row["tight_upgraded"])),
            first_solved_at=row["first_solved_at"],
        )

    def upsert_progress(self, progress: PuzzleProgress) -> None:
        self.conn.execute(
            """
            INSERT INTO puzzle_progress(user_id, puzzle_id, best_medal, timer_upgraded, tight_upgraded, first_solved_at)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(user_id, puzzle_id) DO UPDATE SET
                best_medal=excluded.best_medal,
                timer_upgraded=excluded.timer_upgraded,
                tight_upgraded=excluded.tight_upgraded,
                first_solved_at=COALESCE(puzzle_progress.first_solved_at, excluded.first_solved_at)
            """,
            (
                int(progress.user_id),
                int(progress.puzzle_id),
                int(progress.best_medal),
                1 if progress.timer_upgraded else 0,
                1 if progress.tight_upgraded else 0,
                progress.first_solved_at,
            ),
        )
