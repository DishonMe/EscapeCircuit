import json
import sqlite3
from typing import Optional, List

from Backend import settings
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
            instructions TEXT,
            creator_comment TEXT,
            status TEXT NOT NULL,
            budget INTEGER NOT NULL,
            time_limit_seconds INTEGER,
            difficulty TEXT NOT NULL DEFAULT 'EASY',
            default_gate_set TEXT NOT NULL,
            rating_count INTEGER NOT NULL,
            is_hall_of_fame INTEGER NOT NULL DEFAULT 0,
            avg_difficulty REAL NOT NULL,
            avg_fun REAL NOT NULL,
            avg_clearness REAL NOT NULL,
            min_gate_count INTEGER,
            total_gate_count INTEGER,
            min_cycles INTEGER,
            max_cycles INTEGER,
            riddle_base_name TEXT,
            created_at TEXT NOT NULL
        );
        """)
        # Migrate existing DBs that lack the difficulty column
        try:
            cols = {r[1] for r in self.conn.execute("PRAGMA table_info(puzzles);").fetchall()}
            if "difficulty" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN difficulty TEXT NOT NULL DEFAULT 'EASY';")
            if "instructions" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN instructions TEXT;")
            if "min_gate_count" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN min_gate_count INTEGER;")
            if "total_gate_count" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN total_gate_count INTEGER;")
            if "min_cycles" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN min_cycles INTEGER;")
            if "max_cycles" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN max_cycles INTEGER;")
            if "creator_comment" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN creator_comment TEXT;")
            if "allow_arsenal" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN allow_arsenal INTEGER NOT NULL DEFAULT 1;")
            if "board_rows" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN board_rows INTEGER;")
            if "board_cols" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN board_cols INTEGER;")
            if "is_hall_of_fame" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN is_hall_of_fame INTEGER NOT NULL DEFAULT 0;")
            if "creator_budget" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN creator_budget INTEGER;")
            if "allowed_arsenal_component_ids" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN allowed_arsenal_component_ids TEXT;")
            if "arsenal_component_display_modes" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN arsenal_component_display_modes TEXT;")
            if "riddle_base_name" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN riddle_base_name TEXT;")
            if "initial_board_json" not in cols:
                self.conn.execute("ALTER TABLE puzzles ADD COLUMN initial_board_json TEXT;")
        except Exception:
            pass
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS puzzle_test_cases (
            id INTEGER PRIMARY KEY,
            puzzle_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            inputs TEXT NOT NULL,
            expected_outputs TEXT NOT NULL,
            input_stream TEXT,
            expected_output_stream TEXT,
            gate_name TEXT,
            min_gate_limit INTEGER,
            gate_limit INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(puzzle_id) REFERENCES puzzles(id) ON DELETE CASCADE
        );
        """)
        # Migrate existing DBs - add gate_name, min_gate_limit and gate_limit columns if missing
        try:
            cols = {r[1] for r in self.conn.execute("PRAGMA table_info(puzzle_test_cases);").fetchall()}
            if "gate_name" not in cols:
                self.conn.execute("ALTER TABLE puzzle_test_cases ADD COLUMN gate_name TEXT;")
            if "min_gate_limit" not in cols:
                self.conn.execute("ALTER TABLE puzzle_test_cases ADD COLUMN min_gate_limit INTEGER;")
            if "gate_limit" not in cols:
                self.conn.execute("ALTER TABLE puzzle_test_cases ADD COLUMN gate_limit INTEGER;")
            # Remove old constraint columns if they exist (moved to puzzle-level)
            if "max_gate_count" in cols:
                self.conn.execute("ALTER TABLE puzzle_test_cases DROP COLUMN max_gate_count;")
            if "min_cycles" in cols:
                self.conn.execute("ALTER TABLE puzzle_test_cases DROP COLUMN min_cycles;")
            if "max_cycles" in cols:
                self.conn.execute("ALTER TABLE puzzle_test_cases DROP COLUMN max_cycles;")
        except Exception:
            pass
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS user_deleted_puzzles (
            name TEXT PRIMARY KEY,
            deleted_at TEXT NOT NULL
        );
        """)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_deleted_puzzles (
            name TEXT PRIMARY KEY,
            deleted_at TEXT NOT NULL
        );
        """)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_puzzles (
            user_id INTEGER NOT NULL,
            puzzle_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(user_id, puzzle_id),
            FOREIGN KEY(puzzle_id) REFERENCES puzzles(id) ON DELETE CASCADE
        );
        """)

        # Needed by experienced-only puzzle filters/order when PuzzleRepo is used in isolation.
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            puzzle_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            difficulty INTEGER NOT NULL,
            fun INTEGER NOT NULL,
            clearness INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            is_experienced_at_rating INTEGER NOT NULL,
            rating_xp_awarded INTEGER NOT NULL DEFAULT 0,
            UNIQUE(puzzle_id, user_id)
        );
        """)

    def create(self, puzzle: Puzzle) -> Puzzle:
        cur = self.conn.execute("""
            INSERT INTO puzzles(
                name, creator_user_id, description, instructions, creator_comment, status,
                budget, creator_budget, time_limit_seconds, difficulty, default_gate_set,
                rating_count, is_hall_of_fame, avg_difficulty, avg_fun, avg_clearness,
                min_gate_count, total_gate_count, min_cycles, max_cycles,
                riddle_base_name, allow_arsenal, allowed_arsenal_component_ids, arsenal_component_display_modes,
                initial_board_json, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            puzzle.name,
            puzzle.creator_user_id,
            puzzle.description,
            puzzle.instructions,
            puzzle.creator_comment,
            puzzle.status.value,
            puzzle.budget,
            puzzle.creator_budget,
            puzzle.time_limit_seconds,
            puzzle.difficulty.value if hasattr(puzzle.difficulty, 'value') else str(puzzle.difficulty),
            json.dumps([g.value for g in puzzle.default_gate_set]),
            puzzle.rating_count,
            1 if puzzle.is_hall_of_fame else 0,
            puzzle.avg_difficulty,
            puzzle.avg_fun,
            puzzle.avg_clearness,
            puzzle.min_gate_count,
            puzzle.total_gate_count,
            puzzle.min_cycles,
            puzzle.max_cycles,
            puzzle.riddle_base_name,
            1 if puzzle.allow_arsenal else 0,
            json.dumps(puzzle.allowed_arsenal_component_ids) if puzzle.allowed_arsenal_component_ids else None,
            json.dumps(puzzle.arsenal_component_display_modes) if puzzle.arsenal_component_display_modes else None,
            puzzle.initial_board_json,
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
                instructions=?,
                creator_comment=?,
                status=?,
                budget=?,
                creator_budget=?,
                time_limit_seconds=?,
                difficulty=?,
                default_gate_set=?,
                rating_count=?,
                is_hall_of_fame=?,
                avg_difficulty=?,
                avg_fun=?,
                avg_clearness=?,
                min_gate_count=?,
                total_gate_count=?,
                min_cycles=?,
                max_cycles=?,
                allow_arsenal=?,
                allowed_arsenal_component_ids=?,
                arsenal_component_display_modes=?,
                initial_board_json=?
            WHERE id=?
        """, (
            puzzle.name,
            puzzle.creator_user_id,
            puzzle.description,
            puzzle.instructions,
            puzzle.creator_comment,
            puzzle.status.value,
            puzzle.budget,
            puzzle.creator_budget,
            puzzle.time_limit_seconds,
            puzzle.difficulty.value if hasattr(puzzle.difficulty, 'value') else str(puzzle.difficulty),
            json.dumps([g.value for g in puzzle.default_gate_set]),
            puzzle.rating_count,
            1 if puzzle.is_hall_of_fame else 0,
            float(puzzle.avg_difficulty),
            float(puzzle.avg_fun),
            float(puzzle.avg_clearness),
            puzzle.min_gate_count,
            puzzle.total_gate_count,
            puzzle.min_cycles,
            puzzle.max_cycles,
            1 if puzzle.allow_arsenal else 0,
            json.dumps(puzzle.allowed_arsenal_component_ids) if puzzle.allowed_arsenal_component_ids else None,
            json.dumps(puzzle.arsenal_component_display_modes) if puzzle.arsenal_component_display_modes else None,
            puzzle.initial_board_json,
            puzzle.id
        ))

    def update_rating_aggregates(self, puzzle_id: int, **kwargs) -> None:
        """Update only rating-related columns on a puzzle. Avoids clobbering
        non-rating fields that might be modified concurrently (status, name, etc.).
        Accepted keys: rating_count, avg_difficulty, avg_fun, avg_clearness,
        and any future rating aggregate columns."""
        allowed = {
            "rating_count", "avg_difficulty", "avg_fun", "avg_clearness",
        }
        to_set = {k: v for k, v in kwargs.items() if k in allowed}
        if not to_set:
            return
        set_clause = ", ".join(f"{k}=?" for k in to_set)
        vals = list(to_set.values()) + [int(puzzle_id)]
        self.conn.execute(
            f"UPDATE puzzles SET {set_clause} WHERE id=?", vals
        )

    def mark_hall_of_fame(self, puzzle_id: int) -> bool:
        """Set Hall of Fame flag once. Returns True if this call changed state."""
        cur = self.conn.execute(
            "UPDATE puzzles SET is_hall_of_fame = 1 WHERE id = ? AND is_hall_of_fame = 0",
            (int(puzzle_id),),
        )
        return cur.rowcount > 0

    def list_published(
        self, 
        limit: int = 50, 
        offset: int = 0,
        search: Optional[str] = None,
        creator_id: Optional[int] = None,
        creator_username: Optional[str] = None,
        creator_experience_level: Optional[str] = None,
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
        where_clauses = ["p.status=?"]
        params = [PuzzleStatus.PUBLISHED.value]
        join_sql = ""
        exp_avg_difficulty_sql = "(SELECT AVG(r.difficulty) FROM ratings r WHERE r.puzzle_id = p.id AND r.is_experienced_at_rating = 1)"
        exp_avg_fun_sql = "(SELECT AVG(r.fun) FROM ratings r WHERE r.puzzle_id = p.id AND r.is_experienced_at_rating = 1)"
        exp_avg_clearness_sql = "(SELECT AVG(r.clearness) FROM ratings r WHERE r.puzzle_id = p.id AND r.is_experienced_at_rating = 1)"
        
        if search is not None:
            where_clauses.append("p.name LIKE ?")
            params.append(f"%{search}%")
        
        if creator_id is not None:
            where_clauses.append("p.creator_user_id=?")
            params.append(creator_id)

        needs_creator_join = creator_username is not None or creator_experience_level in ("experienced", "inexperienced")
        if needs_creator_join:
            join_sql = "JOIN users u ON p.creator_user_id = u.id"

        if creator_username is not None:
            where_clauses.append("LOWER(u.username) LIKE LOWER(?)")
            params.append(f"%{creator_username}%")

        if creator_experience_level in ("experienced", "inexperienced"):
            experienced_xp_min = self._min_xp_for_level(settings.EXPERIENCED_LEVEL_MIN)
            if creator_experience_level == "experienced":
                where_clauses.append("u.xp >= ?")
            else:
                where_clauses.append("u.xp < ?")
            params.append(experienced_xp_min)
        
        if only_experienced_difficulty:
            # Experienced mode should always restrict to puzzles that have experienced ratings.
            where_clauses.append(f"{exp_avg_difficulty_sql} IS NOT NULL")

        if min_difficulty is not None or max_difficulty is not None:
            if only_experienced_difficulty:
                # For experienced users: filter by avg_difficulty rating (with fallback to base difficulty)
                # COALESCE to handle NULL avg_difficulty by using base difficulty
                difficulty_case = f"""
                    CASE 
                        WHEN {exp_avg_difficulty_sql} IS NOT NULL THEN {exp_avg_difficulty_sql}
                        WHEN p.difficulty = 'EASY' THEN 1
                        WHEN p.difficulty = 'MEDIUM' THEN 2
                        WHEN p.difficulty = 'HARD' THEN 3
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
                            WHEN p.difficulty = 'EASY' THEN 1
                            WHEN p.difficulty = 'MEDIUM' THEN 2
                            WHEN p.difficulty = 'HARD' THEN 3
                            ELSE 1.5
                        END >= ?
                    """)
                    params.append(min_difficulty)
                if max_difficulty is not None:
                    max_level = self._difficulty_to_level(max_difficulty)
                    where_clauses.append("""
                        CASE 
                            WHEN p.difficulty = 'EASY' THEN 1
                            WHEN p.difficulty = 'MEDIUM' THEN 2
                            WHEN p.difficulty = 'HARD' THEN 3
                            ELSE 1.5
                        END <= ?
                    """)
                    params.append(max_difficulty)
        
        if only_experienced_clearness:
            where_clauses.append(f"{exp_avg_clearness_sql} IS NOT NULL")

        if min_clearness is not None or max_clearness is not None:
            # Exclude unrated puzzles when filtering by clearness
            if only_experienced_clearness:
                if min_clearness is not None:
                    where_clauses.append(f"{exp_avg_clearness_sql}>=?")
                    params.append(min_clearness)
                if max_clearness is not None:
                    where_clauses.append(f"{exp_avg_clearness_sql}<=?")
                    params.append(max_clearness)
            else:
                where_clauses.append("p.avg_clearness > 0")
                # Filter by min/max clearness regardless of experience
                if min_clearness is not None:
                    where_clauses.append("p.avg_clearness>=?")
                    params.append(min_clearness)
                if max_clearness is not None:
                    where_clauses.append("p.avg_clearness<=?")
                    params.append(max_clearness)
        
        if only_experienced_fun:
            where_clauses.append(f"{exp_avg_fun_sql} IS NOT NULL")

        if min_fun is not None or max_fun is not None:
            # Exclude unrated puzzles when filtering by fun
            if only_experienced_fun:
                if min_fun is not None:
                    where_clauses.append(f"{exp_avg_fun_sql}>=?")
                    params.append(min_fun)
                if max_fun is not None:
                    where_clauses.append(f"{exp_avg_fun_sql}<=?")
                    params.append(max_fun)
            else:
                where_clauses.append("p.avg_fun > 0")
                # Filter by min/max fun regardless of experience
                if min_fun is not None:
                    where_clauses.append("p.avg_fun>=?")
                    params.append(min_fun)
                if max_fun is not None:
                    where_clauses.append("p.avg_fun<=?")
                    params.append(max_fun)
        
        if date_from is not None:
            where_clauses.append("p.created_at>=?")
            params.append(date_from)
        
        if date_to is not None:
            where_clauses.append("p.created_at<=?")
            params.append(date_to)
        
        # Build order by clause
        valid_order_fields = ["id", "created_at", "difficulty", "fun", "clearness"]
        if order_by not in valid_order_fields:
            order_by = "created_at"
        
        if order_by == "id":
            order_clause = f"p.id {order_direction}"
        elif order_by == "created_at":
            order_clause = f"p.created_at {order_direction}"
        elif order_by == "difficulty":
            if order_only_experienced:
                order_clause = f"COALESCE({exp_avg_difficulty_sql}, CASE WHEN p.difficulty='EASY' THEN 1 WHEN p.difficulty='MEDIUM' THEN 2 WHEN p.difficulty='HARD' THEN 3 ELSE 1.5 END) {order_direction}"
            else:
                order_clause = f"p.avg_difficulty {order_direction}"
        elif order_by == "fun":
            if order_only_experienced:
                order_clause = f"COALESCE({exp_avg_fun_sql}, -1) {order_direction}"
            else:
                order_clause = f"p.avg_fun {order_direction}"
        elif order_by == "clearness":
            if order_only_experienced:
                order_clause = f"COALESCE({exp_avg_clearness_sql}, -1) {order_direction}"
            else:
                order_clause = f"p.avg_clearness {order_direction}"
        else:
            order_clause = "p.created_at DESC"
        
        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT p.* FROM puzzles p
            {join_sql}
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
        creator_username: Optional[str] = None,
        creator_experience_level: Optional[str] = None,
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
        where_clauses = ["p.status=?"]
        params = [PuzzleStatus.PUBLISHED.value]
        join_sql = ""
        exp_avg_difficulty_sql = "(SELECT AVG(r.difficulty) FROM ratings r WHERE r.puzzle_id = p.id AND r.is_experienced_at_rating = 1)"
        exp_avg_fun_sql = "(SELECT AVG(r.fun) FROM ratings r WHERE r.puzzle_id = p.id AND r.is_experienced_at_rating = 1)"
        exp_avg_clearness_sql = "(SELECT AVG(r.clearness) FROM ratings r WHERE r.puzzle_id = p.id AND r.is_experienced_at_rating = 1)"
        
        if search is not None:
            where_clauses.append("p.name LIKE ?")
            params.append(f"%{search}%")
        
        if creator_id is not None:
            where_clauses.append("p.creator_user_id=?")
            params.append(creator_id)

        needs_creator_join = creator_username is not None or creator_experience_level in ("experienced", "inexperienced")
        if needs_creator_join:
            join_sql = "JOIN users u ON p.creator_user_id = u.id"

        if creator_username is not None:
            where_clauses.append("LOWER(u.username) LIKE LOWER(?)")
            params.append(f"%{creator_username}%")

        if creator_experience_level in ("experienced", "inexperienced"):
            experienced_xp_min = self._min_xp_for_level(settings.EXPERIENCED_LEVEL_MIN)
            if creator_experience_level == "experienced":
                where_clauses.append("u.xp >= ?")
            else:
                where_clauses.append("u.xp < ?")
            params.append(experienced_xp_min)
        
        if only_experienced_difficulty:
            where_clauses.append(f"{exp_avg_difficulty_sql} IS NOT NULL")

        if min_difficulty is not None or max_difficulty is not None:
            if only_experienced_difficulty:
                # For experienced users: filter by avg_difficulty rating (with fallback to base difficulty)
                difficulty_case = f"""
                    CASE 
                        WHEN {exp_avg_difficulty_sql} IS NOT NULL THEN {exp_avg_difficulty_sql}
                        WHEN p.difficulty = 'EASY' THEN 1
                        WHEN p.difficulty = 'MEDIUM' THEN 2
                        WHEN p.difficulty = 'HARD' THEN 3
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
                            WHEN p.difficulty = 'EASY' THEN 1
                            WHEN p.difficulty = 'MEDIUM' THEN 2
                            WHEN p.difficulty = 'HARD' THEN 3
                            ELSE 1.5
                        END >= ?
                    """)
                    params.append(min_difficulty)
                if max_difficulty is not None:
                    where_clauses.append("""
                        CASE 
                            WHEN p.difficulty = 'EASY' THEN 1
                            WHEN p.difficulty = 'MEDIUM' THEN 2
                            WHEN p.difficulty = 'HARD' THEN 3
                            ELSE 1.5
                        END <= ?
                    """)
                    params.append(max_difficulty)
        
        if only_experienced_clearness:
            where_clauses.append(f"{exp_avg_clearness_sql} IS NOT NULL")

        if min_clearness is not None or max_clearness is not None:
            if only_experienced_clearness:
                if min_clearness is not None:
                    where_clauses.append(f"{exp_avg_clearness_sql}>=?")
                    params.append(min_clearness)
                if max_clearness is not None:
                    where_clauses.append(f"{exp_avg_clearness_sql}<=?")
                    params.append(max_clearness)
            else:
                if min_clearness is not None:
                    where_clauses.append("p.avg_clearness>=?")
                    params.append(min_clearness)
                if max_clearness is not None:
                    where_clauses.append("p.avg_clearness<=?")
                    params.append(max_clearness)
        
        if only_experienced_fun:
            where_clauses.append(f"{exp_avg_fun_sql} IS NOT NULL")

        if min_fun is not None or max_fun is not None:
            if only_experienced_fun:
                if min_fun is not None:
                    where_clauses.append(f"{exp_avg_fun_sql}>=?")
                    params.append(min_fun)
                if max_fun is not None:
                    where_clauses.append(f"{exp_avg_fun_sql}<=?")
                    params.append(max_fun)
            else:
                if min_fun is not None:
                    where_clauses.append("p.avg_fun>=?")
                    params.append(min_fun)
                if max_fun is not None:
                    where_clauses.append("p.avg_fun<=?")
                    params.append(max_fun)
        
        if date_from is not None:
            where_clauses.append("p.created_at>=?")
            params.append(date_from)
        
        if date_to is not None:
            where_clauses.append("p.created_at<=?")
            params.append(date_to)
        
        where_sql = " AND ".join(where_clauses)
        cur = self.conn.execute(f"SELECT COUNT(*) FROM puzzles p {join_sql} WHERE {where_sql}", params)
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
            INSERT INTO puzzle_test_cases(puzzle_id, kind, inputs, expected_outputs, input_stream, expected_output_stream, gate_name, min_gate_limit, gate_limit, created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (
            tc.puzzle_id,
            tc.kind.value,
            json.dumps(tc.inputs) if tc.inputs else json.dumps({}),
            json.dumps(tc.expected_outputs) if tc.expected_outputs else json.dumps({}),
            json.dumps(tc.input_stream) if tc.input_stream else None,
            json.dumps(tc.expected_output_stream) if tc.expected_output_stream else None,
            tc.gate_name,
            tc.min_gate_limit,
            tc.gate_limit,
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
                "gate_name": dict(r).get("gate_name"),
                "min_gate_limit": dict(r).get("min_gate_limit"),
                "gate_limit": dict(r).get("gate_limit"),
                "min_gate_count": dict(r).get("min_gate_count"),
                "max_gate_count": dict(r).get("max_gate_count"),
                "min_cycles": dict(r).get("min_cycles"),
                "max_cycles": dict(r).get("max_cycles"),
                "created_at": r["created_at"],
            })
            for r in rows
        ]

    @staticmethod
    def _normalize_component_ids(raw_ids) -> List[int]:
        if not isinstance(raw_ids, list):
            return []

        normalized: List[int] = []
        for raw_id in raw_ids:
            try:
                normalized.append(int(raw_id))
            except (TypeError, ValueError):
                continue
        return normalized

    def _table_exists(self, table_name: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (table_name,),
        ).fetchone()
        return row is not None

    def _cleanup_circuits_for_deleted_puzzle(self, puzzle_id: int, shared_component_ids: List[int]) -> None:
        """Clean up puzzle-linked circuits before deleting the puzzle row.

        - Shared arsenal pieces listed on the puzzle are detached (puzzle_id=NULL).
        - All remaining puzzle-linked circuits are deleted.
        """
        if not self._table_exists("circuits"):
            return

        puzzle_id = int(puzzle_id)
        if not shared_component_ids:
            self.conn.execute("DELETE FROM circuits WHERE puzzle_id=?", (puzzle_id,))
            return

        placeholders = ",".join("?" * len(shared_component_ids))
        params = [puzzle_id, *shared_component_ids]

        # Detach shared arsenal pieces so they survive puzzle deletion.
        self.conn.execute(
            f"UPDATE circuits SET puzzle_id=NULL WHERE puzzle_id=? AND id IN ({placeholders})",
            params,
        )

        # Delete all other puzzle-specific pieces.
        self.conn.execute(
            f"DELETE FROM circuits WHERE puzzle_id=? AND id NOT IN ({placeholders})",
            params,
        )

    def delete(self, puzzle_id: int) -> bool:
        """Delete a puzzle and related data.

        - FK cascade handles puzzle_test_cases/saved_puzzles.
        - Puzzle-linked custom pieces are removed from circuits.
        - Puzzle-linked shared arsenal pieces (listed in allowed_arsenal_component_ids)
          are detached from the puzzle (puzzle_id=NULL) but kept.

        Returns True if a row was actually deleted.
        """
        row = self.conn.execute(
            "SELECT allowed_arsenal_component_ids FROM puzzles WHERE id=?",
            (int(puzzle_id),),
        ).fetchone()
        if not row:
            return False

        allowed_ids_json = row["allowed_arsenal_component_ids"]
        try:
            raw_allowed_ids = json.loads(allowed_ids_json) if allowed_ids_json else []
        except (TypeError, ValueError):
            raw_allowed_ids = []

        shared_component_ids = self._normalize_component_ids(raw_allowed_ids)
        self._cleanup_circuits_for_deleted_puzzle(int(puzzle_id), shared_component_ids)

        cur = self.conn.execute("DELETE FROM puzzles WHERE id=?", (int(puzzle_id),))
        return cur.rowcount > 0

    def unpublish_puzzle(self, puzzle_id: int) -> bool:
        """Set puzzle status to unpublished. Returns True if updated."""
        cur = self.conn.execute(
            "UPDATE puzzles SET status = ? WHERE id = ?",
            (PuzzleStatus.UNPUBLISHED.value, int(puzzle_id))
        )
        self.conn.commit()
        return cur.rowcount > 0

    def list_all_for_admin(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        status: Optional[str] = None,
        creator_id: Optional[int] = None,
        creator_username: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
    ) -> List[Puzzle]:
        """List ALL puzzles (any status) for admin moderation."""
        where_clauses = []
        params = []
        join_sql = ""

        if search is not None:
            where_clauses.append("p.name LIKE ?")
            params.append(f"%{search}%")
        if status is not None:
            where_clauses.append("p.status = ?")
            params.append(status)
        if creator_id is not None:
            where_clauses.append("p.creator_user_id = ?")
            params.append(int(creator_id))
        if creator_username is not None:
            join_sql = "JOIN users u ON p.creator_user_id = u.id"
            where_clauses.append("u.username LIKE ?")
            params.append(f"%{creator_username}%")
        if date_from is not None:
            where_clauses.append("p.created_at >= ?")
            params.append(date_from)
        if date_to is not None:
            where_clauses.append("p.created_at <= ?")
            params.append(date_to)

        valid_order_fields = ["created_at", "avg_fun", "avg_clearness", "rating_count", "name"]
        if order_by not in valid_order_fields:
            order_by = "created_at"
        order_clause = f"p.{order_by} {order_direction}"

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f"SELECT p.* FROM puzzles p {join_sql} {where_sql} ORDER BY {order_clause} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_puzzle(r) for r in rows]

    def count_all_for_admin(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        creator_id: Optional[int] = None,
        creator_username: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> int:
        """Count ALL puzzles (any status) for admin moderation."""
        where_clauses = []
        params = []
        join_sql = ""

        if search is not None:
            where_clauses.append("p.name LIKE ?")
            params.append(f"%{search}%")
        if status is not None:
            where_clauses.append("p.status = ?")
            params.append(status)
        if creator_id is not None:
            where_clauses.append("p.creator_user_id = ?")
            params.append(int(creator_id))
        if creator_username is not None:
            join_sql = "JOIN users u ON p.creator_user_id = u.id"
            where_clauses.append("u.username LIKE ?")
            params.append(f"%{creator_username}%")
        if date_from is not None:
            where_clauses.append("p.created_at >= ?")
            params.append(date_from)
        if date_to is not None:
            where_clauses.append("p.created_at <= ?")
            params.append(date_to)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        cur = self.conn.execute(f"SELECT COUNT(*) FROM puzzles p {join_sql} {where_sql}", params)
        row = cur.fetchone()
        return row[0] if row else 0

    def get_by_creator_and_status(self, creator_user_id: int, status: PuzzleStatus) -> List[Puzzle]:
        """Get all puzzles by a creator with a specific status."""
        rows = self.conn.execute(
            "SELECT * FROM puzzles WHERE creator_user_id=? AND status=?",
            (int(creator_user_id), status.value),
        ).fetchall()
        return [self._row_to_puzzle(r) for r in rows]

    def save_for_later(self, user_id: int, puzzle_id: int, created_at: str) -> bool:
        cur = self.conn.execute(
            """
            INSERT OR IGNORE INTO saved_puzzles(user_id, puzzle_id, created_at)
            VALUES (?, ?, ?)
            """,
            (int(user_id), int(puzzle_id), created_at),
        )
        return cur.rowcount > 0

    def remove_saved_puzzle(self, user_id: int, puzzle_id: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM saved_puzzles WHERE user_id=? AND puzzle_id=?",
            (int(user_id), int(puzzle_id)),
        )
        return cur.rowcount > 0

    def list_saved_puzzles(self, user_id: int) -> List[Puzzle]:
        rows = self.conn.execute(
            """
            SELECT p.*
            FROM saved_puzzles sp
            JOIN puzzles p ON p.id = sp.puzzle_id
            WHERE sp.user_id = ?
            ORDER BY sp.created_at DESC
            """,
            (int(user_id),),
        ).fetchall()
        return [self._row_to_puzzle(r) for r in rows]

    def delete_by_ids(self, puzzle_ids: List[int]) -> int:
        """Delete multiple puzzles by IDs. Returns count deleted."""
        if not puzzle_ids:
            return 0

        deleted = 0
        for puzzle_id in puzzle_ids:
            if self.delete(int(puzzle_id)):
                deleted += 1
        return deleted

    def track_user_deletion(self, puzzle_name: str) -> None:
        """Track that a puzzle was deleted by a user."""
        from datetime import datetime, timezone
        deleted_at = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO user_deleted_puzzles(name, deleted_at) VALUES(?, ?)",
            (puzzle_name, deleted_at)
        )

    def track_admin_deletion(self, puzzle_name: str) -> None:
        """Track that a puzzle was deleted by an admin."""
        from datetime import datetime, timezone
        deleted_at = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO admin_deleted_puzzles(name, deleted_at) VALUES(?, ?)",
            (puzzle_name, deleted_at)
        )

    def get_deleted_puzzle_names(self) -> set:
        """Get all deleted puzzle names (both user and admin deletions)."""
        user_deleted = set(
            r[0] for r in self.conn.execute("SELECT name FROM user_deleted_puzzles").fetchall()
        )
        admin_deleted = set(
            r[0] for r in self.conn.execute("SELECT name FROM admin_deleted_puzzles").fetchall()
        )
        return user_deleted | admin_deleted

    def get_user_deleted_puzzle_names(self) -> set:
        """Get puzzle names deleted by users."""
        return set(
            r[0] for r in self.conn.execute("SELECT name FROM user_deleted_puzzles").fetchall()
        )

    def get_admin_deleted_puzzle_names(self) -> set:
        """Get puzzle names deleted by admins."""
        return set(
            r[0] for r in self.conn.execute("SELECT name FROM admin_deleted_puzzles").fetchall()
        )

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
    def _min_xp_for_level(level: int) -> int:
        lvl = max(1, int(level))
        return ((lvl - 1) ** 2) * settings.LEVEL_XP_DIVISOR

    @staticmethod
    def _row_to_puzzle(row: sqlite3.Row) -> Puzzle:
        gate_values = json.loads(row["default_gate_set"])
        # Safely read difficulty — may be missing in old DBs
        try:
            diff_val = row["difficulty"]
        except (IndexError, KeyError):
            diff_val = "EASY"
        # Safely read instructions — may be missing in old DBs
        try:
            instructions_val = row["instructions"]
        except (IndexError, KeyError):
            instructions_val = None
        # Safely read creator_comment — may be missing in old DBs
        try:
            creator_comment_val = row["creator_comment"]
        except (IndexError, KeyError):
            creator_comment_val = None
        # Safely read constraint fields — may be missing in old DBs
        try:
            min_gate_count = row["min_gate_count"]
        except (IndexError, KeyError):
            min_gate_count = None
        try:
            total_gate_count = row["total_gate_count"]
        except (IndexError, KeyError):
            total_gate_count = None
        try:
            min_cycles = row["min_cycles"]
        except (IndexError, KeyError):
            min_cycles = None
        try:
            max_cycles = row["max_cycles"]
        except (IndexError, KeyError):
            max_cycles = None
        # Safely read allow_arsenal — may be missing in old DBs
        try:
            allow_arsenal = bool(int(row["allow_arsenal"]))
        except (IndexError, KeyError, TypeError):
            allow_arsenal = True
        # Safely read board dimensions — may be missing in old DBs
        try:
            board_rows = row["board_rows"]
        except (IndexError, KeyError):
            board_rows = None
        try:
            board_cols = row["board_cols"]
        except (IndexError, KeyError):
            board_cols = None
        try:
            is_hall_of_fame = bool(int(row["is_hall_of_fame"]))
        except (IndexError, KeyError, TypeError, ValueError):
            is_hall_of_fame = False
        try:
            creator_budget = row["creator_budget"]
            creator_budget = int(creator_budget) if creator_budget is not None else None
        except (IndexError, KeyError, TypeError, ValueError):
            creator_budget = None
        # Safely read allowed_arsenal_component_ids — may be missing in old DBs
        try:
            allowed_arsenal_ids_json = row["allowed_arsenal_component_ids"]
            allowed_arsenal_component_ids = json.loads(allowed_arsenal_ids_json) if allowed_arsenal_ids_json else None
        except (IndexError, KeyError, TypeError, ValueError):
            allowed_arsenal_component_ids = None
        # Safely read arsenal_component_display_modes — may be missing in old DBs
        try:
            display_modes_json = row["arsenal_component_display_modes"]
            arsenal_component_display_modes = json.loads(display_modes_json) if display_modes_json else None
        except (IndexError, KeyError, TypeError, ValueError):
            arsenal_component_display_modes = None
        # Safely read riddle_base_name — may be missing in old DBs
        try:
            riddle_base_name = row["riddle_base_name"]
        except (IndexError, KeyError):
            riddle_base_name = None
        # Safely read initial_board_json — may be missing in old DBs
        try:
            initial_board_json = row["initial_board_json"]
        except (IndexError, KeyError):
            initial_board_json = None
        return Puzzle.from_dict({
            "id": int(row["id"]),
            "name": row["name"],
            "creator_user_id": int(row["creator_user_id"]),
            "description": row["description"],
            "instructions": instructions_val,
            "creator_comment": creator_comment_val,
            "status": row["status"],
            "budget": int(row["budget"]),
            "creator_budget": creator_budget,
            "time_limit_seconds": row["time_limit_seconds"],
            "difficulty": diff_val or "EASY",
            "default_gate_set": gate_values,
            "min_gate_count": min_gate_count,
            "total_gate_count": total_gate_count,
            "min_cycles": min_cycles,
            "max_cycles": max_cycles,
            "allow_arsenal": allow_arsenal,
            "allowed_arsenal_component_ids": allowed_arsenal_component_ids,
            "arsenal_component_display_modes": arsenal_component_display_modes,
            "board_rows": board_rows,
            "board_cols": board_cols,
            "rating_count": int(row["rating_count"]),
            "is_hall_of_fame": is_hall_of_fame,
            "avg_difficulty": float(row["avg_difficulty"]),
            "avg_fun": float(row["avg_fun"]),
            "avg_clearness": float(row["avg_clearness"]),
            "created_at": row["created_at"],
            "riddle_base_name": riddle_base_name,
            "initial_board_json": initial_board_json,
        })
