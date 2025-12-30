import sqlite3
import pytest
from datetime import datetime, timezone

from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.DomainLayer.Puzzle import Puzzle
from Backend.DomainLayer.PuzzleTestCase import PuzzleTestCase
from Backend.DomainLayer.Enums import PuzzleStatus, GateType, TestCaseKind


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    return c


@pytest.fixture
def repo(conn):
    return PuzzleRepo(conn)


def make_puzzle(
    name: str,
    creator_user_id: int = 1,
    status: PuzzleStatus = PuzzleStatus.DRAFT,
    budget: int = 10,
    time_limit_seconds: int | None = 30,
    default_gates=None,
    rating_count: int = 0,
    avg_difficulty: float = 0.0,
    avg_fun: float = 0.0,
    avg_clearness: float = 0.0,
):
    default_gates = default_gates or {GateType.AND, GateType.OR}
    created_at = datetime.now(timezone.utc)

    # Prefer from_dict if exists
    if hasattr(Puzzle, "from_dict"):
        # from_dict in your repo is used with "status": row["status"] (string)
        # and default_gate_set: list of gate values (strings)
        return Puzzle.from_dict({
            "id": 1,
            "name": name,
            "creator_user_id": int(creator_user_id),
            "description": "desc",
            "status": status.value,
            "budget": int(budget),
            "time_limit_seconds": time_limit_seconds,
            "default_gate_set": [g.value for g in default_gates],
            "rating_count": int(rating_count),
            "avg_difficulty": float(avg_difficulty),
            "avg_fun": float(avg_fun),
            "avg_clearness": float(avg_clearness),
            "created_at": created_at.isoformat(),
        })

    # Fallback constructor
    return Puzzle(
        id=1,
        name=name,
        creator_user_id=int(creator_user_id),
        description="desc",
        status=status,
        budget=int(budget),
        time_limit_seconds=time_limit_seconds,
        default_gate_set=set(default_gates),
        rating_count=int(rating_count),
        avg_difficulty=float(avg_difficulty),
        avg_fun=float(avg_fun),
        avg_clearness=float(avg_clearness),
        created_at=created_at,
    )


def make_testcase(puzzle_id: int, kind=TestCaseKind.BLACKBOX, a=1, out=0):
    created_at = datetime.now(timezone.utc)
    if hasattr(PuzzleTestCase, "from_dict"):
        return PuzzleTestCase.from_dict({
            "id": 1,
            "puzzle_id": int(puzzle_id),
            "kind": kind.value,
            "inputs": {"a": a},
            "expected_outputs": {"out": out},
            "created_at": created_at.isoformat(),
        })
    return PuzzleTestCase(
        id=1,
        puzzle_id=int(puzzle_id),
        kind=kind,
        inputs={"a": a},
        expected_outputs={"out": out},
        created_at=created_at,
    )


def test_schema_created(conn, repo):
    for t in ("puzzles", "puzzle_test_cases"):
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (t,),
        ).fetchone()
        assert row is not None


def test_get_by_id_none_branch(repo):
    assert repo.get_by_id(999999) is None


def test_create_get_roundtrip(repo):
    p = make_puzzle("P1", creator_user_id=11, status=PuzzleStatus.DRAFT)
    created = repo.create(p)
    assert created.id > 0

    got = repo.get_by_id(created.id)
    assert got is not None
    assert got.id == created.id
    assert got.name == "P1"
    assert got.creator_user_id == 11
    assert got.status == PuzzleStatus.DRAFT


def test_unique_puzzle_name_constraint(repo):
    repo.create(make_puzzle("UniqueName"))
    with pytest.raises(sqlite3.IntegrityError):
        repo.create(make_puzzle("UniqueName"))


