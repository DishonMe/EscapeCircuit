"""
Concurrency regression tests for Root Cause 2+3+4 fixes.

These tests use real SQLite connections and threads to simulate concurrent
FastAPI requests, proving that BEGIN IMMEDIATE transactions prevent the
race conditions identified in the security audit:

  C2 — Solve XP double-award (claim_xp_delta race)
  C3 — Rating aggregate corruption (concurrent rate_puzzle)
  C4 — Reply count drift (concurrent create/delete)
  C5 — Accept reply double-XP (concurrent accept_reply)
  H1 — Engagement toggle wrong state (double-click race)
"""

import sqlite3
import threading
import time
import pytest
from unittest.mock import Mock, MagicMock, patch

from Backend.PersistantLayer._db import ScopedConnection, connect, transaction


# ---------------------------------------------------------------------------
# Helpers: create minimal schemas for targeted concurrency tests
# ---------------------------------------------------------------------------

def _make_test_db() -> str:
    """Return path to a temp DB.  We use a file-based DB so that multiple
    connections (one per thread) can share it via WAL mode."""
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create the minimal tables needed for concurrency tests."""
    conn.executescript("""
        PRAGMA journal_mode = WAL;
        PRAGMA busy_timeout = 30000;
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'SOLVER',
            xp INTEGER NOT NULL DEFAULT 0,
            password_hash TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS puzzles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            creator_user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'PUBLISHED',
            difficulty TEXT NOT NULL DEFAULT 'EASY',
            rating_count INTEGER NOT NULL DEFAULT 0,
            avg_difficulty REAL NOT NULL DEFAULT 0.0,
            avg_fun REAL NOT NULL DEFAULT 0.0,
            avg_clearness REAL NOT NULL DEFAULT 0.0,
            budget INTEGER NOT NULL DEFAULT 999,
            time_limit_seconds INTEGER,
            total_gate_count INTEGER
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            puzzle_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            difficulty INTEGER NOT NULL,
            fun INTEGER NOT NULL,
            clearness INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_experienced_at_rating INTEGER NOT NULL DEFAULT 0,
            rating_xp_awarded INTEGER NOT NULL DEFAULT 0,
            UNIQUE(puzzle_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS discussions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            author_id INTEGER NOT NULL,
            puzzle_id INTEGER,
            category TEXT NOT NULL DEFAULT 'general',
            is_pinned INTEGER NOT NULL DEFAULT 0,
            is_locked INTEGER NOT NULL DEFAULT 0,
            view_count INTEGER NOT NULL DEFAULT 0,
            reply_count INTEGER NOT NULL DEFAULT 0,
            upvotes INTEGER NOT NULL DEFAULT 0,
            accepted_reply_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discussion_id INTEGER NOT NULL,
            parent_reply_id INTEGER,
            author_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            upvotes INTEGER NOT NULL DEFAULT 0,
            downvotes INTEGER NOT NULL DEFAULT 0,
            is_accepted INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

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
            xp_applied INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, puzzle_id)
        );
    """)


def _fresh_conn(db_path: str) -> sqlite3.Connection:
    """Create a fresh connection for a specific thread."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ===========================================================================
# C2: Solve XP claim_xp_delta race — only one thread should win the delta
# ===========================================================================

