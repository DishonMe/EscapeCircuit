import sqlite3
from typing import Optional, List, Dict

from Backend.DomainLayer.Utils import utcnow


class EngagementRepo:
    """Handles votes, reactions, follows, and bookmarks for discussions and replies."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS discussion_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discussion_id INTEGER NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            value INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(discussion_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS reply_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reply_id INTEGER NOT NULL REFERENCES replies(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            value INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(reply_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS discussion_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discussion_id INTEGER NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            reaction_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(discussion_id, user_id, reaction_type)
        );

        CREATE TABLE IF NOT EXISTS reply_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reply_id INTEGER NOT NULL REFERENCES replies(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            reaction_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(reply_id, user_id, reaction_type)
        );

        CREATE TABLE IF NOT EXISTS discussion_follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discussion_id INTEGER NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            UNIQUE(discussion_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS discussion_bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discussion_id INTEGER NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            UNIQUE(discussion_id, user_id)
        );
        """)

    # ---- Discussion Votes ----

    def get_discussion_vote(self, discussion_id: int, user_id: int) -> Optional[int]:
        row = self.conn.execute(
            "SELECT value FROM discussion_votes WHERE discussion_id=? AND user_id=?",
            (int(discussion_id), int(user_id)),
        ).fetchone()
        return int(row["value"]) if row else None

    def set_discussion_vote(self, discussion_id: int, user_id: int, value: int) -> Optional[int]:
        """Set vote (+1 or -1). Returns the new value, or None if removed (toggle)."""
        existing = self.get_discussion_vote(discussion_id, user_id)
        now = utcnow().isoformat()

        if existing == value:
            # Same vote again -> remove it
            self.conn.execute(
                "DELETE FROM discussion_votes WHERE discussion_id=? AND user_id=?",
                (int(discussion_id), int(user_id)),
            )
            self.conn.commit()
            return None
        elif existing is not None:
            # Different vote -> update
            self.conn.execute(
                "UPDATE discussion_votes SET value=?, created_at=? WHERE discussion_id=? AND user_id=?",
                (value, now, int(discussion_id), int(user_id)),
            )
        else:
            # No existing vote -> insert
            self.conn.execute(
                "INSERT INTO discussion_votes(discussion_id, user_id, value, created_at) VALUES(?,?,?,?)",
                (int(discussion_id), int(user_id), value, now),
            )
        self.conn.commit()
        return value

    def count_discussion_votes(self, discussion_id: int) -> Dict[str, int]:
        row = self.conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN value = 1 THEN 1 ELSE 0 END), 0) as upvotes,
                COALESCE(SUM(CASE WHEN value = -1 THEN 1 ELSE 0 END), 0) as downvotes
            FROM discussion_votes WHERE discussion_id=?
        """, (int(discussion_id),)).fetchone()
        return {"upvotes": int(row["upvotes"]), "downvotes": int(row["downvotes"])}

    # ---- Reply Votes ----

    def get_reply_vote(self, reply_id: int, user_id: int) -> Optional[int]:
        row = self.conn.execute(
            "SELECT value FROM reply_votes WHERE reply_id=? AND user_id=?",
            (int(reply_id), int(user_id)),
        ).fetchone()
        return int(row["value"]) if row else None

    def set_reply_vote(self, reply_id: int, user_id: int, value: int) -> Optional[int]:
        """Set vote (+1 or -1). Returns the new value, or None if removed (toggle)."""
        existing = self.get_reply_vote(reply_id, user_id)
        now = utcnow().isoformat()

        if existing == value:
            self.conn.execute(
                "DELETE FROM reply_votes WHERE reply_id=? AND user_id=?",
                (int(reply_id), int(user_id)),
            )
            self.conn.commit()
            return None
        elif existing is not None:
            self.conn.execute(
                "UPDATE reply_votes SET value=?, created_at=? WHERE reply_id=? AND user_id=?",
                (value, now, int(reply_id), int(user_id)),
            )
        else:
            self.conn.execute(
                "INSERT INTO reply_votes(reply_id, user_id, value, created_at) VALUES(?,?,?,?)",
                (int(reply_id), int(user_id), value, now),
            )
        self.conn.commit()
        return value

    def count_reply_votes(self, reply_id: int) -> Dict[str, int]:
        row = self.conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN value = 1 THEN 1 ELSE 0 END), 0) as upvotes,
                COALESCE(SUM(CASE WHEN value = -1 THEN 1 ELSE 0 END), 0) as downvotes
            FROM reply_votes WHERE reply_id=?
        """, (int(reply_id),)).fetchone()
        return {"upvotes": int(row["upvotes"]), "downvotes": int(row["downvotes"])}

    # ---- Discussion Reactions ----

    def add_discussion_reaction(self, discussion_id: int, user_id: int, reaction_type: str) -> bool:
        """Add a reaction. Returns True if added, False if already exists."""
        now = utcnow().isoformat()
        try:
            self.conn.execute(
                "INSERT INTO discussion_reactions(discussion_id, user_id, reaction_type, created_at) VALUES(?,?,?,?)",
                (int(discussion_id), int(user_id), reaction_type, now),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_discussion_reaction(self, discussion_id: int, user_id: int, reaction_type: str) -> bool:
        """Remove a reaction. Returns True if removed."""
        cur = self.conn.execute(
            "DELETE FROM discussion_reactions WHERE discussion_id=? AND user_id=? AND reaction_type=?",
            (int(discussion_id), int(user_id), reaction_type),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def toggle_discussion_reaction(self, discussion_id: int, user_id: int, reaction_type: str) -> bool:
        """Toggle a reaction. Returns True if now active, False if removed."""
        exists = self.conn.execute(
            "SELECT 1 FROM discussion_reactions WHERE discussion_id=? AND user_id=? AND reaction_type=?",
            (int(discussion_id), int(user_id), reaction_type),
        ).fetchone()
        if exists:
            self.remove_discussion_reaction(discussion_id, user_id, reaction_type)
            return False
        else:
            self.add_discussion_reaction(discussion_id, user_id, reaction_type)
            return True

    def get_discussion_reactions(self, discussion_id: int) -> List[Dict]:
        """Get reaction counts grouped by type."""
        rows = self.conn.execute("""
            SELECT reaction_type, COUNT(*) as count
            FROM discussion_reactions WHERE discussion_id=?
            GROUP BY reaction_type
        """, (int(discussion_id),)).fetchall()
        return [{"type": row["reaction_type"], "count": int(row["count"])} for row in rows]

    def get_user_discussion_reactions(self, discussion_id: int, user_id: int) -> List[str]:
        """Get the reaction types a specific user has on a discussion."""
        rows = self.conn.execute(
            "SELECT reaction_type FROM discussion_reactions WHERE discussion_id=? AND user_id=?",
            (int(discussion_id), int(user_id)),
        ).fetchall()
        return [row["reaction_type"] for row in rows]

    # ---- Reply Reactions ----

    def toggle_reply_reaction(self, reply_id: int, user_id: int, reaction_type: str) -> bool:
        """Toggle a reaction on a reply. Returns True if now active, False if removed."""
        exists = self.conn.execute(
            "SELECT 1 FROM reply_reactions WHERE reply_id=? AND user_id=? AND reaction_type=?",
            (int(reply_id), int(user_id), reaction_type),
        ).fetchone()
        now = utcnow().isoformat()
        if exists:
            self.conn.execute(
                "DELETE FROM reply_reactions WHERE reply_id=? AND user_id=? AND reaction_type=?",
                (int(reply_id), int(user_id), reaction_type),
            )
            self.conn.commit()
            return False
        else:
            try:
                self.conn.execute(
                    "INSERT INTO reply_reactions(reply_id, user_id, reaction_type, created_at) VALUES(?,?,?,?)",
                    (int(reply_id), int(user_id), reaction_type, now),
                )
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_reply_reactions(self, reply_id: int) -> List[Dict]:
        rows = self.conn.execute("""
            SELECT reaction_type, COUNT(*) as count
            FROM reply_reactions WHERE reply_id=?
            GROUP BY reaction_type
        """, (int(reply_id),)).fetchall()
        return [{"type": row["reaction_type"], "count": int(row["count"])} for row in rows]

    def get_user_reply_reactions(self, reply_id: int, user_id: int) -> List[str]:
        rows = self.conn.execute(
            "SELECT reaction_type FROM reply_reactions WHERE reply_id=? AND user_id=?",
            (int(reply_id), int(user_id)),
        ).fetchall()
        return [row["reaction_type"] for row in rows]

    # ---- Discussion Follows ----

    def toggle_follow(self, discussion_id: int, user_id: int) -> bool:
        """Toggle follow. Returns True if now following, False if unfollowed."""
        exists = self.conn.execute(
            "SELECT 1 FROM discussion_follows WHERE discussion_id=? AND user_id=?",
            (int(discussion_id), int(user_id)),
        ).fetchone()
        if exists:
            self.conn.execute(
                "DELETE FROM discussion_follows WHERE discussion_id=? AND user_id=?",
                (int(discussion_id), int(user_id)),
            )
            self.conn.commit()
            return False
        else:
            now = utcnow().isoformat()
            self.conn.execute(
                "INSERT INTO discussion_follows(discussion_id, user_id, created_at) VALUES(?,?,?)",
                (int(discussion_id), int(user_id), now),
            )
            self.conn.commit()
            return True

    def is_following(self, discussion_id: int, user_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM discussion_follows WHERE discussion_id=? AND user_id=?",
            (int(discussion_id), int(user_id)),
        ).fetchone()
        return row is not None

    def get_follower_ids(self, discussion_id: int) -> List[int]:
        rows = self.conn.execute(
            "SELECT user_id FROM discussion_follows WHERE discussion_id=?",
            (int(discussion_id),),
        ).fetchall()
        return [int(row["user_id"]) for row in rows]

    # ---- Discussion Bookmarks ----

    def toggle_bookmark(self, discussion_id: int, user_id: int) -> bool:
        """Toggle bookmark. Returns True if now bookmarked, False if removed."""
        exists = self.conn.execute(
            "SELECT 1 FROM discussion_bookmarks WHERE discussion_id=? AND user_id=?",
            (int(discussion_id), int(user_id)),
        ).fetchone()
        if exists:
            self.conn.execute(
                "DELETE FROM discussion_bookmarks WHERE discussion_id=? AND user_id=?",
                (int(discussion_id), int(user_id)),
            )
            self.conn.commit()
            return False
        else:
            now = utcnow().isoformat()
            self.conn.execute(
                "INSERT INTO discussion_bookmarks(discussion_id, user_id, created_at) VALUES(?,?,?)",
                (int(discussion_id), int(user_id), now),
            )
            self.conn.commit()
            return True

    def is_bookmarked(self, discussion_id: int, user_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM discussion_bookmarks WHERE discussion_id=? AND user_id=?",
            (int(discussion_id), int(user_id)),
        ).fetchone()
        return row is not None

    def get_user_bookmarked_ids(self, user_id: int) -> List[int]:
        rows = self.conn.execute(
            "SELECT discussion_id FROM discussion_bookmarks WHERE user_id=? ORDER BY created_at DESC",
            (int(user_id),),
        ).fetchall()
        return [int(row["discussion_id"]) for row in rows]

    # ---- Bulk engagement data for a discussion (for get_discussion enrichment) ----

    def get_discussion_engagement(self, discussion_id: int, user_id: int) -> Dict:
        """Get all engagement data for a discussion for a specific user."""
        votes = self.count_discussion_votes(discussion_id)
        user_vote = self.get_discussion_vote(discussion_id, user_id)
        reactions = self.get_discussion_reactions(discussion_id)
        user_reactions = self.get_user_discussion_reactions(discussion_id, user_id)
        is_following = self.is_following(discussion_id, user_id)
        is_bookmarked = self.is_bookmarked(discussion_id, user_id)

        return {
            "upvotes": votes["upvotes"],
            "downvotes": votes["downvotes"],
            "user_vote": user_vote,
            "reactions": reactions,
            "user_reactions": user_reactions,
            "is_following": is_following,
            "is_bookmarked": is_bookmarked,
        }

    def get_reply_engagement(self, reply_id: int, user_id: int) -> Dict:
        """Get all engagement data for a reply for a specific user."""
        votes = self.count_reply_votes(reply_id)
        user_vote = self.get_reply_vote(reply_id, user_id)
        reactions = self.get_reply_reactions(reply_id)
        user_reactions = self.get_user_reply_reactions(reply_id, user_id)

        return {
            "upvotes": votes["upvotes"],
            "downvotes": votes["downvotes"],
            "user_vote": user_vote,
            "reactions": reactions,
            "user_reactions": user_reactions,
        }
