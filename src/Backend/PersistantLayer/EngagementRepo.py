import sqlite3
from typing import Optional, List, Dict

from Backend.DomainLayer.Utils import utcnow
from Backend.PersistantLayer._db import transaction


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

        CREATE TABLE IF NOT EXISTS engagement_xp_awarded (
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL,
            xp_type TEXT NOT NULL,
            UNIQUE(target_type, target_id, actor_user_id, xp_type)
        );
        """)

    # ---- Engagement XP Guard ----

    def try_award_engagement_xp(self, target_type: str, target_id: int, actor_user_id: int, xp_type: str, commit: bool = True) -> bool:
        """Atomically mark XP as awarded for an engagement action.
        Returns True if this is the first time (XP should be awarded).
        Returns False if XP was already awarded (e.g. upvote toggle cycling)."""
        try:
            self.conn.execute(
                "INSERT INTO engagement_xp_awarded(target_type, target_id, actor_user_id, xp_type) VALUES(?,?,?,?)",
                (target_type, int(target_id), int(actor_user_id), xp_type),
            )
            if commit:
                self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    # ---- Discussion Votes ----

    def get_discussion_vote(self, discussion_id: int, user_id: int) -> Optional[int]:
        row = self.conn.execute(
            "SELECT value FROM discussion_votes WHERE discussion_id=? AND user_id=?",
            (int(discussion_id), int(user_id)),
        ).fetchone()
        return int(row["value"]) if row else None

    def set_discussion_vote(self, discussion_id: int, user_id: int, value: int) -> Optional[int]:
        """Set vote (+1 or -1). Returns the new value, or None if removed (toggle).
        Wrapped in BEGIN IMMEDIATE to make DELETE→check→UPSERT atomic."""
        now = utcnow().isoformat()
        did, uid = int(discussion_id), int(user_id)

        with transaction(self.conn):
            # Try to delete the exact same vote (toggle off)
            cur = self.conn.execute(
                "DELETE FROM discussion_votes WHERE discussion_id=? AND user_id=? AND value=?",
                (did, uid, value),
            )
            if cur.rowcount > 0:
                return None

            # Upsert: insert or update to the new value
            self.conn.execute("""
                INSERT INTO discussion_votes(discussion_id, user_id, value, created_at) VALUES(?,?,?,?)
                ON CONFLICT(discussion_id, user_id) DO UPDATE SET value=excluded.value, created_at=excluded.created_at
            """, (did, uid, value, now))
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
        """Set vote (+1 or -1). Returns the new value, or None if removed (toggle).
        Wrapped in BEGIN IMMEDIATE to make DELETE→check→UPSERT atomic."""
        now = utcnow().isoformat()
        rid, uid = int(reply_id), int(user_id)

        with transaction(self.conn):
            # Try to delete the exact same vote (toggle off)
            cur = self.conn.execute(
                "DELETE FROM reply_votes WHERE reply_id=? AND user_id=? AND value=?",
                (rid, uid, value),
            )
            if cur.rowcount > 0:
                return None

            # Upsert: insert or update to the new value
            self.conn.execute("""
                INSERT INTO reply_votes(reply_id, user_id, value, created_at) VALUES(?,?,?,?)
                ON CONFLICT(reply_id, user_id) DO UPDATE SET value=excluded.value, created_at=excluded.created_at
            """, (rid, uid, value, now))
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

    def toggle_discussion_reaction(self, discussion_id: int, user_id: int, reaction_type: str) -> bool:
        """Toggle a reaction. Returns True if now active, False if removed.
        Wrapped in BEGIN IMMEDIATE — no IntegrityError fallback needed."""
        did, uid = int(discussion_id), int(user_id)
        now = utcnow().isoformat()
        with transaction(self.conn):
            cur = self.conn.execute(
                "DELETE FROM discussion_reactions WHERE discussion_id=? AND user_id=? AND reaction_type=?",
                (did, uid, reaction_type),
            )
            if cur.rowcount > 0:
                return False
            self.conn.execute(
                "INSERT INTO discussion_reactions(discussion_id, user_id, reaction_type, created_at) VALUES(?,?,?,?)",
                (did, uid, reaction_type, now),
            )
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
        """Toggle a reaction on a reply. Returns True if now active, False if removed.
        Wrapped in BEGIN IMMEDIATE — no IntegrityError fallback needed."""
        rid, uid = int(reply_id), int(user_id)
        now = utcnow().isoformat()
        with transaction(self.conn):
            cur = self.conn.execute(
                "DELETE FROM reply_reactions WHERE reply_id=? AND user_id=? AND reaction_type=?",
                (rid, uid, reaction_type),
            )
            if cur.rowcount > 0:
                return False
            self.conn.execute(
                "INSERT INTO reply_reactions(reply_id, user_id, reaction_type, created_at) VALUES(?,?,?,?)",
                (rid, uid, reaction_type, now),
            )
            return True

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
        """Toggle follow. Returns True if now following, False if unfollowed.
        Wrapped in BEGIN IMMEDIATE — no IntegrityError fallback needed."""
        did, uid = int(discussion_id), int(user_id)
        now = utcnow().isoformat()
        with transaction(self.conn):
            cur = self.conn.execute(
                "DELETE FROM discussion_follows WHERE discussion_id=? AND user_id=?",
                (did, uid),
            )
            if cur.rowcount > 0:
                return False
            self.conn.execute(
                "INSERT INTO discussion_follows(discussion_id, user_id, created_at) VALUES(?,?,?)",
                (did, uid, now),
            )
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
        """Toggle bookmark. Returns True if now bookmarked, False if removed.
        Wrapped in BEGIN IMMEDIATE — no IntegrityError fallback needed."""
        did, uid = int(discussion_id), int(user_id)
        now = utcnow().isoformat()
        with transaction(self.conn):
            cur = self.conn.execute(
                "DELETE FROM discussion_bookmarks WHERE discussion_id=? AND user_id=?",
                (did, uid),
            )
            if cur.rowcount > 0:
                return False
            self.conn.execute(
                "INSERT INTO discussion_bookmarks(discussion_id, user_id, created_at) VALUES(?,?,?)",
                (did, uid, now),
            )
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
        """Get all engagement data for a discussion in 3 queries instead of 6."""
        did, uid = int(discussion_id), int(user_id)

        # Query 1: vote counts + user's vote in one pass
        row = self.conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN value = 1 THEN 1 ELSE 0 END), 0) as upvotes,
                COALESCE(SUM(CASE WHEN value = -1 THEN 1 ELSE 0 END), 0) as downvotes,
                MAX(CASE WHEN user_id = ? THEN value ELSE NULL END) as user_vote
            FROM discussion_votes WHERE discussion_id = ?
        """, (uid, did)).fetchone()
        upvotes = int(row["upvotes"])
        downvotes = int(row["downvotes"])
        user_vote = int(row["user_vote"]) if row["user_vote"] is not None else None

        # Query 2: reaction counts + user's reactions in one pass
        reaction_rows = self.conn.execute("""
            SELECT reaction_type, COUNT(*) as count,
                MAX(CASE WHEN user_id = ? THEN 1 ELSE 0 END) as user_reacted
            FROM discussion_reactions WHERE discussion_id = ?
            GROUP BY reaction_type
        """, (uid, did)).fetchall()
        reactions = [{"type": r["reaction_type"], "count": int(r["count"])} for r in reaction_rows]
        user_reactions = [r["reaction_type"] for r in reaction_rows if int(r["user_reacted"])]

        # Query 3: follow + bookmark in one pass
        row = self.conn.execute("""
            SELECT
                EXISTS(SELECT 1 FROM discussion_follows WHERE discussion_id = ? AND user_id = ?) as is_following,
                EXISTS(SELECT 1 FROM discussion_bookmarks WHERE discussion_id = ? AND user_id = ?) as is_bookmarked
        """, (did, uid, did, uid)).fetchone()

        return {
            "upvotes": upvotes,
            "downvotes": downvotes,
            "user_vote": user_vote,
            "reactions": reactions,
            "user_reactions": user_reactions,
            "is_following": bool(row["is_following"]),
            "is_bookmarked": bool(row["is_bookmarked"]),
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

    def get_bulk_reply_engagement(self, reply_ids: List[int], user_id: int) -> Dict[int, Dict]:
        """Get engagement data for multiple replies in 4 queries instead of 4*N.
        Returns {reply_id: {upvotes, downvotes, user_vote, reactions, user_reactions}}."""
        if not reply_ids:
            return {}
        unique_ids = list(set(int(rid) for rid in reply_ids))
        uid = int(user_id)

        result: Dict[int, Dict] = {rid: {
            "upvotes": 0, "downvotes": 0, "user_vote": None,
            "reactions": [], "user_reactions": [],
        } for rid in unique_ids}

        for i in range(0, len(unique_ids), 900):
            chunk = unique_ids[i:i + 900]
            ph = ",".join("?" for _ in chunk)

            # 1. Vote counts per reply
            rows = self.conn.execute(f"""
                SELECT reply_id,
                    COALESCE(SUM(CASE WHEN value = 1 THEN 1 ELSE 0 END), 0) as upvotes,
                    COALESCE(SUM(CASE WHEN value = -1 THEN 1 ELSE 0 END), 0) as downvotes
                FROM reply_votes WHERE reply_id IN ({ph})
                GROUP BY reply_id
            """, chunk).fetchall()
            for row in rows:
                rid = int(row["reply_id"])
                result[rid]["upvotes"] = int(row["upvotes"])
                result[rid]["downvotes"] = int(row["downvotes"])

            # 2. User's votes on these replies
            rows = self.conn.execute(f"""
                SELECT reply_id, value FROM reply_votes
                WHERE reply_id IN ({ph}) AND user_id = ?
            """, chunk + [uid]).fetchall()
            for row in rows:
                result[int(row["reply_id"])]["user_vote"] = int(row["value"])

            # 3. Reaction counts per reply grouped by type
            rows = self.conn.execute(f"""
                SELECT reply_id, reaction_type, COUNT(*) as count
                FROM reply_reactions WHERE reply_id IN ({ph})
                GROUP BY reply_id, reaction_type
            """, chunk).fetchall()
            for row in rows:
                rid = int(row["reply_id"])
                result[rid]["reactions"].append({
                    "type": row["reaction_type"],
                    "count": int(row["count"]),
                })

            # 4. User's reactions on these replies
            rows = self.conn.execute(f"""
                SELECT reply_id, reaction_type FROM reply_reactions
                WHERE reply_id IN ({ph}) AND user_id = ?
            """, chunk + [uid]).fetchall()
            for row in rows:
                result[int(row["reply_id"])]["user_reactions"].append(row["reaction_type"])

        return result
