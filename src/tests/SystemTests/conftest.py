"""
Shared fixtures for system tests.

System tests exercise complete multi-step user workflows that span multiple
API endpoints.  They reuse the same in-memory wiring as integration tests
but add higher-level helper functions for common multi-step operations.
"""
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient

# Re-use the full app wiring from integration tests
from tests.IntegrationTests.conftest import (
    _build_test_app,
    register_user,
    register_and_login,
    auth_header,
)


class _SafeCommitConnection:
    """Thin wrapper around sqlite3.Connection that suppresses stray
    ``conn.commit()`` / ``conn.rollback()`` calls that happen *inside*
    an explicit ``BEGIN IMMEDIATE … COMMIT`` block managed by
    ``_db.transaction()``.

    The ``_db.transaction()`` context manager communicates via
    ``raw.execute("BEGIN IMMEDIATE;")``, ``raw.execute("COMMIT;")``, and
    ``raw.execute("ROLLBACK;")``.  We track these to know when we are in a
    managed transaction and absorb any intermediate ``commit()`` calls from
    repo code (e.g. ``SolveRepo.try_award_creator_solve_xp``).
    """

    def __init__(self, real: sqlite3.Connection):
        object.__setattr__(self, "_real", real)
        object.__setattr__(self, "_managed_txn", False)

    # ---- intercept execute to track managed transactions ----
    def execute(self, sql, parameters=()):
        real = object.__getattribute__(self, "_real")
        sql_upper = sql.strip().upper() if isinstance(sql, str) else ""
        if sql_upper.startswith("BEGIN"):
            object.__setattr__(self, "_managed_txn", True)
        elif sql_upper.startswith(("COMMIT", "ROLLBACK")):
            # Only the transaction manager sends COMMIT/ROLLBACK via execute()
            object.__setattr__(self, "_managed_txn", False)
        return real.execute(sql, parameters)

    # ---- suppress commit/rollback during managed transactions ----
    def commit(self):
        if object.__getattribute__(self, "_managed_txn"):
            return  # silently skip — transaction manager will handle it
        real = object.__getattribute__(self, "_real")
        if real.in_transaction:
            real.commit()

    def rollback(self):
        if object.__getattribute__(self, "_managed_txn"):
            return
        real = object.__getattribute__(self, "_real")
        if real.in_transaction:
            real.rollback()

    # ---- proxy everything else to the real connection ----
    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_real"), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_real"), name, value)

    def executemany(self, sql, seq_of_parameters):
        return object.__getattribute__(self, "_real").executemany(sql, seq_of_parameters)

    def executescript(self, sql_script):
        return object.__getattribute__(self, "_real").executescript(sql_script)

    def cursor(self):
        return object.__getattribute__(self, "_real").cursor()

    def close(self):
        object.__getattribute__(self, "_real").close()

    @property
    def row_factory(self):
        return object.__getattribute__(self, "_real").row_factory

    @row_factory.setter
    def row_factory(self, value):
        object.__getattribute__(self, "_real").row_factory = value

    @property
    def isolation_level(self):
        return object.__getattribute__(self, "_real").isolation_level

    @isolation_level.setter
    def isolation_level(self, value):
        object.__getattribute__(self, "_real").isolation_level = value

    @property
    def in_transaction(self):
        return object.__getattribute__(self, "_real").in_transaction


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:", check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    c.execute("PRAGMA foreign_keys = ON;")
    wrapped = _SafeCommitConnection(c)
    yield wrapped
    c.close()


@pytest.fixture()
def app(conn):
    return _build_test_app(conn)


@pytest.fixture()
def client(app):
    return TestClient(app)


# ── Workflow helpers ────────────────────────────────────────────────────────

def make_creator(client, conn, username="creator"):
    """Register a user, promote to creator via DB, return token."""
    token = register_and_login(client, username)
    me = client.get("/users/me", headers=auth_header(token)).json()
    conn.execute("UPDATE users SET role = 'creator' WHERE id = ?", (me["id"],))
    return token


def make_admin(client, conn, username="admin"):
    """Register a user, promote to admin via DB, return token."""
    token = register_and_login(client, username)
    me = client.get("/users/me", headers=auth_header(token)).json()
    conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (me["id"],))
    return token


def get_user_xp(client, token):
    """Return the current XP for the authenticated user."""
    me = client.get("/users/me", headers=auth_header(token)).json()
    return me.get("xp", 0)


def get_user_info(client, token):
    """Return full user info dict."""
    return client.get("/users/me", headers=auth_header(token)).json()


def create_puzzle(client, token, name="Test Puzzle", budget=100,
                  time_limit=None, difficulty="EASY"):
    """Create a puzzle and return the response dict."""
    payload = {
        "name": name,
        "description": "A test puzzle",
        "budget": budget,
        "default_gate_set": ["AND", "OR", "NOT"],
        "difficulty": difficulty,
    }
    if time_limit is not None:
        payload["time_limit_seconds"] = time_limit
    resp = client.post("/puzzles", json=payload, headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def add_blackbox_test_case(client, token, puzzle_id, inputs, expected_outputs):
    """Add a blackbox test case to a puzzle."""
    resp = client.post(f"/puzzles/{puzzle_id}/testcases", json={
        "kind": "blackbox",
        "inputs": inputs,
        "expected_outputs": expected_outputs,
    }, headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _and_solution(input_a="A", input_b="B", output_name="out"):
    """
    Build a minimal AND-gate circuit solution that the logic engine can
    evaluate.  Returns the solution dict expected by POST /validate.
    """
    return {
        "placedComponents": [
            {"id": "and1", "componentId": "AND"},
        ],
        "wires": [
            {"from": {"componentId": f"IO:IN:{input_a}", "pinIndex": 0},
             "to":   {"componentId": "and1", "pinIndex": 0}},
            {"from": {"componentId": f"IO:IN:{input_b}", "pinIndex": 0},
             "to":   {"componentId": "and1", "pinIndex": 1}},
            {"from": {"componentId": "and1", "pinIndex": 2},
             "to":   {"componentId": f"IO:OUT:{output_name}", "pinIndex": 0}},
        ],
        "totalCost": 1,
    }


def validate_solution(client, token, puzzle_id, solution, time_taken=0):
    """Submit a solution for validation. Returns the response dict."""
    resp = client.post(f"/puzzles/{puzzle_id}/validate", json={
        "solution": solution,
        "time_taken": time_taken,
    }, headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def create_and_publish_puzzle(client, conn, creator_token, name="Pub Puzzle",
                              budget=100, time_limit=300, difficulty="EASY"):
    """
    Full workflow: create puzzle -> add AND-gate test cases -> creator self-solves
    -> publish.  Returns (puzzle_id, puzzle_dict).
    """
    puzzle = create_puzzle(client, creator_token, name=name, budget=budget,
                           time_limit=time_limit, difficulty=difficulty)
    pid = int(puzzle["id"])

    # Add two blackbox test cases for an AND gate
    add_blackbox_test_case(client, creator_token, pid,
                           {"A": 0, "B": 0}, {"out": 0})
    add_blackbox_test_case(client, creator_token, pid,
                           {"A": 1, "B": 1}, {"out": 1})

    # Creator must self-solve before publishing
    solution = _and_solution()
    result = validate_solution(client, creator_token, pid, solution,
                               time_taken=10)
    assert result["solved"] is True

    # Publish
    resp = client.post(f"/puzzles/{pid}/publish",
                       headers=auth_header(creator_token))
    assert resp.status_code == 200, resp.text

    return pid, puzzle
