import sqlite3
import contextvars
import threading
from contextlib import contextmanager
from typing import Iterator, Optional

from Backend import settings


def _make_conn(db_path: str) -> sqlite3.Connection:
    """Create and configure a single SQLite connection."""
    conn = sqlite3.connect(db_path, timeout=settings.DB_CONNECTION_TIMEOUT_S)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute(f"PRAGMA busy_timeout = {settings.DB_BUSY_TIMEOUT_MS};")
    return conn


class ScopedConnection:
    """A proxy that gives each execution context its own SQLite connection.

    Works correctly for **both** sync (threadpool) and async (event-loop)
    FastAPI endpoints:

    * **Sync ``def`` endpoints** — FastAPI dispatches these onto a
      threadpool.  Each thread gets its own ``contextvars`` copy,
      so each request gets its own connection.
    * **Async ``async def`` endpoints** — each incoming ASGI request
      creates its own context, so concurrent requests on the same
      event-loop thread still get isolated connections.

    Repos and services continue to use ``self.conn.execute(...)`` and
    ``self.conn.commit()`` unchanged.  This class proxies those calls
    to the context-local connection.

    Each ``ScopedConnection`` instance owns a private ``ContextVar``
    so that the connection is scoped to the current execution context
    (thread for sync, ASGI request scope for async).
    """

    # Class-level counter to ensure unique ContextVar names.
    _counter: int = 0

    def __init__(self, db_path: str) -> None:
        # Use object.__setattr__ because __setattr__ is overridden.
        ScopedConnection._counter += 1
        cvar = contextvars.ContextVar(
            f"_scoped_conn_{ScopedConnection._counter}", default=None
        )
        object.__setattr__(self, "_db_path", db_path)
        object.__setattr__(self, "_ctx_conn", cvar)

    # ---- connection lifecycle ----

    def _get_conn(self) -> sqlite3.Connection:
        """Return the connection for the current context, creating one
        if needed."""
        ctx_conn = object.__getattribute__(self, "_ctx_conn")
        conn = ctx_conn.get()
        if conn is None:
            db_path = object.__getattribute__(self, "_db_path")
            conn = _make_conn(db_path)
            ctx_conn.set(conn)
        return conn

    # ---- proxy behaviour ----

    def __getattr__(self, name: str):
        """Forward every attribute lookup to the context-local connection."""
        return getattr(self._get_conn(), name)

    def __setattr__(self, name: str, value):
        """Forward attribute writes (e.g. ``conn.row_factory = ...``)."""
        setattr(self._get_conn(), name, value)

    # ---- methods that repos call directly ----
    # Defined explicitly for performance and IDE support.

    def execute(self, sql, parameters=()):
        return self._get_conn().execute(sql, parameters)

    def executemany(self, sql, seq_of_parameters):
        return self._get_conn().executemany(sql, seq_of_parameters)

    def executescript(self, sql_script):
        return self._get_conn().executescript(sql_script)

    def commit(self):
        return self._get_conn().commit()

    def rollback(self):
        return self._get_conn().rollback()

    def close(self):
        ctx_conn = object.__getattribute__(self, "_ctx_conn")
        conn = ctx_conn.get()
        if conn is not None:
            conn.close()
            ctx_conn.set(None)

    def cursor(self):
        return self._get_conn().cursor()

    @property
    def isolation_level(self):
        return self._get_conn().isolation_level

    @isolation_level.setter
    def isolation_level(self, value):
        self._get_conn().isolation_level = value

    @property
    def row_factory(self):
        return self._get_conn().row_factory

    @row_factory.setter
    def row_factory(self, value):
        self._get_conn().row_factory = value

    @property
    def in_transaction(self):
        return self._get_conn().in_transaction

    # ---- helpers ----

    def get_raw_connection(self) -> sqlite3.Connection:
        """Return the actual underlying ``sqlite3.Connection`` for the
        current execution context.  Useful in tests and for the
        ``transaction`` context manager."""
        return self._get_conn()

    def close_all(self) -> None:
        """Best-effort close of the current context's connection."""
        self.close()


# Keep the old name as an alias so existing tests that import it
# still work.
ThreadLocalConnection = ScopedConnection


def connect(db_path: str) -> ScopedConnection:
    """Create a context-scoped connection proxy for *db_path*.

    Drop-in replacement for the old ``sqlite3.connect()`` call.  Every
    execution context (thread **or** asyncio Task) that touches the
    returned object gets its own ``sqlite3.Connection``.
    """
    proxy = ScopedConnection(db_path)
    # Eagerly create the connection for the *current* context (the
    # thread running ``create_app()``) so that ``_ensure_schema()``
    # calls in repo constructors work immediately.
    proxy._get_conn()
    return proxy


@contextmanager
def transaction(conn) -> Iterator[sqlite3.Connection]:
    """Execute a block inside an explicit ``BEGIN IMMEDIATE … COMMIT``.

    *conn* can be a real ``sqlite3.Connection`` **or** our
    ``ScopedConnection`` proxy — we extract the raw connection in the
    latter case so that ``BEGIN``/``COMMIT``/``ROLLBACK`` operate on
    the correct context-local connection.
    """
    raw: sqlite3.Connection
    if isinstance(conn, ScopedConnection):
        raw = conn.get_raw_connection()
    else:
        raw = conn

    try:
        raw.execute("BEGIN IMMEDIATE;")
        yield raw
        raw.execute("COMMIT;")
    except Exception:
        raw.execute("ROLLBACK;")
        raise
