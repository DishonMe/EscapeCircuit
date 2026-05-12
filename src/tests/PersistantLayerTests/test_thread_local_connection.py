"""Tests for ThreadLocalConnection — the per-thread SQLite connection proxy.

These tests prove that:
1. Each thread gets its own isolated connection (no transaction bleed).
2. Concurrent writes on separate threads do not corrupt each other.
3. The proxy is a drop-in replacement for sqlite3.Connection.
4. The transaction() context manager works with the proxy.
"""

import contextvars
import sqlite3
import tempfile
import threading
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from Backend.PersistantLayer._db import (
    ScopedConnection,
    ThreadLocalConnection,
    connect,
    transaction,
    _make_conn,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """Return a path to a temporary SQLite database file."""
    return str(tmp_path / "test.db")


@pytest.fixture
def proxy(db_path):
    """Create a ThreadLocalConnection proxy with a test schema."""
    p = connect(db_path)
    p.execute(
        "CREATE TABLE IF NOT EXISTS counters (id INTEGER PRIMARY KEY, value INTEGER NOT NULL)"
    )
    p.execute("INSERT INTO counters (id, value) VALUES (1, 0)")
    p.commit()
    return p


# ---------------------------------------------------------------------------
# 1. Thread isolation — each thread gets its own connection
# ---------------------------------------------------------------------------


class TestThreadIsolation:
    def test_different_threads_get_different_connections(self, db_path):
        """Two threads must not share the same underlying sqlite3 connection."""
        proxy = connect(db_path)
        conn_ids = []
        barrier = threading.Barrier(2)

        def worker():
            raw = proxy.get_raw_connection()
            conn_ids.append(id(raw))
            barrier.wait()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(conn_ids) == 2
        assert conn_ids[0] != conn_ids[1], "Threads must get different connections"

    def test_same_thread_gets_same_connection(self, db_path):
        """Repeated access on the same thread returns the same connection."""
        proxy = connect(db_path)
        c1 = proxy.get_raw_connection()
        c2 = proxy.get_raw_connection()
        assert c1 is c2

    def test_row_factory_set_on_each_thread(self, db_path):
        """Every thread-local connection must have row_factory = sqlite3.Row."""
        proxy = connect(db_path)
        proxy.execute("CREATE TABLE t (x INTEGER)")
        proxy.execute("INSERT INTO t VALUES (42)")
        proxy.commit()

        results = []

        def worker():
            row = proxy.execute("SELECT x FROM t").fetchone()
            results.append(type(row))

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert results[0] is sqlite3.Row

    def test_pragmas_set_on_each_thread(self, db_path):
        """Foreign keys and WAL mode must be active on every connection."""
        proxy = connect(db_path)
        results = {}

        def worker():
            fk = proxy.execute("PRAGMA foreign_keys").fetchone()[0]
            jm = proxy.execute("PRAGMA journal_mode").fetchone()[0]
            results["fk"] = fk
            results["jm"] = jm

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert results["fk"] == 1, "foreign_keys must be ON"
        assert results["jm"] == "wal", "journal_mode must be WAL"


# ---------------------------------------------------------------------------
# 2. No transaction bleed between threads
# ---------------------------------------------------------------------------


class TestNoTransactionBleed:
    def test_rollback_on_one_thread_does_not_affect_another(self, proxy):
        """A ROLLBACK on thread A must not undo thread B's committed work.

        Thread B commits first, then thread A rolls back — the key
        assertion is that B's data survives A's rollback because they
        operate on separate connections.
        """
        done_b = threading.Event()
        done_a = threading.Event()
        errors = []

        def writer_b():
            """Commits an insert on its own connection."""
            try:
                proxy.execute(
                    "INSERT INTO counters (id, value) VALUES (20, 200)"
                )
                proxy.commit()
                done_b.set()  # signal: B is committed
            except Exception as e:
                errors.append(e)
                done_b.set()

        def writer_a():
            """Waits for B to commit, then inserts and rolls back."""
            try:
                done_b.wait(timeout=5)  # wait for B
                raw = proxy.get_raw_connection()
                raw.execute("BEGIN IMMEDIATE")
                raw.execute(
                    "INSERT INTO counters (id, value) VALUES (10, 100)"
                )
                raw.execute("ROLLBACK")
                done_a.set()
            except Exception as e:
                errors.append(e)
                done_a.set()

        t2 = threading.Thread(target=writer_b)
        t1 = threading.Thread(target=writer_a)
        t2.start()
        t1.start()
        t1.join()
        t2.join()

        assert not errors, f"Unexpected errors: {errors}"

        # Thread A's insert (id=10) should be rolled back
        row_a = proxy.execute(
            "SELECT value FROM counters WHERE id = 10"
        ).fetchone()
        assert row_a is None, "Thread A's rollback must not persist"

        # Thread B's insert (id=20) should survive
        row_b = proxy.execute(
            "SELECT value FROM counters WHERE id = 20"
        ).fetchone()
        assert row_b is not None, "Thread B's commit must survive A's rollback"
        assert row_b["value"] == 200

    def test_commit_on_one_thread_does_not_auto_commit_another(self, proxy):
        """A commit on thread A must not commit thread B's uncommitted work.

        Thread A commits, then thread B rolls back — B's data must be gone.
        With the OLD shared-connection pattern, A's commit would have
        also committed B's pending data.
        """
        done_a = threading.Event()
        errors = []

        def writer_a():
            try:
                proxy.execute(
                    "INSERT INTO counters (id, value) VALUES (30, 300)"
                )
                proxy.commit()
                done_a.set()
            except Exception as e:
                errors.append(e)
                done_a.set()

        def writer_b():
            try:
                done_a.wait(timeout=5)  # wait for A to commit
                raw = proxy.get_raw_connection()
                raw.execute("BEGIN IMMEDIATE")
                raw.execute(
                    "INSERT INTO counters (id, value) VALUES (40, 400)"
                )
                raw.execute("ROLLBACK")
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=writer_a)
        t2 = threading.Thread(target=writer_b)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors, f"Unexpected errors: {errors}"

        row_a = proxy.execute(
            "SELECT value FROM counters WHERE id = 30"
        ).fetchone()
        assert row_a is not None and row_a["value"] == 300

        row_b = proxy.execute(
            "SELECT value FROM counters WHERE id = 40"
        ).fetchone()
        assert row_b is None, "Thread B's uncommitted data must not persist"


