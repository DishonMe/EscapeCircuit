import sqlite3
import pytest
from datetime import datetime, timezone

from Backend.PersistantLayer.RatingRepo import RatingRepo
from Backend.DomainLayer.Rating import Rating


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    return c


@pytest.fixture
def repo(conn):
    return RatingRepo(conn)


def make_rating(puzzle_id: int, user_id: int, difficulty=3, fun=4, clearness=5, exp=False):
    created_at = datetime.now(timezone.utc)

    if hasattr(Rating, "from_dict"):
        return Rating.from_dict({
            "id": 1,
            "puzzle_id": int(puzzle_id),
            "user_id": int(user_id),
            "difficulty": int(difficulty),
            "fun": int(fun),
            "clearness": int(clearness),
            "created_at": created_at.isoformat(),
            "is_experienced_at_rating": bool(exp),
        })

    return Rating(
        id=1,
        puzzle_id=int(puzzle_id),
        user_id=int(user_id),
        difficulty=int(difficulty),
        fun=int(fun),
        clearness=int(clearness),
        created_at=created_at,
        is_experienced_at_rating=bool(exp),
    )


def test_schema_created(conn, repo):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ratings'"
    ).fetchone()
    assert row is not None


def test_get_by_puzzle_user_none_branch(repo):
    assert repo.get_by_puzzle_user(1, 1) is None


def test_upsert_insert_then_get_roundtrip(conn, repo):
    r = repo.upsert(make_rating(1, 2, difficulty=2, fun=3, clearness=4, exp=False))
    assert r.id > 0

    got = repo.get_by_puzzle_user(1, 2)
    assert got is not None
    assert got.difficulty == 2
    assert got.fun == 3
    assert got.clearness == 4
    assert got.is_experienced_at_rating is False

    # DB assert bool stored as 0
    row = conn.execute("SELECT is_experienced_at_rating FROM ratings WHERE id=?", (r.id,)).fetchone()
    assert row is not None
    assert int(row["is_experienced_at_rating"]) == 0


def test_upsert_update_branch_overwrites_fields(conn, repo):
    r1 = repo.upsert(make_rating(1, 2, difficulty=1, fun=1, clearness=1, exp=False))
    r2 = repo.upsert(make_rating(1, 2, difficulty=5, fun=4, clearness=3, exp=True))

    # same logical row, id must stay same (update branch)
    assert r2.id == r1.id

    got = repo.get_by_puzzle_user(1, 2)
    assert got is not None
    assert got.difficulty == 5
    assert got.fun == 4
    assert got.clearness == 3
    assert got.is_experienced_at_rating is True

    # DB assert bool stored as 1
    row = conn.execute("SELECT is_experienced_at_rating FROM ratings WHERE id=?", (r2.id,)).fetchone()
    assert row is not None
    assert int(row["is_experienced_at_rating"]) == 1


def test_unique_constraint_enforced_by_upsert_logic(repo):
    # upsert should not raise IntegrityError; it updates
    repo.upsert(make_rating(10, 20))
    repo.upsert(make_rating(10, 20, difficulty=4))  # should update, not insert a new row

    lst = repo.list_by_puzzle(10)
    assert len(lst) == 1
    assert lst[0].user_id == 20


def test_list_by_puzzle_empty_then_ordered(repo):
    assert repo.list_by_puzzle(999) == []

    # insert 3 ratings for same puzzle
    r1 = repo.upsert(make_rating(7, 1, difficulty=1))
    r2 = repo.upsert(make_rating(7, 2, difficulty=2))
    r3 = repo.upsert(make_rating(7, 3, difficulty=3))

    lst = repo.list_by_puzzle(7)
    assert len(lst) == 3
    ids = [r.id for r in lst]
    assert ids == sorted(ids)  # ORDER BY id ASC

    user_ids = {r.user_id for r in lst}
    assert user_ids == {1, 2, 3}