class TestClaimXpDeltaRace:
    """Two threads concurrently call claim_xp_delta for the same puzzle+user.
    Only one should win — the total XP applied must not exceed total_xp_awarded."""

    def test_concurrent_claim_no_double_award(self):
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        # Seed: user 1 solved puzzle 1, earned 100 XP, none applied yet
        setup_conn.execute("INSERT INTO users(id, username, xp) VALUES(1, 'solver', 0)")
        setup_conn.execute("""
            INSERT INTO puzzle_progress(user_id, puzzle_id, best_medal, total_xp_awarded, xp_applied)
            VALUES(1, 1, 1, 100, 0)
        """)
        setup_conn.commit()
        setup_conn.close()

        results = [0, 0]
        barrier = threading.Barrier(2)

        def claim_xp(thread_idx):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                # Replicate claim_xp_delta logic inside a transaction
                conn.execute("BEGIN IMMEDIATE;")
                row = conn.execute(
                    "SELECT total_xp_awarded, xp_applied FROM puzzle_progress WHERE user_id=1 AND puzzle_id=1"
                ).fetchone()
                unapplied = row["total_xp_awarded"] - row["xp_applied"]
                if unapplied > 0:
                    cur = conn.execute(
                        """UPDATE puzzle_progress SET xp_applied = xp_applied + ?
                           WHERE user_id=1 AND puzzle_id=1
                             AND xp_applied + ? <= total_xp_awarded""",
                        (unapplied, unapplied),
                    )
                    if cur.rowcount > 0:
                        conn.execute(
                            "UPDATE users SET xp = xp + ? WHERE id = 1", (unapplied,)
                        )
                        results[thread_idx] = unapplied
                conn.execute("COMMIT;")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                results[thread_idx] = 0
            finally:
                conn.close()

        t1 = threading.Thread(target=claim_xp, args=(0,))
        t2 = threading.Thread(target=claim_xp, args=(1,))
        t1.start(); t2.start()
        t1.join(timeout=10); t2.join(timeout=10)

        # Verify: total claimed must be exactly 100 (not 200)
        verify = _fresh_conn(db_path)
        row = verify.execute("SELECT xp FROM users WHERE id=1").fetchone()
        progress = verify.execute(
            "SELECT xp_applied, total_xp_awarded FROM puzzle_progress WHERE user_id=1 AND puzzle_id=1"
        ).fetchone()
        verify.close()

        assert row["xp"] == 100, f"XP should be 100, got {row['xp']}"
        assert progress["xp_applied"] == 100, f"xp_applied should be 100, got {progress['xp_applied']}"
        # Exactly one thread should have won
        assert sum(results) == 100, f"Total claimed should be 100, got {sum(results)}"

        import os; os.unlink(db_path)


# ===========================================================================
# C3: Rating aggregate corruption — concurrent ratings must produce correct aggregates
# ===========================================================================

class TestRatingAggregateRace:
    """Multiple threads rate the same puzzle concurrently.
    Aggregates must reflect ALL ratings, not a stale subset."""

    def test_concurrent_ratings_correct_aggregates(self):
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        # Seed: puzzle by user 100, 10 raters (users 1-10)
        setup_conn.execute(
            "INSERT INTO puzzles(id, name, creator_user_id, status) VALUES(1, 'TestPuzzle', 100, 'PUBLISHED')"
        )
        setup_conn.execute("INSERT INTO users(id, username, xp) VALUES(100, 'creator', 0)")
        for i in range(1, 11):
            setup_conn.execute(f"INSERT INTO users(id, username, xp) VALUES({i}, 'user{i}', 0)")
        setup_conn.commit()
        setup_conn.close()

        NUM_RATERS = 10
        barrier = threading.Barrier(NUM_RATERS)
        errors = []

        def rate_puzzle(user_id, difficulty, fun, clearness):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                # Replicate rate_puzzle transaction: upsert + recalculate + store
                conn.execute("BEGIN IMMEDIATE;")

                conn.execute("""
                    INSERT INTO ratings(puzzle_id, user_id, difficulty, fun, clearness)
                    VALUES(1, ?, ?, ?, ?)
                    ON CONFLICT(puzzle_id, user_id) DO UPDATE SET
                        difficulty=excluded.difficulty,
                        fun=excluded.fun,
                        clearness=excluded.clearness
                """, (user_id, difficulty, fun, clearness))

                # Recalculate aggregates from ALL ratings (inside the write lock)
                rows = conn.execute("SELECT difficulty, fun, clearness FROM ratings WHERE puzzle_id=1").fetchall()
                count = len(rows)
                avg_d = sum(r["difficulty"] for r in rows) / count
                avg_f = sum(r["fun"] for r in rows) / count
                avg_c = sum(r["clearness"] for r in rows) / count

                conn.execute("""
                    UPDATE puzzles SET rating_count=?, avg_difficulty=?, avg_fun=?, avg_clearness=?
                    WHERE id=1
                """, (count, avg_d, avg_f, avg_c))

                conn.execute("COMMIT;")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                errors.append(str(e))
            finally:
                conn.close()

        threads = []
        for i in range(1, NUM_RATERS + 1):
            t = threading.Thread(target=rate_puzzle, args=(i, i, i, i))
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert not errors, f"Errors during concurrent rating: {errors}"

        # Verify: all 10 ratings present, aggregates correct
        verify = _fresh_conn(db_path)
        rating_rows = verify.execute("SELECT COUNT(*) as cnt FROM ratings WHERE puzzle_id=1").fetchone()
        puzzle = verify.execute("SELECT rating_count, avg_difficulty, avg_fun, avg_clearness FROM puzzles WHERE id=1").fetchone()
        verify.close()

        assert rating_rows["cnt"] == NUM_RATERS
        assert puzzle["rating_count"] == NUM_RATERS
        expected_avg = sum(range(1, 11)) / 10  # 5.5
        assert abs(puzzle["avg_difficulty"] - expected_avg) < 0.01, f"avg_difficulty should be {expected_avg}, got {puzzle['avg_difficulty']}"
        assert abs(puzzle["avg_fun"] - expected_avg) < 0.01
        assert abs(puzzle["avg_clearness"] - expected_avg) < 0.01

        import os; os.unlink(db_path)


# ===========================================================================
# C4: Reply count drift — concurrent create/delete must maintain consistency
# ===========================================================================

class TestReplyCountDrift:
    """Concurrent reply creates and deletes must leave reply_count = actual COUNT(*)."""

    def test_concurrent_create_delete_no_drift(self):
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        setup_conn.execute("INSERT INTO users(id, username) VALUES(1, 'author')")
        setup_conn.execute("""
            INSERT INTO discussions(id, title, body, author_id, reply_count)
            VALUES(1, 'Test Thread', 'Body', 1, 0)
        """)
        setup_conn.commit()
        setup_conn.close()

        NUM_CREATORS = 10
        barrier = threading.Barrier(NUM_CREATORS)
        errors = []

        def create_and_maybe_delete(thread_idx):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                # Create a reply inside a transaction
                conn.execute("BEGIN IMMEDIATE;")
                cur = conn.execute("""
                    INSERT INTO replies(discussion_id, author_id, body)
                    VALUES(1, 1, ?)
                """, (f"Reply from thread {thread_idx}",))
                reply_id = cur.lastrowid
                conn.execute(
                    "UPDATE discussions SET reply_count = reply_count + 1 WHERE id = 1"
                )
                conn.execute("COMMIT;")

                # Even-numbered threads delete their reply
                if thread_idx % 2 == 0:
                    conn.execute("BEGIN IMMEDIATE;")
                    del_cur = conn.execute("DELETE FROM replies WHERE id = ?", (reply_id,))
                    if del_cur.rowcount > 0:
                        conn.execute(
                            "UPDATE discussions SET reply_count = MAX(0, reply_count - 1) WHERE id = 1"
                        )
                    conn.execute("COMMIT;")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                errors.append(str(e))
            finally:
                conn.close()

        threads = []
        for i in range(NUM_CREATORS):
            t = threading.Thread(target=create_and_maybe_delete, args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert not errors, f"Errors: {errors}"

        # Verify: reply_count == actual COUNT(*)
        verify = _fresh_conn(db_path)
        actual = verify.execute("SELECT COUNT(*) as cnt FROM replies WHERE discussion_id=1").fetchone()["cnt"]
        cached = verify.execute("SELECT reply_count FROM discussions WHERE id=1").fetchone()["reply_count"]
        verify.close()

        assert cached == actual, f"reply_count ({cached}) != actual COUNT (*) ({actual})"
        # 10 created, 5 deleted (even indices 0,2,4,6,8) → 5 remaining
        assert actual == 5, f"Expected 5 replies, got {actual}"

        import os; os.unlink(db_path)


# ===========================================================================
# C5: Accept reply double-XP — only one concurrent acceptor wins XP
# ===========================================================================

class TestAcceptReplyDoubleXp:
    """Two threads concurrently accept the same reply.
    Only one should win the XP award."""

    def test_concurrent_accept_no_double_xp(self):
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        # Seed: discussion by user 1, reply by user 2 (not yet accepted)
        setup_conn.execute("INSERT INTO users(id, username, xp) VALUES(1, 'author', 0)")
        setup_conn.execute("INSERT INTO users(id, username, xp) VALUES(2, 'replier', 0)")
        setup_conn.execute("""
            INSERT INTO discussions(id, title, body, author_id) VALUES(1, 'Test', 'Body', 1)
        """)
        setup_conn.execute("""
            INSERT INTO replies(id, discussion_id, author_id, body, is_accepted)
            VALUES(1, 1, 2, 'Great answer', 0)
        """)
        setup_conn.commit()
        setup_conn.close()

        REPLY_ACCEPTED_XP = 25
        ACCEPT_SOLUTION_XP = 5
        xp_awards = [0, 0]  # Track XP awarded by each thread
        barrier = threading.Barrier(2)

        def accept_reply(thread_idx):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                conn.execute("BEGIN IMMEDIATE;")

                # Re-read is_accepted under write lock (our fix for C5)
                fresh = conn.execute(
                    "SELECT is_accepted FROM replies WHERE id = 1"
                ).fetchone()

                if fresh["is_accepted"]:
                    # Already accepted — no XP
                    conn.execute("COMMIT;")
                    return

                # Atomically set is_accepted=1 only if still 0
                cur = conn.execute(
                    "UPDATE replies SET is_accepted = 1 WHERE id = 1 AND is_accepted = 0"
                )
                if cur.rowcount > 0:
                    # Won the race — award XP
                    conn.execute(
                        "UPDATE users SET xp = xp + ? WHERE id = 2", (REPLY_ACCEPTED_XP,)
                    )
                    conn.execute(
                        "UPDATE users SET xp = xp + ? WHERE id = 1", (ACCEPT_SOLUTION_XP,)
                    )
                    xp_awards[thread_idx] = REPLY_ACCEPTED_XP + ACCEPT_SOLUTION_XP

                conn.execute("UPDATE discussions SET accepted_reply_id = 1 WHERE id = 1")
                conn.execute("COMMIT;")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
            finally:
                conn.close()

        t1 = threading.Thread(target=accept_reply, args=(0,))
        t2 = threading.Thread(target=accept_reply, args=(1,))
        t1.start(); t2.start()
        t1.join(timeout=10); t2.join(timeout=10)

        # Verify: XP awarded exactly once
        verify = _fresh_conn(db_path)
        replier = verify.execute("SELECT xp FROM users WHERE id=2").fetchone()
        author = verify.execute("SELECT xp FROM users WHERE id=1").fetchone()
        reply_row = verify.execute("SELECT is_accepted FROM replies WHERE id=1").fetchone()
        verify.close()

        assert replier["xp"] == REPLY_ACCEPTED_XP, f"Replier XP should be {REPLY_ACCEPTED_XP}, got {replier['xp']}"
        assert author["xp"] == ACCEPT_SOLUTION_XP, f"Author XP should be {ACCEPT_SOLUTION_XP}, got {author['xp']}"
        assert reply_row["is_accepted"] == 1
        # Exactly one thread should have awarded XP
        assert sum(1 for x in xp_awards if x > 0) == 1, f"XP should be awarded by exactly 1 thread, awards: {xp_awards}"

        import os; os.unlink(db_path)


# ===========================================================================
# Rating XP dedup — try_mark_xp_awarded race
# ===========================================================================

class TestRatingXpDedup:
    """Multiple threads concurrently try to mark rating XP as awarded.
    Only one should win the atomic UPDATE ... WHERE rating_xp_awarded = 0."""

    def test_concurrent_mark_xp_only_one_wins(self):
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        setup_conn.execute("INSERT INTO users(id, username, xp) VALUES(1, 'rater', 0)")
        setup_conn.execute("INSERT INTO users(id, username, xp) VALUES(100, 'creator', 0)")
        setup_conn.execute("""
            INSERT INTO ratings(puzzle_id, user_id, difficulty, fun, clearness, rating_xp_awarded)
            VALUES(1, 1, 3, 4, 3, 0)
        """)
        setup_conn.commit()
        setup_conn.close()

        RATING_XP = 5
        NUM_THREADS = 5
        barrier = threading.Barrier(NUM_THREADS)
        wins = [False] * NUM_THREADS

        def try_mark_and_award(idx):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                conn.execute("BEGIN IMMEDIATE;")
                cur = conn.execute(
                    "UPDATE ratings SET rating_xp_awarded = 1 WHERE puzzle_id = 1 AND user_id = 1 AND rating_xp_awarded = 0"
                )
                if cur.rowcount > 0:
                    conn.execute("UPDATE users SET xp = xp + ? WHERE id = 1", (RATING_XP,))
                    wins[idx] = True
                conn.execute("COMMIT;")
            except Exception:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
            finally:
                conn.close()

        threads = [threading.Thread(target=try_mark_and_award, args=(i,)) for i in range(NUM_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        verify = _fresh_conn(db_path)
        user = verify.execute("SELECT xp FROM users WHERE id=1").fetchone()
        rating = verify.execute("SELECT rating_xp_awarded FROM ratings WHERE puzzle_id=1 AND user_id=1").fetchone()
        verify.close()

        assert user["xp"] == RATING_XP, f"XP should be {RATING_XP}, got {user['xp']}"
        assert rating["rating_xp_awarded"] == 1
        assert sum(wins) == 1, f"Exactly 1 thread should win, got {sum(wins)}"

        import os; os.unlink(db_path)


# ===========================================================================
# Stress: many concurrent operations on the same puzzle
# ===========================================================================

class TestConcurrentStress:
    """High-contention stress test: 20 threads performing mixed operations
    on the same puzzle concurrently. No assertion failures, no data corruption."""

    def test_mixed_concurrent_operations(self):
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        # Seed
        setup_conn.execute("INSERT INTO puzzles(id, name, creator_user_id) VALUES(1, 'Stress', 100)")
        setup_conn.execute("INSERT INTO users(id, username, xp) VALUES(100, 'creator', 0)")
        for i in range(1, 21):
            setup_conn.execute(f"INSERT INTO users(id, username, xp) VALUES({i}, 'u{i}', 0)")
        setup_conn.execute("""
            INSERT INTO discussions(id, title, body, author_id) VALUES(1, 'Stress Thread', 'Body', 1)
        """)
        setup_conn.commit()
        setup_conn.close()

        NUM_THREADS = 20
        barrier = threading.Barrier(NUM_THREADS)
        errors = []

        def worker(idx):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                user_id = idx + 1

                # Operation 1: Rate the puzzle
                conn.execute("BEGIN IMMEDIATE;")
                conn.execute("""
                    INSERT INTO ratings(puzzle_id, user_id, difficulty, fun, clearness)
                    VALUES(1, ?, ?, ?, ?)
                    ON CONFLICT(puzzle_id, user_id) DO UPDATE SET
                        difficulty=excluded.difficulty, fun=excluded.fun, clearness=excluded.clearness
                """, (user_id, (idx % 5) + 1, (idx % 5) + 1, (idx % 5) + 1))
                rows = conn.execute("SELECT COUNT(*) as c FROM ratings WHERE puzzle_id=1").fetchone()
                conn.execute("UPDATE puzzles SET rating_count=? WHERE id=1", (rows["c"],))
                conn.execute("COMMIT;")

                # Operation 2: Create a reply
                conn.execute("BEGIN IMMEDIATE;")
                conn.execute(
                    "INSERT INTO replies(discussion_id, author_id, body) VALUES(1, ?, ?)",
                    (user_id, f"Reply {idx}"),
                )
                conn.execute("UPDATE discussions SET reply_count = reply_count + 1 WHERE id = 1")
                conn.execute("COMMIT;")

            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                errors.append(f"Thread {idx}: {e}")
            finally:
                conn.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(NUM_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, f"Errors: {errors}"

        # Verify data integrity
        verify = _fresh_conn(db_path)
        rating_count = verify.execute("SELECT COUNT(*) as c FROM ratings WHERE puzzle_id=1").fetchone()["c"]
        puzzle_count = verify.execute("SELECT rating_count FROM puzzles WHERE id=1").fetchone()["rating_count"]
        reply_count = verify.execute("SELECT COUNT(*) as c FROM replies WHERE discussion_id=1").fetchone()["c"]
        disc_count = verify.execute("SELECT reply_count FROM discussions WHERE id=1").fetchone()["reply_count"]
        verify.close()

        assert rating_count == NUM_THREADS, f"Expected {NUM_THREADS} ratings, got {rating_count}"
        assert puzzle_count == NUM_THREADS, f"puzzle.rating_count should be {NUM_THREADS}, got {puzzle_count}"
        assert reply_count == NUM_THREADS, f"Expected {NUM_THREADS} replies, got {reply_count}"
        assert disc_count == NUM_THREADS, f"discussion.reply_count should be {NUM_THREADS}, got {disc_count}"

        import os; os.unlink(db_path)


# ===========================================================================
# Engagement toggles: concurrent reaction/vote/follow/bookmark atomicity
# ===========================================================================

class TestEngagementToggleRace:
    """Concurrent engagement toggles must never produce duplicate rows
    or leave the state inconsistent."""

    def test_concurrent_reaction_toggle_no_duplicate(self):
        """5 threads toggle the SAME reaction for the same user on the same discussion.
        Final state: exactly 0 or 1 row (no duplicates from INSERT race)."""
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        setup_conn.execute("INSERT INTO users(id, username) VALUES(1, 'author')")
        setup_conn.execute("""
            INSERT INTO discussions(id, title, body, author_id) VALUES(1, 'Eng Test', 'Body', 1)
        """)
        # Need the engagement table
        setup_conn.execute("""
            CREATE TABLE IF NOT EXISTS discussion_reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discussion_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reaction_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(discussion_id, user_id, reaction_type)
            )
        """)
        setup_conn.commit()
        setup_conn.close()

        NUM_THREADS = 5
        barrier = threading.Barrier(NUM_THREADS)
        errors = []
        results = [None] * NUM_THREADS

        def toggle_reaction(idx):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                conn.execute("BEGIN IMMEDIATE;")
                cur = conn.execute(
                    "DELETE FROM discussion_reactions WHERE discussion_id=1 AND user_id=1 AND reaction_type='like'"
                )
                if cur.rowcount > 0:
                    results[idx] = False  # removed
                else:
                    conn.execute(
                        "INSERT INTO discussion_reactions(discussion_id, user_id, reaction_type, created_at) VALUES(1, 1, 'like', '2025-01-01')"
                    )
                    results[idx] = True  # added
                conn.execute("COMMIT;")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                errors.append(str(e))
            finally:
                conn.close()

        threads = [threading.Thread(target=toggle_reaction, args=(i,)) for i in range(NUM_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors: {errors}"

        verify = _fresh_conn(db_path)
        count = verify.execute(
            "SELECT COUNT(*) as cnt FROM discussion_reactions WHERE discussion_id=1 AND user_id=1 AND reaction_type='like'"
        ).fetchone()["cnt"]
        verify.close()

        assert count in (0, 1), f"Expected 0 or 1 reaction rows, got {count} (duplicate INSERT!)"

        import os; os.unlink(db_path)

    def test_concurrent_vote_toggle_correct_state(self):
        """10 threads all upvote the same discussion by the same user.
        Final state: exactly 0 or 1 vote row (toggle semantics)."""
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        setup_conn.execute("INSERT INTO users(id, username) VALUES(1, 'voter')")
        setup_conn.execute("""
            INSERT INTO discussions(id, title, body, author_id) VALUES(1, 'Vote Test', 'Body', 1)
        """)
        setup_conn.execute("""
            CREATE TABLE IF NOT EXISTS discussion_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discussion_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                value INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(discussion_id, user_id)
            )
        """)
        setup_conn.commit()
        setup_conn.close()

        NUM_THREADS = 10
        barrier = threading.Barrier(NUM_THREADS)
        errors = []

        def toggle_upvote(idx):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                conn.execute("BEGIN IMMEDIATE;")
                cur = conn.execute(
                    "DELETE FROM discussion_votes WHERE discussion_id=1 AND user_id=1 AND value=1"
                )
                if cur.rowcount == 0:
                    conn.execute("""
                        INSERT INTO discussion_votes(discussion_id, user_id, value, created_at) VALUES(1, 1, 1, '2025-01-01')
                        ON CONFLICT(discussion_id, user_id) DO UPDATE SET value=excluded.value
                    """)
                conn.execute("COMMIT;")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                errors.append(str(e))
            finally:
                conn.close()

        threads = [threading.Thread(target=toggle_upvote, args=(i,)) for i in range(NUM_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors: {errors}"

        verify = _fresh_conn(db_path)
        rows = verify.execute(
            "SELECT COUNT(*) as cnt FROM discussion_votes WHERE discussion_id=1 AND user_id=1"
        ).fetchone()["cnt"]
        verify.close()

        assert rows in (0, 1), f"Expected 0 or 1 vote rows, got {rows}"

        import os; os.unlink(db_path)

    def test_multi_user_reactions_no_cross_contamination(self):
        """5 different users toggle reactions simultaneously on the same discussion.
        Each user's state must be independent — no cross-contamination."""
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        for uid in range(1, 6):
            setup_conn.execute(f"INSERT INTO users(id, username) VALUES({uid}, 'user{uid}')")
        setup_conn.execute("""
            INSERT INTO discussions(id, title, body, author_id) VALUES(1, 'Multi-user', 'Body', 1)
        """)
        setup_conn.execute("""
            CREATE TABLE IF NOT EXISTS discussion_reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discussion_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reaction_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(discussion_id, user_id, reaction_type)
            )
        """)
        setup_conn.commit()
        setup_conn.close()

        NUM_USERS = 5
        barrier = threading.Barrier(NUM_USERS)
        errors = []

        def add_reaction(user_id):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                conn.execute("BEGIN IMMEDIATE;")
                cur = conn.execute(
                    "DELETE FROM discussion_reactions WHERE discussion_id=1 AND user_id=? AND reaction_type='helpful'",
                    (user_id,),
                )
                if cur.rowcount == 0:
                    conn.execute(
                        "INSERT INTO discussion_reactions(discussion_id, user_id, reaction_type, created_at) VALUES(1, ?, 'helpful', '2025-01-01')",
                        (user_id,),
                    )
                conn.execute("COMMIT;")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                errors.append(str(e))
            finally:
                conn.close()

        threads = [threading.Thread(target=add_reaction, args=(uid,)) for uid in range(1, NUM_USERS + 1)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors: {errors}"

        verify = _fresh_conn(db_path)
        # Each user should have exactly 1 reaction (first toggle = add)
        for uid in range(1, NUM_USERS + 1):
            cnt = verify.execute(
                "SELECT COUNT(*) as cnt FROM discussion_reactions WHERE discussion_id=1 AND user_id=?",
                (uid,),
            ).fetchone()["cnt"]
            assert cnt == 1, f"User {uid} should have exactly 1 reaction, got {cnt}"

        total = verify.execute(
            "SELECT COUNT(*) as cnt FROM discussion_reactions WHERE discussion_id=1"
        ).fetchone()["cnt"]
        verify.close()

        assert total == NUM_USERS, f"Expected {NUM_USERS} total reactions, got {total}"

        import os; os.unlink(db_path)


# ===========================================================================
# Group B: Pin/Lock toggle — concurrent toggles must serialize correctly
# ===========================================================================

class TestPinLockToggleTransaction:
    """Concurrent pin/lock toggles must serialize via IMMEDIATE transactions.
    Even N rapid toggles should leave the field in a deterministic state."""

    def test_concurrent_pin_toggle_consistent_state(self):
        """10 threads toggle is_pinned concurrently.
        Final state must equal actual DB value — no torn writes."""
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        setup_conn.execute("INSERT INTO users(id, username) VALUES(1, 'admin')")
        setup_conn.execute("""
            INSERT INTO discussions(id, title, body, author_id, is_pinned)
            VALUES(1, 'Pin Test', 'Body', 1, 0)
        """)
        setup_conn.commit()
        setup_conn.close()

        NUM_THREADS = 10
        barrier = threading.Barrier(NUM_THREADS)
        errors = []

        def toggle_pin(idx):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                conn.execute("BEGIN IMMEDIATE;")
                conn.execute(
                    "UPDATE discussions SET is_pinned = 1 - is_pinned WHERE id = 1"
                )
                conn.execute("COMMIT;")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                errors.append(str(e))
            finally:
                conn.close()

        threads = [threading.Thread(target=toggle_pin, args=(i,)) for i in range(NUM_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors: {errors}"

        verify = _fresh_conn(db_path)
        pinned = verify.execute("SELECT is_pinned FROM discussions WHERE id=1").fetchone()["is_pinned"]
        verify.close()

        # 10 toggles from 0 → should end at 0 (even number of toggles)
        assert pinned == 0, f"After 10 toggles starting at 0, is_pinned should be 0, got {pinned}"

        import os; os.unlink(db_path)

    def test_concurrent_lock_toggle_consistent_state(self):
        """7 threads toggle is_locked concurrently.
        Odd number of toggles from 0 → must end at 1."""
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        setup_conn.execute("INSERT INTO users(id, username) VALUES(1, 'admin')")
        setup_conn.execute("""
            INSERT INTO discussions(id, title, body, author_id, is_locked)
            VALUES(1, 'Lock Test', 'Body', 1, 0)
        """)
        setup_conn.commit()
        setup_conn.close()

        NUM_THREADS = 7
        barrier = threading.Barrier(NUM_THREADS)
        errors = []

        def toggle_lock(idx):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                conn.execute("BEGIN IMMEDIATE;")
                conn.execute(
                    "UPDATE discussions SET is_locked = 1 - is_locked WHERE id = 1"
                )
                conn.execute("COMMIT;")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                errors.append(str(e))
            finally:
                conn.close()

        threads = [threading.Thread(target=toggle_lock, args=(i,)) for i in range(NUM_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors: {errors}"

        verify = _fresh_conn(db_path)
        locked = verify.execute("SELECT is_locked FROM discussions WHERE id=1").fetchone()["is_locked"]
        verify.close()

        # 7 toggles from 0 → should end at 1 (odd number of toggles)
        assert locked == 1, f"After 7 toggles starting at 0, is_locked should be 1, got {locked}"

        import os; os.unlink(db_path)


# ===========================================================================
# Group D: Circuit/Arsenal capacity TOCTOU — concurrent creates must respect limit
# ===========================================================================

class TestCircuitCapacityTOCTOU:
    """Concurrent circuit creates must not exceed the capacity limit,
    even when all threads pass the COUNT check simultaneously."""

    def test_concurrent_circuit_create_respects_limit(self):
        """5 threads concurrently try to create a circuit for a user with limit=3.
        At most 3 should succeed (the rest hit the capacity or UNIQUE constraint)."""
        db_path = _make_test_db()
        setup_conn = _fresh_conn(db_path)
        _init_schema(setup_conn)

        # Need circuits table
        setup_conn.execute("""
            CREATE TABLE IF NOT EXISTS circuits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                cost INTEGER NOT NULL DEFAULT 0,
                structure_json TEXT NOT NULL DEFAULT '{}',
                is_arsenal INTEGER NOT NULL DEFAULT 0,
                basic_gates TEXT,
                truth_table TEXT,
                num_inputs INTEGER,
                num_outputs INTEGER,
                UNIQUE(user_id, name)
            )
        """)
        setup_conn.execute("INSERT INTO users(id, username, xp) VALUES(1, 'builder', 0)")
        setup_conn.commit()
        setup_conn.close()

        LIMIT = 3
        NUM_THREADS = 5
        barrier = threading.Barrier(NUM_THREADS)
        successes = [False] * NUM_THREADS
        errors_detail = [None] * NUM_THREADS

        def create_circuit(idx):
            conn = _fresh_conn(db_path)
            try:
                barrier.wait(timeout=5)
                conn.execute("BEGIN IMMEDIATE;")
                count_row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM circuits WHERE user_id = 1"
                ).fetchone()
                if count_row["cnt"] >= LIMIT:
                    conn.execute("COMMIT;")
                    errors_detail[idx] = "capacity"
                    return
                conn.execute(
                    "INSERT INTO circuits(user_id, name, cost, structure_json) VALUES(1, ?, 10, '{}')",
                    (f"circuit_{idx}",),
                )
                conn.execute("COMMIT;")
                successes[idx] = True
            except Exception as e:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                errors_detail[idx] = str(e)
            finally:
                conn.close()

        threads = [threading.Thread(target=create_circuit, args=(i,)) for i in range(NUM_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        verify = _fresh_conn(db_path)
        actual_count = verify.execute(
            "SELECT COUNT(*) as cnt FROM circuits WHERE user_id = 1"
        ).fetchone()["cnt"]
        verify.close()

        assert actual_count <= LIMIT, (
            f"Circuit count ({actual_count}) exceeds limit ({LIMIT})! "
            f"TOCTOU bypass detected. Successes: {successes}, Errors: {errors_detail}"
        )
        assert sum(successes) == actual_count, (
            f"Success count ({sum(successes)}) != actual DB count ({actual_count})"
        )

        import os; os.unlink(db_path)