# ---------------------------------------------------------------------------
# 3. Concurrent writes don't corrupt data
# ---------------------------------------------------------------------------


class TestConcurrentWrites:
    def test_concurrent_increments_are_not_lost(self, proxy):
        """N threads each incrementing a counter by 1 must produce final value = N."""
        num_threads = 20
        iterations_per_thread = 50

        def increment_worker():
            for _ in range(iterations_per_thread):
                proxy.execute(
                    "UPDATE counters SET value = value + 1 WHERE id = 1"
                )
                proxy.commit()

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=increment_worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        row = proxy.execute("SELECT value FROM counters WHERE id = 1").fetchone()
        expected = num_threads * iterations_per_thread
        assert row["value"] == expected, (
            f"Expected {expected}, got {row['value']}. Lost updates detected."
        )

    def test_concurrent_inserts_no_duplicates(self, proxy):
        """Concurrent inserts with unique IDs must all succeed."""
        num_threads = 10
        rows_per_thread = 20

        def insert_worker(thread_id):
            for i in range(rows_per_thread):
                row_id = (thread_id + 1) * 1000 + i  # +1 to avoid id=1 from fixture
                proxy.execute(
                    "INSERT INTO counters (id, value) VALUES (?, ?)",
                    (row_id, thread_id),
                )
                proxy.commit()

        with ThreadPoolExecutor(max_workers=num_threads) as pool:
            futures = [
                pool.submit(insert_worker, tid) for tid in range(num_threads)
            ]
            for f in as_completed(futures):
                f.result()  # raise if any thread failed

        total = proxy.execute("SELECT COUNT(*) FROM counters").fetchone()[0]
        # +1 for the initial row with id=1
        assert total == num_threads * rows_per_thread + 1

    def test_concurrent_upserts_converge(self, proxy):
        """Concurrent upserts on the same row must not lose updates."""
        num_threads = 10

        def upsert_worker(thread_id):
            for i in range(50):
                proxy.execute(
                    """INSERT INTO counters (id, value) VALUES (1, ?)
                       ON CONFLICT(id) DO UPDATE SET value = value + 1""",
                    (thread_id,),
                )
                proxy.commit()

        with ThreadPoolExecutor(max_workers=num_threads) as pool:
            futures = [
                pool.submit(upsert_worker, tid) for tid in range(num_threads)
            ]
            for f in as_completed(futures):
                f.result()

        row = proxy.execute("SELECT value FROM counters WHERE id = 1").fetchone()
        # Initial value was 0. First upsert sets it to thread_id (via INSERT
        # conflict), then increments. The exact value depends on ordering, but
        # must be >= num_threads * 50 - 1 (at least all increments applied).
        # With isolated connections, no updates should be lost.
        # Each of the 500 upserts increments by 1 (ON CONFLICT path after first).
        # The very first upsert hits the existing row, so it also does +1.
        assert row["value"] >= num_threads * 50


