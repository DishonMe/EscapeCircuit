import sqlite3
from typing import Optional, List, Dict

from Backend.DomainLayer.Discussion import Discussion
from Backend.DomainLayer.Utils import utcnow


class DiscussionRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS discussions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            author_id INTEGER NOT NULL REFERENCES users(id),
            puzzle_id INTEGER REFERENCES puzzles(id),
            category TEXT NOT NULL DEFAULT 'general',
            is_pinned INTEGER NOT NULL DEFAULT 0,
            is_locked INTEGER NOT NULL DEFAULT 0,
            view_count INTEGER NOT NULL DEFAULT 0,
            reply_count INTEGER NOT NULL DEFAULT 0,
            upvotes INTEGER NOT NULL DEFAULT 0,
            accepted_reply_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

    def create(self, discussion: Discussion) -> Discussion:
        cur = self.conn.execute("""
            INSERT INTO discussions(title, body, author_id, puzzle_id, category,
                is_pinned, is_locked, view_count, reply_count, upvotes,
                accepted_reply_id, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            discussion.title,
            discussion.body,
            int(discussion.author_id),
            int(discussion.puzzle_id) if discussion.puzzle_id is not None else None,
            discussion.category.value,
            1 if discussion.is_pinned else 0,
            1 if discussion.is_locked else 0,
            discussion.view_count,
            discussion.reply_count,
            discussion.upvotes,
            int(discussion.accepted_reply_id) if discussion.accepted_reply_id is not None else None,
            discussion.created_at.isoformat(),
            discussion.updated_at.isoformat(),
        ))
        self.conn.commit()
        discussion.id = int(cur.lastrowid)
        return discussion

    def get_by_id(self, discussion_id: int) -> Optional[Discussion]:
        row = self.conn.execute(
            "SELECT * FROM discussions WHERE id=?", (int(discussion_id),)
        ).fetchone()
        return self._row_to_discussion(row) if row else None

    def get_by_ids(self, discussion_ids: List[int]) -> Dict[int, Discussion]:
        """Fetch multiple discussions by ID in one query. Returns {id: Discussion} dict."""
        if not discussion_ids:
            return {}
        unique_ids = list(set(int(did) for did in discussion_ids))
        result: Dict[int, Discussion] = {}
        for i in range(0, len(unique_ids), 900):
            chunk = unique_ids[i:i + 900]
            placeholders = ",".join("?" for _ in chunk)
            rows = self.conn.execute(
                f"SELECT * FROM discussions WHERE id IN ({placeholders})", chunk
            ).fetchall()
            for row in rows:
                disc = self._row_to_discussion(row)
                result[disc.id] = disc
        return result

    @staticmethod
    def _build_where(
        category: Optional[str] = None,
        puzzle_id: Optional[int] = None,
        author_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> tuple:
        """Build WHERE clause and params shared by list_all() and count()."""
        where_clauses: list = []
        params: list = []
        if category:
            where_clauses.append("category = ?")
            params.append(category)
        if puzzle_id is not None:
            where_clauses.append("puzzle_id = ?")
            params.append(int(puzzle_id))
        if author_id is not None:
            where_clauses.append("author_id = ?")
            params.append(int(author_id))
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            where_clauses.append("(title LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\')")
            pattern = f"%{escaped}%"
            params.extend([pattern, pattern])
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        return where_sql, params

    def list_all(
        self,
        limit: int = 20,
        offset: int = 0,
        category: Optional[str] = None,
        puzzle_id: Optional[int] = None,
        author_id: Optional[int] = None,
        sort_by: str = "newest",
        search: Optional[str] = None,
    ) -> List[Discussion]:
        where_sql, params = self._build_where(category=category, puzzle_id=puzzle_id, author_id=author_id, search=search)

        order_map = {
            "newest": "created_at DESC",
            "oldest": "created_at ASC",
            "most_replies": "reply_count DESC, created_at DESC",
            "most_upvotes": "upvotes DESC, created_at DESC",
            "trending": "(upvotes * 3 + reply_count * 2 + view_count * 0.5) / MAX(1.0, (julianday('now') - julianday(created_at)) * 24) DESC",
        }
        order_clause = order_map.get(sort_by, "created_at DESC")

        query = f"""
            SELECT * FROM discussions {where_sql}
            ORDER BY is_pinned DESC, {order_clause}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_discussion(r) for r in rows]

    def count(
        self,
        category: Optional[str] = None,
        puzzle_id: Optional[int] = None,
        author_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> int:
        where_sql, params = self._build_where(category=category, puzzle_id=puzzle_id, author_id=author_id, search=search)
        row = self.conn.execute(
            f"SELECT COUNT(*) FROM discussions {where_sql}", params
        ).fetchone()
        return row[0] if row else 0

    def update(self, discussion_id: int, fields: dict) -> Optional[Discussion]:
        allowed = {"title", "body", "category", "is_pinned", "is_locked", "upvotes", "updated_at"}
        set_clauses = []
        params: list = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            if key in ("is_pinned", "is_locked"):
                value = 1 if value else 0
            set_clauses.append(f"{key} = ?")
            params.append(value)

        if not set_clauses:
            return self.get_by_id(discussion_id)

        # Always update updated_at
        if "updated_at" not in fields:
            set_clauses.append("updated_at = ?")
            params.append(utcnow().isoformat())

        params.append(int(discussion_id))
        self.conn.execute(
            f"UPDATE discussions SET {', '.join(set_clauses)} WHERE id = ?", params
        )
        self.conn.commit()
        return self.get_by_id(discussion_id)

    def delete(self, discussion_id: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM discussions WHERE id=?", (int(discussion_id),)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def increment_view_count(self, discussion_id: int) -> None:
        self.conn.execute(
            "UPDATE discussions SET view_count = view_count + 1 WHERE id = ?",
            (int(discussion_id),),
        )
        self.conn.commit()

    def increment_reply_count(self, discussion_id: int, delta: int = 1, commit: bool = True) -> None:
        self.conn.execute(
            "UPDATE discussions SET reply_count = MAX(0, reply_count + ?) WHERE id = ?",
            (delta, int(discussion_id)),
        )
        if commit:
            self.conn.commit()

    def sync_upvotes_from_votes(self, discussion_id: int, commit: bool = True) -> Dict[str, int]:
        """Compute authoritative vote counts, update cache, and return counts.
        Eliminates the need for a separate count_discussion_votes() call."""
        did = int(discussion_id)
        row = self.conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN value = 1 THEN 1 ELSE 0 END), 0) as upvotes,
                COALESCE(SUM(CASE WHEN value = -1 THEN 1 ELSE 0 END), 0) as downvotes
            FROM discussion_votes WHERE discussion_id = ?
        """, (did,)).fetchone()
        upvotes = int(row["upvotes"])
        downvotes = int(row["downvotes"])
        self.conn.execute(
            "UPDATE discussions SET upvotes = ? WHERE id = ?",
            (upvotes, did),
        )
        if commit:
            self.conn.commit()
        return {"upvotes": upvotes, "downvotes": downvotes}

    def set_accepted_reply(self, discussion_id: int, reply_id: Optional[int]) -> None:
        self.conn.execute(
            "UPDATE discussions SET accepted_reply_id = ? WHERE id = ?",
            (int(reply_id) if reply_id is not None else None, int(discussion_id)),
        )
        self.conn.commit()

    @staticmethod
    def _row_to_discussion(row: sqlite3.Row) -> Discussion:
        return Discussion.from_dict({
            "id": int(row["id"]),
            "title": row["title"],
            "body": row["body"],
            "author_id": int(row["author_id"]),
            "puzzle_id": int(row["puzzle_id"]) if row["puzzle_id"] is not None else None,
            "category": row["category"],
            "is_pinned": bool(int(row["is_pinned"])),
            "is_locked": bool(int(row["is_locked"])),
            "view_count": int(row["view_count"]),
            "reply_count": int(row["reply_count"]),
            "upvotes": int(row["upvotes"]),
            "accepted_reply_id": int(row["accepted_reply_id"]) if row["accepted_reply_id"] is not None else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })
