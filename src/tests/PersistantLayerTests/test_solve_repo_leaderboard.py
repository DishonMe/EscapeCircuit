"""
Unit tests for the per-puzzle leaderboard queries on SolveRepo.

Fulfils the "Leaderboard" unit-test rows promised in ADD Chapter 7.2.2
(Experience (XP) and Rewards Calculation), which name SolveRepo.py as the
target module:

    • "Leaderboard sorted by fastest time"   → get_leaderboard ordered by time ASC
    • "Leaderboard sorted by lowest cost"     → get_leaderboard_by_cost ordered by cost ASC
    • "Leaderboard respects passed=1 filter"  → failed attempts excluded
    • "Leaderboard immediate update"          → a just-saved solve appears, ranked

These run directly against an in-memory SQLite database (no API), per the
AAA (Arrange, Act, Assert) pattern described in ADD 7.2.
"""
import sqlite3
import pytest

from Backend.PersistantLayer.SolveRepo import SolveRepo


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    return c


@pytest.fixture
def repo(conn):
    r = SolveRepo(conn)
    # The leaderboard JOINs the users table for usernames.
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT)")
    for uid, name in [(1, "alice"), (2, "bob"), (3, "carol")]:
        conn.execute("INSERT INTO users(id, username) VALUES(?, ?)", (uid, name))
    return r


PUZZLE_ID = 1


def test_leaderboard_sorted_by_fastest_time(repo):
    """ADD 7.2.2 — 3 passed solves with times 120/90/150 → ranked 90,120,150."""
    repo.add_solve(user_id=1, puzzle_id=PUZZLE_ID, time_taken_seconds=120, xp_earned=10)
    repo.add_solve(user_id=2, puzzle_id=PUZZLE_ID, time_taken_seconds=90, xp_earned=10)
    repo.add_solve(user_id=3, puzzle_id=PUZZLE_ID, time_taken_seconds=150, xp_earned=10)

    board = repo.get_leaderboard(PUZZLE_ID, 50)

    assert [e["rank"] for e in board] == [1, 2, 3]
    assert [e["best_time"] for e in board] == [90, 120, 150]
    assert [e["username"] for e in board] == ["bob", "alice", "carol"]


def test_leaderboard_sorted_by_lowest_cost(repo):
    """ADD 7.2.2 — 3 passed solves with costs 20/10/15 → ranked 10,15,20."""
    repo.add_solve(user_id=1, puzzle_id=PUZZLE_ID, time_taken_seconds=100, xp_earned=10, cost_used=20)
    repo.add_solve(user_id=2, puzzle_id=PUZZLE_ID, time_taken_seconds=100, xp_earned=10, cost_used=10)
    repo.add_solve(user_id=3, puzzle_id=PUZZLE_ID, time_taken_seconds=100, xp_earned=10, cost_used=15)

    board = repo.get_leaderboard_by_cost(PUZZLE_ID, 50)

    assert [e["rank"] for e in board] == [1, 2, 3]
    assert [e["best_cost"] for e in board] == [10, 15, 20]


def test_leaderboard_respects_passed_filter(repo, conn):
    """ADD 7.2.2 — a faster *failed* attempt must NOT appear on the leaderboard;
    only the passed attempt is returned."""
    # Passed attempt at 120s.
    repo.add_solve(user_id=1, puzzle_id=PUZZLE_ID, time_taken_seconds=120, xp_earned=10)
    # Faster *failed* attempt at 90s (passed=0) — must be excluded.
    conn.execute(
        """INSERT INTO solve_attempts(puzzle_id, user_id, started_at, submitted_at,
                                      passed, time_used_seconds, time_taken_seconds, xp_earned)
           VALUES(?,?,datetime('now'),datetime('now'),0,90,90,0)""",
        (PUZZLE_ID, 2),
    )

    board = repo.get_leaderboard(PUZZLE_ID, 50)

    assert len(board) == 1
    assert board[0]["user_id"] == 1
    assert board[0]["best_time"] == 120


def test_leaderboard_immediate_update(repo):
    """ADD 7.2.2 — a solve saved to the DB is present in the leaderboard
    immediately and ranked correctly."""
    repo.add_solve(user_id=1, puzzle_id=PUZZLE_ID, time_taken_seconds=50, xp_earned=10)

    board = repo.get_leaderboard(PUZZLE_ID, 50)

    assert any(e["user_id"] == 1 and e["best_time"] == 50 for e in board)
    assert board[0]["rank"] == 1
