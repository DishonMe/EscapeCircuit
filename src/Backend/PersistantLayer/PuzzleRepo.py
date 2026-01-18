import json
import sqlite3
from typing import Optional, List

from Backend.DomainLayer.Puzzle import Puzzle
from Backend.DomainLayer.PuzzleTestCase import PuzzleTestCase
from Backend.DomainLayer.Enums import PuzzleStatus, GateType


class PuzzleRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS puzzles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            creator_user_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            budget INTEGER NOT NULL,
            time_limit_seconds INTEGER,
            default_gate_set TEXT NOT NULL,
            rating_count INTEGER NOT NULL,
            avg_difficulty REAL NOT NULL,
            avg_fun REAL NOT NULL,
            avg_clearness REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS puzzle_test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            puzzle_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            inputs TEXT NOT NULL,
            expected_outputs TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(puzzle_id) REFERENCES puzzles(id) ON DELETE CASCADE
        );
        """)

    def create(self, puzzle: Puzzle) -> Puzzle:
        cur = self.conn.execute("""
            INSERT INTO puzzles(
                name, creator_user_id, description, status,
                budget, time_limit_seconds, default_gate_set,
                rating_count, avg_difficulty, avg_fun, avg_clearness,
                created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            puzzle.name,
            puzzle.creator_user_id,
            puzzle.description,
            puzzle.status.value,
            puzzle.budget,
            puzzle.time_limit_seconds,
            json.dumps([g.value for g in puzzle.default_gate_set]),
            puzzle.rating_count,
            puzzle.avg_difficulty,
            puzzle.avg_fun,
            puzzle.avg_clearness,
            puzzle.created_at.isoformat(),
        ))
        puzzle.id = int(cur.lastrowid)
        return puzzle

    def get_by_id(self, puzzle_id: int) -> Optional[Puzzle]:
        row = self.conn.execute("SELECT * FROM puzzles WHERE id=?", (puzzle_id,)).fetchone()
        return self._row_to_puzzle(row) if row else None

    def update(self, puzzle: Puzzle) -> None:
        self.conn.execute("""
            UPDATE puzzles SET
                name=?,
                creator_user_id=?,
                description=?,
                status=?,
                budget=?,
                time_limit_seconds=?,
                default_gate_set=?,
                rating_count=?,
                avg_difficulty=?,
                avg_fun=?,
                avg_clearness=?
            WHERE id=?
        """, (
            puzzle.name,
            puzzle.creator_user_id,
            puzzle.description,
            puzzle.status.value,
            puzzle.budget,
            puzzle.time_limit_seconds,
            json.dumps([g.value for g in puzzle.default_gate_set]),
            puzzle.rating_count,
            float(puzzle.avg_difficulty),
            float(puzzle.avg_fun),
            float(puzzle.avg_clearness),
            puzzle.id
        ))

    def list_published(self, limit: int = 50, offset: int = 0) -> List[Puzzle]:
        rows = self.conn.execute("""
            SELECT * FROM puzzles
            WHERE status=?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (PuzzleStatus.PUBLISHED.value, limit, offset)).fetchall()
        return [self._row_to_puzzle(r) for r in rows]

    def count_published(self) -> int:
        cur = self.conn.execute("""
            SELECT COUNT(*) FROM puzzles WHERE status=?
        """, (PuzzleStatus.PUBLISHED.value,))
        row = cur.fetchone()
        return row[0] if row else 0

    def search_by_name(self, q: str, only_published: bool = True, limit: int = 50) -> List[Puzzle]:
        like = f"%{q}%"
        if only_published:
            rows = self.conn.execute("""
                SELECT * FROM puzzles
                WHERE status=? AND name LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (PuzzleStatus.PUBLISHED.value, like, limit)).fetchall()
        else:
            rows = self.conn.execute("""
                SELECT * FROM puzzles
                WHERE name LIKE ?
                ORDER BY id DESC LIMIT ?
            """, (like, limit)).fetchall()
        return [self._row_to_puzzle(r) for r in rows]

    def add_test_case(self, tc: PuzzleTestCase) -> PuzzleTestCase:
        cur = self.conn.execute("""
            INSERT INTO puzzle_test_cases(puzzle_id, kind, inputs, expected_outputs, created_at)
            VALUES(?,?,?,?,?)
        """, (
            tc.puzzle_id,
            tc.kind.value,
            json.dumps(tc.inputs),
            json.dumps(tc.expected_outputs),
            tc.created_at.isoformat(),
        ))
        tc.id = int(cur.lastrowid)
        return tc

    def list_test_cases(self, puzzle_id: int) -> List[PuzzleTestCase]:
        rows = self.conn.execute("""
            SELECT * FROM puzzle_test_cases WHERE puzzle_id=? ORDER BY id ASC
        """, (puzzle_id,)).fetchall()
        return [
            PuzzleTestCase.from_dict({
                "id": int(r["id"]),
                "puzzle_id": int(r["puzzle_id"]),
                "kind": r["kind"],
                "inputs": json.loads(r["inputs"]),
                "expected_outputs": json.loads(r["expected_outputs"]),
                "created_at": r["created_at"],
            })
            for r in rows
        ]

    @staticmethod
    def _row_to_puzzle(row: sqlite3.Row) -> Puzzle:
        gate_values = json.loads(row["default_gate_set"])
        return Puzzle.from_dict({
            "id": int(row["id"]),
            "name": row["name"],
            "creator_user_id": int(row["creator_user_id"]),
            "description": row["description"],
            "status": row["status"],
            "budget": int(row["budget"]),
            "time_limit_seconds": row["time_limit_seconds"],
            "default_gate_set": gate_values,
            "rating_count": int(row["rating_count"]),
            "avg_difficulty": float(row["avg_difficulty"]),
            "avg_fun": float(row["avg_fun"]),
            "avg_clearness": float(row["avg_clearness"]),
            "created_at": row["created_at"],
        })
