import sqlite3
import pytest
from datetime import datetime, timezone

from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.DomainLayer.SolveAttempt import SolveAttempt


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    return c


@pytest.fixture
def repo(conn):
    return SolveRepo(conn)


def make_attempt(puzzle_id: int = 1, user_id: int = 2, circuit_id=None):
    started = datetime.now(timezone.utc)

    # prefer from_dict if exists
    if hasattr(SolveAttempt, "from_dict"):
        return SolveAttempt.from_dict({
            "id": 1,
            "puzzle_id": int(puzzle_id),
            "user_id": int(user_id),
            "circuit_id": circuit_id,
            "started_at": started.isoformat(),
            "submitted_at": None,
            "passed": None,
            "fail_reason": None,
        })

    return SolveAttempt(
        id=1,
        puzzle_id=int(puzzle_id),
        user_id=int(user_id),
        circuit_id=circuit_id,
        started_at=started,
    )


def test_schema_created(conn, repo):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='solve_attempts'"
    ).fetchone()
    assert row is not None


def test_get_open_attempt_none_branch(repo):
    assert repo.get_open_attempt(user_id=1, puzzle_id=1) is None


def test_create_attempt_passed_none_persists_as_null(conn, repo):
    a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    assert a.id > 0

    # open attempt exists
    open_a = repo.get_open_attempt(user_id=2, puzzle_id=1)
    assert open_a is not None
    assert open_a.passed is None  # should remain None until submitted

    # DB-level assert passed is NULL
    row = conn.execute("SELECT passed FROM solve_attempts WHERE id=?", (a.id,)).fetchone()
    assert row is not None
    assert row["passed"] is None


def test_update_attempt_failed_writes_passed_0_and_fail_reason(conn, repo):
    a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    a.mark_submitted(passed=False, circuit_id=99, fail_reason="wrong output")
    repo.update_attempt(a)

    # no open attempt after submitted
    assert repo.get_open_attempt(user_id=2, puzzle_id=1) is None
    assert repo.has_passed(user_id=2, puzzle_id=1) is False

    # DB asserts: passed=0, fail_reason stored, submitted_at NOT NULL
    row = conn.execute("SELECT passed, fail_reason, submitted_at FROM solve_attempts WHERE id=?", (a.id,)).fetchone()
    assert row is not None
    assert int(row["passed"]) == 0
    assert row["fail_reason"] == "wrong output"
    assert row["submitted_at"] is not None


def test_update_attempt_success_has_passed_true(conn, repo):
    a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    a.mark_submitted(passed=True, circuit_id=77)
    repo.update_attempt(a)

    assert repo.has_passed(user_id=2, puzzle_id=1) is True

    row = conn.execute("SELECT passed FROM solve_attempts WHERE id=?", (a.id,)).fetchone()
    assert row is not None
    assert int(row["passed"]) == 1


def test_open_attempt_returns_latest(repo):
    a1 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    a2 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    open_a = repo.get_open_attempt(user_id=2, puzzle_id=1)
    assert open_a is not None
    assert open_a.id == a2.id


def test_has_passed_before_attempt_false_then_true(repo):
    # attempt #1 open (not passed)
    a1 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    assert repo.has_passed_before_attempt(user_id=2, puzzle_id=1, attempt_id=a1.id) is False

    # attempt #1 becomes passed
    a1.mark_submitted(passed=True, circuit_id=10)
    repo.update_attempt(a1)

    # attempt #2 open => should see previous pass
    a2 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    assert repo.has_passed_before_attempt(user_id=2, puzzle_id=1, attempt_id=a2.id) is True


def test_first_attempt_started_at_none_then_value(repo):
    assert repo.first_attempt_started_at(user_id=9, puzzle_id=9) is None

    a1 = repo.create_attempt(make_attempt(puzzle_id=9, user_id=9))
    a2 = repo.create_attempt(make_attempt(puzzle_id=9, user_id=9))

    ts = repo.first_attempt_started_at(user_id=9, puzzle_id=9)
    assert ts is not None
    assert isinstance(ts, str)
