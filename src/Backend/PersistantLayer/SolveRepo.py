import sqlite3
from dataclasses import dataclass
from typing import Dict, Optional

from Backend.DomainLayer.SolveAttempt import SolveAttempt


@dataclass(frozen=True)
class PuzzleProgress:
    user_id: int
    puzzle_id: int
    best_medal: int  # 0=none, 1=bronze, 2=silver, 3=gold
    timer_upgraded: bool
    tight_upgraded: bool
    first_solved_at: Optional[str]
    max_xp_reached: bool = False
    best_xp: int = 0
    total_xp_awarded: int = 0  # Sum of all deltas awarded (not raw xp_earned)


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
            "time_taken_seconds INTEGER",
            "xp_earned INTEGER DEFAULT 0",
            "highest_medal INTEGER DEFAULT 0",
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
            max_xp_reached INTEGER NOT NULL DEFAULT 0,
            best_xp INTEGER NOT NULL DEFAULT 0,
            total_xp_awarded INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, puzzle_id)
        );
        """)

        # Migrate existing puzzle_progress tables
        for coldef in [
            "max_xp_reached INTEGER NOT NULL DEFAULT 0",
            "best_xp INTEGER NOT NULL DEFAULT 0",
            "total_xp_awarded INTEGER NOT NULL DEFAULT 0",
        ]:
            col = coldef.split()[0]
            pp_cols = {r[1] for r in self.conn.execute("PRAGMA table_info(puzzle_progress);").fetchall()}
            if col not in pp_cols:
                self.conn.execute(f"ALTER TABLE puzzle_progress ADD COLUMN {coldef};")

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

    def get_total_time_on_puzzle(self, user_id: int, puzzle_id: int) -> int:
        """Sum time_used_seconds from solve_attempts for this user/puzzle.
        Used for the 5-minute attempt eligibility rule."""
        row = self.conn.execute(
            """
            SELECT COALESCE(SUM(time_used_seconds), 0) AS total
            FROM solve_attempts
            WHERE user_id=? AND puzzle_id=?
            """,
            (int(user_id), int(puzzle_id)),
        ).fetchone()
        return int(row["total"]) if row else 0

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
            max_xp_reached=bool(int(row["max_xp_reached"])) if "max_xp_reached" in row.keys() else False,
            best_xp=int(row["best_xp"]) if "best_xp" in row.keys() else 0,
            total_xp_awarded=int(row["total_xp_awarded"]) if "total_xp_awarded" in row.keys() else 0,
        )

    # --- solve status map ---
    def get_solve_status_map(self, user_id: int) -> Dict[int, dict]:
        """Return a mapping of puzzle_id -> solve metadata for all puzzles
        the user has passed.  Includes best time, total xp (deltas), and best medal."""
        # Get from puzzle_progress which has the correct total_xp_awarded (sum of deltas)
        rows = self.conn.execute(
            """
            SELECT pp.puzzle_id, pp.best_medal, pp.total_xp_awarded,
                   sa.best_time, sa.first_solved_at
            FROM puzzle_progress pp
            LEFT JOIN (
                SELECT puzzle_id, 
                       MIN(time_taken_seconds) AS best_time,
                       MIN(submitted_at) AS first_solved_at
                FROM solve_attempts
                WHERE user_id = ? AND passed = 1
                GROUP BY puzzle_id
            ) sa ON pp.puzzle_id = sa.puzzle_id
            WHERE pp.user_id = ?
            """,
            (int(user_id), int(user_id)),
        ).fetchall()
        result: Dict[int, dict] = {}
        for r in rows:
            result[int(r["puzzle_id"])] = {
                "is_solved": True,
                "best_time": r["best_time"],
                "total_xp": int(r["total_xp_awarded"]) or 0,
                "best_medal": int(r["best_medal"]) or 0,
                "first_solved_at": r["first_solved_at"],
            }
        return result

    def get_best_xp_for_puzzle(self, user_id: int, puzzle_id: int) -> int:
        """Return the highest xp_earned from any single passed attempt for this user+puzzle.
        Returns 0 if the user has never solved this puzzle."""
        row = self.conn.execute(
            """
            SELECT MAX(xp_earned) AS best_xp
            FROM solve_attempts
            WHERE user_id = ? AND puzzle_id = ? AND passed = 1
            """,
            (int(user_id), int(puzzle_id)),
        ).fetchone()
        return int(row["best_xp"]) if row and row["best_xp"] is not None else 0

    def get_solved_counts(self) -> Dict[int, int]:
        """Return a mapping of puzzle_id -> number of distinct users who solved it."""
        rows = self.conn.execute(
            """
            SELECT puzzle_id, COUNT(DISTINCT user_id) AS solver_count
            FROM solve_attempts
            WHERE passed = 1
            GROUP BY puzzle_id
            """
        ).fetchall()
        return {int(r["puzzle_id"]): int(r["solver_count"]) for r in rows}

    def add_solve(self, user_id: int, puzzle_id: int, time_taken_seconds: int, xp_earned: int, medal: int = 0) -> int:
        """Convenience: insert a passed attempt with time/xp/medal metadata and return its id."""
        from Backend.DomainLayer.Utils import utcnow
        now = utcnow()
        cur = self.conn.execute(
            """
            INSERT INTO solve_attempts(puzzle_id, user_id, started_at, submitted_at, passed,
                                       time_used_seconds, time_taken_seconds, xp_earned, highest_medal)
            VALUES(?,?,?,?,1,?,?,?,?)
            """,
            (int(puzzle_id), int(user_id), now.isoformat(), now.isoformat(),
             int(time_taken_seconds), int(time_taken_seconds), int(xp_earned), int(medal)),
        )
        return int(cur.lastrowid)

    def delete_by_puzzle(self, puzzle_id: int) -> None:
        """Delete all solve attempts and progress for a puzzle."""
        self.conn.execute("DELETE FROM solve_attempts WHERE puzzle_id=?", (int(puzzle_id),))
        self.conn.execute("DELETE FROM puzzle_progress WHERE puzzle_id=?", (int(puzzle_id),))

    def delete_by_puzzle_ids(self, puzzle_ids: list) -> None:
        """Delete all solve attempts and progress for a list of puzzles."""
        if not puzzle_ids:
            return
        placeholders = ",".join("?" * len(puzzle_ids))
        self.conn.execute(f"DELETE FROM solve_attempts WHERE puzzle_id IN ({placeholders})", puzzle_ids)
        self.conn.execute(f"DELETE FROM puzzle_progress WHERE puzzle_id IN ({placeholders})", puzzle_ids)

    def upsert_progress(self, progress: PuzzleProgress) -> None:
        self.conn.execute(
            """
            INSERT INTO puzzle_progress(user_id, puzzle_id, best_medal, timer_upgraded, tight_upgraded, first_solved_at, max_xp_reached, best_xp, total_xp_awarded)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id, puzzle_id) DO UPDATE SET
                best_medal=excluded.best_medal,
                timer_upgraded=excluded.timer_upgraded,
                tight_upgraded=excluded.tight_upgraded,
                first_solved_at=COALESCE(puzzle_progress.first_solved_at, excluded.first_solved_at),
                max_xp_reached=excluded.max_xp_reached,
                best_xp=excluded.best_xp,
                total_xp_awarded=excluded.total_xp_awarded
            """,
            (
                int(progress.user_id),
                int(progress.puzzle_id),
                int(progress.best_medal),
                1 if progress.timer_upgraded else 0,
                1 if progress.tight_upgraded else 0,
                progress.first_solved_at,
                1 if progress.max_xp_reached else 0,
                int(progress.best_xp),
                int(progress.total_xp_awarded),
            ),
        )