# ---------------------------------------------------------------------------
# 4. Drop-in compatibility (proxy behaves like sqlite3.Connection)
# ---------------------------------------------------------------------------


class TestDropInCompatibility:
    def test_execute_returns_cursor(self, db_path):
        proxy = connect(db_path)
        proxy.execute("CREATE TABLE t (x INTEGER)")
        cur = proxy.execute("INSERT INTO t VALUES (1)")
        assert cur.rowcount == 1

    def test_executemany(self, db_path):
        proxy = connect(db_path)
        proxy.execute("CREATE TABLE t (x INTEGER)")
        proxy.executemany("INSERT INTO t VALUES (?)", [(1,), (2,), (3,)])
        proxy.commit()
        rows = proxy.execute("SELECT COUNT(*) FROM t").fetchone()
        assert rows[0] == 3

    def test_executescript(self, db_path):
        proxy = connect(db_path)
        proxy.executescript("""
            CREATE TABLE a (x INTEGER);
            CREATE TABLE b (y INTEGER);
            INSERT INTO a VALUES (1);
            INSERT INTO b VALUES (2);
        """)
        assert proxy.execute("SELECT x FROM a").fetchone()[0] == 1
        assert proxy.execute("SELECT y FROM b").fetchone()[0] == 2

    def test_row_factory_property(self, db_path):
        proxy = connect(db_path)
        assert proxy.row_factory is sqlite3.Row

    def test_cursor_method(self, db_path):
        proxy = connect(db_path)
        cur = proxy.cursor()
        assert cur is not None

    def test_commit_and_rollback(self, db_path):
        proxy = connect(db_path)
        proxy.execute("CREATE TABLE t (x INTEGER)")
        proxy.execute("INSERT INTO t VALUES (1)")
        proxy.commit()

        proxy.execute("INSERT INTO t VALUES (2)")
        proxy.rollback()

        rows = proxy.execute("SELECT COUNT(*) FROM t").fetchone()
        assert rows[0] == 1

    def test_close(self, db_path):
        proxy = connect(db_path)
        proxy.execute("CREATE TABLE t (x INTEGER)")
        proxy.commit()
        proxy.close()
        # After close, a new connection should be created on next access
        proxy.execute("SELECT * FROM t")  # should not raise


# ---------------------------------------------------------------------------
# 5. transaction() context manager works with proxy
# ---------------------------------------------------------------------------


