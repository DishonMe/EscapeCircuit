import sqlite3
from typing import Optional, List

from Backend.DomainLayer.Reply import Reply
from Backend.DomainLayer.Utils import utcnow


class ReplyRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discussion_id INTEGER NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
            parent_reply_id INTEGER REFERENCES replies(id) ON DELETE CASCADE,
            author_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL,
            upvotes INTEGER NOT NULL DEFAULT 0,
            downvotes INTEGER NOT NULL DEFAULT 0,
            is_accepted INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

    def create(self, reply: Reply, commit: bool = True) -> Reply:
        cur = self.conn.execute("""
            INSERT INTO replies(discussion_id, parent_reply_id, author_id, body,
                upvotes, downvotes, is_accepted, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (
            int(reply.discussion_id),
            int(reply.parent_reply_id) if reply.parent_reply_id is not None else None,
            int(reply.author_id),
            reply.body,
            reply.upvotes,
            reply.downvotes,
            1 if reply.is_accepted else 0,
            reply.created_at.isoformat(),
            reply.updated_at.isoformat(),
        ))
        if commit:
            self.conn.commit()
        reply.id = int(cur.lastrowid)
        return reply

    def get_by_id(self, reply_id: int) -> Optional[Reply]:
        row = self.conn.execute(
            "SELECT * FROM replies WHERE id=?", (int(reply_id),)
        ).fetchone()
        return self._row_to_reply(row) if row else None

    def list_by_discussion(
        self, discussion_id: int, limit: int = 100, offset: int = 0
    ) -> List[Reply]:
        rows = self.conn.execute("""
            SELECT * FROM replies WHERE discussion_id=?
            ORDER BY created_at ASC LIMIT ? OFFSET ?
        """, (int(discussion_id), limit, offset)).fetchall()
        return [self._row_to_reply(r) for r in rows]

    def list_top_level(
        self, discussion_id: int, limit: int = 100, offset: int = 0
    ) -> List[Reply]:
        rows = self.conn.execute("""
            SELECT * FROM replies
            WHERE discussion_id=? AND parent_reply_id IS NULL
            ORDER BY created_at ASC LIMIT ? OFFSET ?
        """, (int(discussion_id), limit, offset)).fetchall()
        return [self._row_to_reply(r) for r in rows]

    def list_children(self, parent_reply_id: int) -> List[Reply]:
        rows = self.conn.execute("""
            SELECT * FROM replies WHERE parent_reply_id=?
            ORDER BY created_at ASC
        """, (int(parent_reply_id),)).fetchall()
        return [self._row_to_reply(r) for r in rows]

    def count_by_discussion(self, discussion_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM replies WHERE discussion_id=?",
            (int(discussion_id),),
        ).fetchone()
        return row[0] if row else 0

    def update(self, reply_id: int, fields: dict, commit: bool = True) -> Optional[Reply]:
        allowed = {"body", "is_accepted", "updated_at"}
        set_clauses = []
        params: list = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            if key == "is_accepted":
                value = 1 if value else 0
            set_clauses.append(f"{key} = ?")
            params.append(value)

        if not set_clauses:
            return self.get_by_id(reply_id)

        if "updated_at" not in fields:
            set_clauses.append("updated_at = ?")
            params.append(utcnow().isoformat())

        params.append(int(reply_id))
        self.conn.execute(
            f"UPDATE replies SET {', '.join(set_clauses)} WHERE id = ?", params
        )
        if commit:
            self.conn.commit()
        return self.get_by_id(reply_id)

    def delete(self, reply_id: int, commit: bool = True) -> bool:
        cur = self.conn.execute(
            "DELETE FROM replies WHERE id=?", (int(reply_id),)
        )
        if commit:
            self.conn.commit()
        return cur.rowcount > 0

    def update_votes(self, reply_id: int, upvotes: int, downvotes: int, commit: bool = True) -> None:
        self.conn.execute(
            "UPDATE replies SET upvotes=?, downvotes=? WHERE id=?",
            (upvotes, downvotes, int(reply_id)),
        )
        if commit:
            self.conn.commit()

    def sync_votes_from_votes(self, reply_id: int, commit: bool = True) -> None:
        """Atomically update cached upvotes/downvotes from the authoritative reply_votes table."""
        self.conn.execute("""
            UPDATE replies SET
                upvotes = (SELECT COALESCE(SUM(CASE WHEN value = 1 THEN 1 ELSE 0 END), 0) FROM reply_votes WHERE reply_id = ?),
                downvotes = (SELECT COALESCE(SUM(CASE WHEN value = -1 THEN 1 ELSE 0 END), 0) FROM reply_votes WHERE reply_id = ?)
            WHERE id = ?
        """, (int(reply_id), int(reply_id), int(reply_id)))
        if commit:
            self.conn.commit()

    def clear_accepted_for_discussion(self, discussion_id: int, commit: bool = True) -> None:
        self.conn.execute(
            "UPDATE replies SET is_accepted=0 WHERE discussion_id=?",
            (int(discussion_id),),
        )
        if commit:
            self.conn.commit()

    @staticmethod
    def _row_to_reply(row: sqlite3.Row) -> Reply:
        return Reply.from_dict({
            "id": int(row["id"]),
            "discussion_id": int(row["discussion_id"]),
            "parent_reply_id": int(row["parent_reply_id"]) if row["parent_reply_id"] is not None else None,
            "author_id": int(row["author_id"]),
            "body": row["body"],
            "upvotes": int(row["upvotes"]),
            "downvotes": int(row["downvotes"]),
            "is_accepted": bool(int(row["is_accepted"])),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })
