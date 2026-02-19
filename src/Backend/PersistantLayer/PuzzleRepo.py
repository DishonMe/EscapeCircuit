import json
import sqlite3
from typing import Optional, List

from Backend.DomainLayer.Puzzle import Puzzle
from Backend.DomainLayer.PuzzleTestCase import PuzzleTestCase
from Backend.DomainLayer.Enums import PuzzleStatus, GateType, PuzzleDifficulty


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
            difficulty TEXT NOT NULL DEFAULT 'EASY',
            default_gate_set TEXT NOT NULL,
            rating_count INTEGER NOT NULL,
            avg_difficulty REAL NOT NULL,
            avg_fun REAL NOT NULL,
            avg_clearness REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        # Migrate existing DBs that lack the difficulty column
        try:
            cols = {r[1] for r in self.conn.execute("PRAGMA table_info(puzzles);").fetchall()}
            if "difficulty" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN difficulty TEXT NOT NULL DEFAULT 'EASY';")
        except Exception:
            pass
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS puzzle_test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            puzzle_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            inputs TEXT NOT NULL,
            expected_outputs TEXT NOT NULL,
            input_stream TEXT,
            expected_output_stream TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(puzzle_id) REFERENCES puzzles(id) ON DELETE CASCADE
        );
        """)

    def create(self, puzzle: Puzzle) -> Puzzle:
        cur = self.conn.execute("""
            INSERT INTO puzzles(
                name, creator_user_id, description, status,
                budget, time_limit_seconds, difficulty, default_gate_set,
                rating_count, avg_difficulty, avg_fun, avg_clearness,
                created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            puzzle.name,
            puzzle.creator_user_id,
            puzzle.description,
            puzzle.status.value,
            puzzle.budget,
            puzzle.time_limit_seconds,
            puzzle.difficulty.value if hasattr(puzzle.difficulty, 'value') else str(puzzle.difficulty),
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
                difficulty=?,
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
            puzzle.difficulty.value if hasattr(puzzle.difficulty, 'value') else str(puzzle.difficulty),
            json.dumps([g.value for g in puzzle.default_gate_set]),
            puzzle.rating_count,
            float(puzzle.avg_difficulty),
            float(puzzle.avg_fun),
            float(puzzle.avg_clearness),
            puzzle.id
        ))

    def list_published(
        self, 
        limit: int = 50, 
        offset: int = 0,
        search: Optional[str] = None,
        creator_id: Optional[int] = None,
        min_difficulty: Optional[float] = None,
        max_difficulty: Optional[float] = None,
        only_experienced_difficulty: bool = False,
        min_clearness: Optional[float] = None,
        max_clearness: Optional[float] = None,
        only_experienced_clearness: bool = False,
        min_fun: Optional[float] = None,
        max_fun: Optional[float] = None,
        only_experienced_fun: bool = False,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
        order_only_experienced: bool = False
    ) -> List[Puzzle]:
        """
        List published puzzles with optional filters and ordering.
        
        Args:
            search: Partial puzzle name search
            order_by: 'created_at' (default), 'difficulty', 'fun', or 'clearness'
            order_direction: 'DESC' (default) or 'ASC'
            order_only_experienced: If True, uses avg ratings for ordering (experienced users only)
        """
        where_clauses = ["status=?"]
        params = [PuzzleStatus.PUBLISHED.value]
        
        if search is not None:
            where_clauses.append("name LIKE ?")
            params.append(f"%{search}%")
        
        if creator_id is not None:
            where_clauses.append("creator_user_id=?")
            params.append(creator_id)
        
        if min_difficulty is not None or max_difficulty is not None:
            if only_experienced_difficulty:
                # For experienced users: filter by avg_difficulty rating (with fallback to base difficulty)
                # COALESCE to handle NULL avg_difficulty by using base difficulty
                difficulty_case = """
                    CASE 
                        WHEN avg_difficulty IS NOT NULL THEN avg_difficulty
                        WHEN difficulty = 'EASY' THEN 1
                        WHEN difficulty = 'MEDIUM' THEN 2
                        WHEN difficulty = 'HARD' THEN 3
                        ELSE 1.5
                    END
                """
                if min_difficulty is not None:
                    where_clauses.append(f"({difficulty_case}) >= ?")
                    params.append(min_difficulty)
                if max_difficulty is not None:
                    where_clauses.append(f"({difficulty_case}) <= ?")
                    params.append(max_difficulty)
            else:
                # For all users: filter by base puzzle difficulty enum
                # Convert enum strings to numeric values for proper comparison
                if min_difficulty is not None:
                    min_level = self._difficulty_to_level(min_difficulty)
                    where_clauses.append("""
                        CASE 
                            WHEN difficulty = 'EASY' THEN 1
                            WHEN difficulty = 'MEDIUM' THEN 2
                            WHEN difficulty = 'HARD' THEN 3
                            ELSE 1.5
                        END >= ?
                    """)
                    params.append(min_difficulty)
                if max_difficulty is not None:
                    max_level = self._difficulty_to_level(max_difficulty)
                    where_clauses.append("""
                        CASE 
                            WHEN difficulty = 'EASY' THEN 1
                            WHEN difficulty = 'MEDIUM' THEN 2
                            WHEN difficulty = 'HARD' THEN 3
                            ELSE 1.5
                        END <= ?
                    """)
                    params.append(max_difficulty)
        
        if min_clearness is not None or max_clearness is not None:
            # Exclude unrated puzzles when filtering by clearness
            where_clauses.append("avg_clearness > 0")
            if only_experienced_clearness:
                if min_clearness is not None:
                    where_clauses.append("avg_clearness>=?")
                    params.append(min_clearness)
                if max_clearness is not None:
                    where_clauses.append("avg_clearness<=?")
                    params.append(max_clearness)
            else:
                # Filter by min/max clearness regardless of experience
                if min_clearness is not None:
                    where_clauses.append("avg_clearness>=?")
                    params.append(min_clearness)
                if max_clearness is not None:
                    where_clauses.append("avg_clearness<=?")
                    params.append(max_clearness)
        
        if min_fun is not None or max_fun is not None:
            # Exclude unrated puzzles when filtering by fun
            where_clauses.append("avg_fun > 0")
            if only_experienced_fun:
                if min_fun is not None:
                    where_clauses.append("avg_fun>=?")
                    params.append(min_fun)
                if max_fun is not None:
                    where_clauses.append("avg_fun<=?")
                    params.append(max_fun)
            else:
                # Filter by min/max fun regardless of experience
                if min_fun is not None:
                    where_clauses.append("avg_fun>=?")
                    params.append(min_fun)
                if max_fun is not None:
                    where_clauses.append("avg_fun<=?")
                    params.append(max_fun)
        
        if date_from is not None:
            where_clauses.append("created_at>=?")
            params.append(date_from)
        
        if date_to is not None:
            where_clauses.append("created_at<=?")
            params.append(date_to)
        
        # Build order by clause
        valid_order_fields = ["created_at", "difficulty", "fun", "clearness"]
        if order_by not in valid_order_fields:
            order_by = "created_at"
        
        if order_by == "created_at":
            order_clause = f"created_at {order_direction}"
        elif order_by == "difficulty":
            order_clause = f"avg_difficulty {order_direction}"
        elif order_by == "fun":
            order_clause = f"avg_fun {order_direction}"
        elif order_by == "clearness":
            order_clause = f"avg_clearness {order_direction}"
        else:
            order_clause = "created_at DESC"
        
        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT * FROM puzzles
            WHERE {where_sql}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_puzzle(r) for r in rows]

    def count_published(
        self,
        search: Optional[str] = None,
        creator_id: Optional[int] = None,
        min_difficulty: Optional[float] = None,
        max_difficulty: Optional[float] = None,
        only_experienced_difficulty: bool = False,
        min_clearness: Optional[float] = None,
        max_clearness: Optional[float] = None,
        only_experienced_clearness: bool = False,
        min_fun: Optional[float] = None,
        max_fun: Optional[float] = None,
        only_experienced_fun: bool = False,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> int:
        """Count published puzzles with optional filters."""
        where_clauses = ["status=?"]
        params = [PuzzleStatus.PUBLISHED.value]
        
        if search is not None:
            where_clauses.append("name LIKE ?")
            params.append(f"%{search}%")
        
        if creator_id is not None:
            where_clauses.append("creator_user_id=?")
            params.append(creator_id)
        
        if min_difficulty is not None or max_difficulty is not None:
            if only_experienced_difficulty:
                # For experienced users: filter by avg_difficulty rating (with fallback to base difficulty)
                difficulty_case = """
                    CASE 
                        WHEN avg_difficulty IS NOT NULL THEN avg_difficulty
                        WHEN difficulty = 'EASY' THEN 1
                        WHEN difficulty = 'MEDIUM' THEN 2
                        WHEN difficulty = 'HARD' THEN 3
                        ELSE 1.5
                    END
                """
                if min_difficulty is not None:
                    where_clauses.append(f"({difficulty_case}) >= ?")
                    params.append(min_difficulty)
                if max_difficulty is not None:
                    where_clauses.append(f"({difficulty_case}) <= ?")
                    params.append(max_difficulty)
            else:
                # For all users: filter by base puzzle difficulty enum
                if min_difficulty is not None:
                    where_clauses.append("""
                        CASE 
                            WHEN difficulty = 'EASY' THEN 1
                            WHEN difficulty = 'MEDIUM' THEN 2
                            WHEN difficulty = 'HARD' THEN 3
                            ELSE 1.5
                        END >= ?
                    """)
                    params.append(min_difficulty)
                if max_difficulty is not None:
                    where_clauses.append("""
                        CASE 
                            WHEN difficulty = 'EASY' THEN 1
                            WHEN difficulty = 'MEDIUM' THEN 2
                            WHEN difficulty = 'HARD' THEN 3
                            ELSE 1.5
                        END <= ?
                    """)
                    params.append(max_difficulty)
        
        if min_clearness is not None or max_clearness is not None:
            if only_experienced_clearness:
                if min_clearness is not None:
                    where_clauses.append("avg_clearness>=?")
                    params.append(min_clearness)
                if max_clearness is not None:
                    where_clauses.append("avg_clearness<=?")
                    params.append(max_clearness)
        
        if min_fun is not None or max_fun is not None:
            if only_experienced_fun:
                if min_fun is not None:
                    where_clauses.append("avg_fun>=?")
                    params.append(min_fun)
                if max_fun is not None:
                    where_clauses.append("avg_fun<=?")
                    params.append(max_fun)
        
        if date_from is not None:
            where_clauses.append("created_at>=?")
            params.append(date_from)
        
        if date_to is not None:
            where_clauses.append("created_at<=?")
            params.append(date_to)
        
        where_sql = " AND ".join(where_clauses)
        cur = self.conn.execute(f"SELECT COUNT(*) FROM puzzles WHERE {where_sql}", params)
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
            INSERT INTO puzzle_test_cases(puzzle_id, kind, inputs, expected_outputs, input_stream, expected_output_stream, created_at)
            VALUES(?,?,?,?,?,?,?)
        """, (
            tc.puzzle_id,
            tc.kind.value,
            json.dumps(tc.inputs) if tc.inputs else json.dumps({}),
            json.dumps(tc.expected_outputs) if tc.expected_outputs else json.dumps({}),
            json.dumps(tc.input_stream) if tc.input_stream else None,
            json.dumps(tc.expected_output_stream) if tc.expected_output_stream else None,
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
                "inputs": json.loads(r["inputs"]) if r["inputs"] else {},
                "expected_outputs": json.loads(r["expected_outputs"]) if r["expected_outputs"] else {},
                "input_stream": json.loads(r["input_stream"]) if r["input_stream"] else [],
                "expected_output_stream": json.loads(r["expected_output_stream"]) if r["expected_output_stream"] else {},
                "created_at": r["created_at"],
            })
            for r in rows
        ]

    def delete(self, puzzle_id: int) -> bool:
        """Delete a puzzle and its test cases (FK cascade handles test_cases).
        Returns True if a row was actually deleted."""
        cur = self.conn.execute("DELETE FROM puzzles WHERE id=?", (int(puzzle_id),))
        return cur.rowcount > 0

    def list_all_for_admin(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        status: Optional[str] = None,
        creator_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
    ) -> List[Puzzle]:
        """List ALL puzzles (any status) for admin moderation."""
        where_clauses = []
        params = []

        if search is not None:
            where_clauses.append("name LIKE ?")
            params.append(f"%{search}%")
        if status is not None:
            where_clauses.append("status = ?")
            params.append(status)
        if creator_id is not None:
            where_clauses.append("creator_user_id = ?")
            params.append(int(creator_id))
        if date_from is not None:
            where_clauses.append("created_at >= ?")
            params.append(date_from)
        if date_to is not None:
            where_clauses.append("created_at <= ?")
            params.append(date_to)

        valid_order_fields = ["created_at", "avg_fun", "avg_clearness", "rating_count", "name"]
        if order_by not in valid_order_fields:
            order_by = "created_at"
        order_clause = f"{order_by} {order_direction}"

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f"SELECT * FROM puzzles {where_sql} ORDER BY {order_clause} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_puzzle(r) for r in rows]

    def count_all_for_admin(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        creator_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> int:
        """Count ALL puzzles (any status) for admin moderation."""
        where_clauses = []
        params = []

        if search is not None:
            where_clauses.append("name LIKE ?")
            params.append(f"%{search}%")
        if status is not None:
            where_clauses.append("status = ?")
            params.append(status)
        if creator_id is not None:
            where_clauses.append("creator_user_id = ?")
            params.append(int(creator_id))
        if date_from is not None:
            where_clauses.append("created_at >= ?")
            params.append(date_from)
        if date_to is not None:
            where_clauses.append("created_at <= ?")
            params.append(date_to)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        cur = self.conn.execute(f"SELECT COUNT(*) FROM puzzles {where_sql}", params)
        row = cur.fetchone()
        return row[0] if row else 0

    def get_by_creator_and_status(self, creator_user_id: int, status: PuzzleStatus) -> List[Puzzle]:
        """Get all puzzles by a creator with a specific status."""
        rows = self.conn.execute(
            "SELECT * FROM puzzles WHERE creator_user_id=? AND status=?",
            (int(creator_user_id), status.value),
        ).fetchall()
        return [self._row_to_puzzle(r) for r in rows]

    def delete_by_ids(self, puzzle_ids: List[int]) -> int:
        """Delete multiple puzzles by IDs. Returns count deleted."""
        if not puzzle_ids:
            return 0
        placeholders = ",".join("?" * len(puzzle_ids))
        cur = self.conn.execute(
            f"DELETE FROM puzzles WHERE id IN ({placeholders})", puzzle_ids
        )
        return cur.rowcount

    @staticmethod
    def _difficulty_to_level(difficulty_value: float) -> str:
        """Convert a floating point difficulty value to puzzle difficulty level string."""
        if difficulty_value <= 1.5:
            return "EASY"
        elif difficulty_value <= 2.5:
            return "MEDIUM"
        else:
            return "HARD"

    @staticmethod
    def _row_to_puzzle(row: sqlite3.Row) -> Puzzle:
        gate_values = json.loads(row["default_gate_set"])
        # Safely read difficulty — may be missing in old DBs
        try:
            diff_val = row["difficulty"]
        except (IndexError, KeyError):
            diff_val = "EASY"
        return Puzzle.from_dict({
            "id": int(row["id"]),
            "name": row["name"],
            "creator_user_id": int(row["creator_user_id"]),
            "description": row["description"],
            "status": row["status"],
            "budget": int(row["budget"]),
            "time_limit_seconds": row["time_limit_seconds"],
            "difficulty": diff_val or "EASY",
            "default_gate_set": gate_values,
            "rating_count": int(row["rating_count"]),
            "avg_difficulty": float(row["avg_difficulty"]),
            "avg_fun": float(row["avg_fun"]),
            "avg_clearness": float(row["avg_clearness"]),
            "created_at": row["created_at"],
        })