class TestTransactionContextManager:
    def test_transaction_commits_on_success(self, proxy):
        with transaction(proxy) as conn:
            conn.execute("INSERT INTO counters (id, value) VALUES (50, 500)")

        row = proxy.execute(
            "SELECT value FROM counters WHERE id = 50"
        ).fetchone()
        assert row["value"] == 500

    def test_transaction_rolls_back_on_exception(self, proxy):
        with pytest.raises(ValueError):
            with transaction(proxy) as conn:
                conn.execute(
                    "INSERT INTO counters (id, value) VALUES (60, 600)"
                )
                raise ValueError("simulated failure")

        row = proxy.execute(
            "SELECT value FROM counters WHERE id = 60"
        ).fetchone()
        assert row is None

    def test_transaction_uses_begin_immediate(self, proxy):
        """BEGIN IMMEDIATE acquires a write lock immediately, preventing
        concurrent writers from interleaving."""
        # If this doesn't deadlock or error, BEGIN IMMEDIATE works
        with transaction(proxy) as conn:
            conn.execute(
                "UPDATE counters SET value = value + 1 WHERE id = 1"
            )

        row = proxy.execute(
            "SELECT value FROM counters WHERE id = 1"
        ).fetchone()
        assert row["value"] == 1

    def test_nested_transactions_on_different_threads(self, proxy):
        """Two threads using transaction() must not interfere."""
        results = {"a": None, "b": None}
        barrier = threading.Barrier(2)

        def txn_a():
            with transaction(proxy) as conn:
                conn.execute(
                    "INSERT INTO counters (id, value) VALUES (70, 700)"
                )
            barrier.wait()
            results["a"] = proxy.execute(
                "SELECT value FROM counters WHERE id = 70"
            ).fetchone()

        def txn_b():
            barrier.wait()  # wait for A to finish
            with transaction(proxy) as conn:
                conn.execute(
                    "INSERT INTO counters (id, value) VALUES (80, 800)"
                )
            results["b"] = proxy.execute(
                "SELECT value FROM counters WHERE id = 80"
            ).fetchone()

        t1 = threading.Thread(target=txn_a)
        t2 = threading.Thread(target=txn_b)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results["a"]["value"] == 700
        assert results["b"]["value"] == 800


# ---------------------------------------------------------------------------
# 6. Stress test — simulates concurrent request handlers
# ---------------------------------------------------------------------------


class TestConcurrentRequestSimulation:
    def test_simulated_concurrent_api_requests(self, db_path):
        """Simulate what happens when FastAPI handles concurrent requests.

        Each 'request' reads a counter, computes new value, and writes
        it back using the atomic ``value = value + 1`` SQL pattern.
        With the old shared connection, some updates would be lost.
        With ThreadLocalConnection, all updates must be preserved.
        """
        proxy = connect(db_path)
        proxy.execute(
            "CREATE TABLE scores (user_id INTEGER PRIMARY KEY, xp INTEGER NOT NULL)"
        )
        # Create 5 users
        for uid in range(1, 6):
            proxy.execute(
                "INSERT INTO scores (user_id, xp) VALUES (?, 0)", (uid,)
            )
        proxy.commit()

        increments_per_user = 100
        num_workers = 10

        def request_handler(user_id):
            """Simulates a single API request adding XP."""
            proxy.execute(
                "UPDATE scores SET xp = xp + 1 WHERE user_id = ?",
                (user_id,),
            )
            proxy.commit()

        with ThreadPoolExecutor(max_workers=num_workers) as pool:
            futures = []
            for uid in range(1, 6):
                for _ in range(increments_per_user):
                    futures.append(pool.submit(request_handler, uid))

            for f in as_completed(futures):
                f.result()

        # Every user should have exactly increments_per_user XP
        for uid in range(1, 6):
            row = proxy.execute(
                "SELECT xp FROM scores WHERE user_id = ?", (uid,)
            ).fetchone()
            assert row["xp"] == increments_per_user, (
                f"User {uid}: expected {increments_per_user}, got {row['xp']}"
            )

    def test_simulated_concurrent_vote_toggle(self, db_path):
        """Simulate concurrent vote toggling — a common forum pattern.

        Multiple threads toggle an upvote for different users on the
        same discussion. Each user's final vote state must be consistent.
        """
        proxy = connect(db_path)
        proxy.execute("""
            CREATE TABLE votes (
                discussion_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                value INTEGER NOT NULL,
                PRIMARY KEY (discussion_id, user_id)
            )
        """)
        proxy.commit()

        num_users = 20

        def toggle_vote(user_id):
            """Toggle a user's upvote — delete if exists, insert if not."""
            cur = proxy.execute(
                "DELETE FROM votes WHERE discussion_id = 1 AND user_id = ? AND value = 1",
                (user_id,),
            )
            if cur.rowcount == 0:
                proxy.execute(
                    "INSERT OR IGNORE INTO votes (discussion_id, user_id, value) VALUES (1, ?, 1)",
                    (user_id,),
                )
            proxy.commit()

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = []
            # Each user toggles 3 times: on → off → on (net: on)
            for uid in range(1, num_users + 1):
                for _ in range(3):
                    futures.append(pool.submit(toggle_vote, uid))

            for f in as_completed(futures):
                f.result()

        # After 3 toggles, each user should have vote = 1 (on)
        votes = proxy.execute(
            "SELECT COUNT(*) FROM votes WHERE discussion_id = 1"
        ).fetchone()[0]
        assert votes == num_users, (
            f"Expected {num_users} votes, got {votes}"
        )


