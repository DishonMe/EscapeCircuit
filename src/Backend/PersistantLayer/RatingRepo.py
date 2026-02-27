import sqlite3
from typing import Optional, List

from Backend.DomainLayer.Rating import Rating


class RatingRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
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
            UNIQUE(puzzle_id, user_id)
        );
        """)
        # Migration: add rating_xp_awarded column for atomic first-time XP guard
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(ratings)").fetchall()}
        if "rating_xp_awarded" not in cols:
            self.conn.execute("ALTER TABLE ratings ADD COLUMN rating_xp_awarded INTEGER NOT NULL DEFAULT 0")

    def get_by_puzzle_user(self, puzzle_id: int, user_id: int) -> Optional[Rating]:
        row = self.conn.execute("""
            SELECT * FROM ratings WHERE puzzle_id=? AND user_id=?
        """, (puzzle_id, user_id)).fetchone()
        if not row:
            return None
        return Rating.from_dict({
            "id": int(row["id"]),
            "puzzle_id": int(row["puzzle_id"]),
            "user_id": int(row["user_id"]),
            "difficulty": int(row["difficulty"]),
            "fun": int(row["fun"]),
            "clearness": int(row["clearness"]),
            "created_at": row["created_at"],
            "is_experienced_at_rating": bool(int(row["is_experienced_at_rating"])),
        })

    def upsert(self, rating: Rating, commit: bool = True) -> Rating:
        cur = self.conn.execute("""
            INSERT INTO ratings(puzzle_id, user_id, difficulty, fun, clearness, created_at, is_experienced_at_rating)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(puzzle_id, user_id) DO UPDATE SET
                difficulty=excluded.difficulty,
                fun=excluded.fun,
                clearness=excluded.clearness,
                created_at=excluded.created_at,
                is_experienced_at_rating=excluded.is_experienced_at_rating
        """, (
            rating.puzzle_id,
            rating.user_id,
            rating.difficulty,
            rating.fun,
            rating.clearness,
            rating.created_at.isoformat(),
            1 if rating.is_experienced_at_rating else 0
        ))
        rating.id = int(cur.lastrowid) if cur.lastrowid else rating.id
        if commit:
            self.conn.commit()
        return rating

    def list_by_puzzle(self, puzzle_id: int) -> List[Rating]:
        rows = self.conn.execute("""
            SELECT * FROM ratings WHERE puzzle_id=? ORDER BY id ASC
        """, (puzzle_id,)).fetchall()
        return [
            Rating.from_dict({
                "id": int(r["id"]),
                "puzzle_id": int(r["puzzle_id"]),
                "user_id": int(r["user_id"]),
                "difficulty": int(r["difficulty"]),
                "fun": int(r["fun"]),
                "clearness": int(r["clearness"]),
                "created_at": r["created_at"],
                "is_experienced_at_rating": bool(int(r["is_experienced_at_rating"])),
            })
            for r in rows
        ]

    def delete(self, puzzle_id: int, user_id: int) -> bool:
        cur = self.conn.execute("""
            DELETE FROM ratings WHERE puzzle_id=? AND user_id=?
        """, (int(puzzle_id), int(user_id)))
        self.conn.commit()
        return cur.rowcount > 0

    def delete_by_puzzle(self, puzzle_id: int) -> None:
        """Delete all ratings for a puzzle."""
        self.conn.execute("DELETE FROM ratings WHERE puzzle_id=?", (int(puzzle_id),))

    def try_mark_xp_awarded(self, puzzle_id: int, user_id: int) -> bool:
        """Atomically mark XP as awarded for this rating. Returns True if this was the first time.
        Uses SQL WHERE guard to prevent double-awarding under concurrent requests."""
        cur = self.conn.execute(
            "UPDATE ratings SET rating_xp_awarded = 1 WHERE puzzle_id = ? AND user_id = ? AND rating_xp_awarded = 0",
            (int(puzzle_id), int(user_id)),
        )
        return cur.rowcount > 0

    # Aliases for spec compatibility
    add_rating = upsert
    update_rating = upsert
    delete_rating = delete
    get_ratings_for_puzzle = list_by_puzzle
    get_user_rating = get_by_puzzle_user