def test_update_persists_all_casts(repo):
    p = repo.create(make_puzzle("ToUpdate", creator_user_id=1, status=PuzzleStatus.DRAFT))
    # mutate all fields touched by UPDATE statement + float casts
    p.name = "UpdatedName"
    p.creator_user_id = 99
    p.description = "new desc"
    p.status = PuzzleStatus.PUBLISHED
    p.budget = 123
    p.time_limit_seconds = None
    p.default_gate_set = {GateType.NOT}
    p.rating_count = 7
    p.avg_difficulty = 3.25
    p.avg_fun = 4.5
    p.avg_clearness = 1.75

    repo.update(p)

    got = repo.get_by_id(p.id)
    assert got is not None
    assert got.name == "UpdatedName"
    assert got.creator_user_id == 99
    assert got.description == "new desc"
    assert got.status == PuzzleStatus.PUBLISHED
    assert got.budget == 123
    assert got.time_limit_seconds is None
    assert {g.value for g in got.default_gate_set} == {GateType.NOT.value}
    assert got.rating_count == 7
    assert abs(got.avg_difficulty - 3.25) < 1e-9
    assert abs(got.avg_fun - 4.5) < 1e-9
    assert abs(got.avg_clearness - 1.75) < 1e-9


def test_list_published_filters_and_pagination(repo):
    # create 3 published + 1 draft
    d = repo.create(make_puzzle("DraftOne", status=PuzzleStatus.DRAFT))
    p1 = repo.create(make_puzzle("Pub1", status=PuzzleStatus.PUBLISHED))
    p2 = repo.create(make_puzzle("Pub2", status=PuzzleStatus.PUBLISHED))
    p3 = repo.create(make_puzzle("Pub3", status=PuzzleStatus.PUBLISHED))

    published_all = repo.list_published(limit=50, offset=0)
    names = [x.name for x in published_all]
    assert "DraftOne" not in names
    assert set(names) >= {"Pub1", "Pub2", "Pub3"}

    # ORDER BY id DESC, then pagination
    published_page = repo.list_published(limit=1, offset=1)
    assert len(published_page) == 1
    # second item in DESC order:
    ordered = sorted([p1, p2, p3], key=lambda x: x.id, reverse=True)
    assert published_page[0].id == ordered[1].id


def test_search_by_name_covers_both_branches(repo):
    # published and draft with same keyword
    repo.create(make_puzzle("Alpha Draft", status=PuzzleStatus.DRAFT))
    repo.create(make_puzzle("Alpha Published", status=PuzzleStatus.PUBLISHED))
    repo.create(make_puzzle("Beta Published", status=PuzzleStatus.PUBLISHED))

    only_pub = repo.search_by_name("Alpha", only_published=True, limit=50)
    assert {p.name for p in only_pub} == {"Alpha Published"}

    include_all = repo.search_by_name("Alpha", only_published=False, limit=50)
    assert {p.name for p in include_all} == {"Alpha Draft", "Alpha Published"}


def test_add_list_test_cases_roundtrip_and_empty(repo):
    p = repo.create(make_puzzle("WithTC", status=PuzzleStatus.PUBLISHED))
    assert repo.list_test_cases(p.id) == []

    tc1 = repo.add_test_case(make_testcase(p.id, a=0, out=0))
    tc2 = repo.add_test_case(make_testcase(p.id, a=1, out=1))
    assert tc1.id > 0 and tc2.id > 0

    tcs = repo.list_test_cases(p.id)
    assert len(tcs) == 2
    # ORDER BY id ASC, so inputs a should appear as 1 then 2
    assert [tc.inputs["a"] for tc in tcs] == [0, 1]
    assert tcs[0].expected_outputs == {"out": 0}
    assert tcs[1].expected_outputs == {"out": 1}


def test_testcase_cascade_delete(conn, repo):
    p = repo.create(make_puzzle("CascadePuzzle", status=PuzzleStatus.PUBLISHED))
    repo.add_test_case(make_testcase(p.id, a=1, out=1))
    assert len(repo.list_test_cases(p.id)) == 1

    # delete puzzle row -> ON DELETE CASCADE
    conn.execute("DELETE FROM puzzles WHERE id=?", (p.id,))
    assert repo.list_test_cases(p.id) == []