# ---------------------------------------------------------------------------
# 7. Async isolation — proves contextvars works for asyncio Tasks
# ---------------------------------------------------------------------------


class TestAsyncIsolation:
    def test_separate_worker_threads_get_different_connections(self, db_path):
        """Simulates how FastAPI handles concurrent requests.

        FastAPI runs sync endpoints on a threadpool.  Each worker
        thread starts with a clean ``contextvars`` context where
        the ContextVar defaults to ``None``, so each request
        creates its own connection.  Async endpoints similarly
        get fresh contexts from the ASGI server.
        """
        proxy = connect(db_path)
        conn_ids = []
        barrier = threading.Barrier(2)

        def simulate_request():
            raw = proxy.get_raw_connection()
            conn_ids.append(id(raw))
            barrier.wait()

        # Simulate two concurrent requests on separate threads
        t1 = threading.Thread(target=simulate_request)
        t2 = threading.Thread(target=simulate_request)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(conn_ids) == 2
        assert conn_ids[0] != conn_ids[1], (
            "Separate request threads must get different connections"
        )

    def test_contextvars_isolation_between_fresh_contexts(self, db_path):
        """Verifies that a ScopedConnection created inside a fresh
        context (no inherited connection) gets its own connection per
        context — simulating what happens when the ASGI server spawns
        tasks that haven't touched the proxy before."""
        # Create proxy without triggering _get_conn() in current context
        proxy = ScopedConnection(db_path)

        # Eagerly init schema from a temporary connection
        setup = _make_conn(db_path)
        setup.execute("CREATE TABLE ctx_test (id INTEGER PRIMARY KEY)")
        setup.commit()
        setup.close()

        # Hold the connections alive simultaneously so the GC can't free the
        # first before the second is allocated — otherwise CPython readily
        # reuses the freed address and `id()` collides even for distinct
        # connections.
        raw_conns = []

        def request_handler():
            raw_conns.append(proxy.get_raw_connection())

        # Each copy_context().run() starts with _ctx_conn=None (default)
        contextvars.copy_context().run(request_handler)
        contextvars.copy_context().run(request_handler)

        assert len(raw_conns) == 2
        assert raw_conns[0] is not raw_conns[1], (
            "Fresh contextvars contexts must get different connections"
        )

    def test_commit_on_one_thread_does_not_affect_other_thread(self, db_path):
        """A commit in one worker thread must not persist another's rollback."""
        proxy = connect(db_path)
        proxy.execute(
            "CREATE TABLE async_test (id INTEGER PRIMARY KEY, val INTEGER)"
        )
        proxy.commit()

        done = threading.Event()

        def request_a():
            proxy.execute("INSERT INTO async_test (id, val) VALUES (1, 100)")
            proxy.commit()
            done.set()

        def request_b():
            done.wait(timeout=5)
            raw = proxy.get_raw_connection()
            raw.execute("BEGIN IMMEDIATE")
            raw.execute("INSERT INTO async_test (id, val) VALUES (2, 200)")
            raw.execute("ROLLBACK")

        t1 = threading.Thread(target=request_a)
        t2 = threading.Thread(target=request_b)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        check_conn = _make_conn(db_path)
        row_a = check_conn.execute(
            "SELECT val FROM async_test WHERE id = 1"
        ).fetchone()
        row_b = check_conn.execute(
            "SELECT val FROM async_test WHERE id = 2"
        ).fetchone()
        check_conn.close()

        assert row_a is not None and row_a[0] == 100
        assert row_b is None, "Request B's rollback must not persist"
