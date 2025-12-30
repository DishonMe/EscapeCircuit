import sqlite3
import pytest
import json

from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.DomainLayer.Circuit import Circuit


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    return c


@pytest.fixture
def repo(conn):
    return CircuitRepo(conn)


def structure_json(tag="x"):
    return json.dumps({"tag": tag, "eval_map": {json.dumps({"a": 1}, sort_keys=True): {"out": 0}}})


def test_schema_created(conn, repo):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='circuits'"
    ).fetchone()
    assert row is not None


def test_get_by_id_missing_branch(repo):
    assert repo.get_by_id(999999) is None


def test_create_and_get_roundtrip(repo):
    c = Circuit(id=0, user_id=1, name="c1", cost=3, structure_json=structure_json("c1"))
    created = repo.create(c)
    assert created.id > 0

    got = repo.get_by_id(created.id)
    assert got is not None
    assert got.id == created.id
    assert got.user_id == 1
    assert got.name == "c1"
    assert got.cost == 3
    assert got.structure_json == c.structure_json


def test_list_by_user_empty(repo):
    assert repo.list_by_user(12345) == []


def test_list_by_user_order_desc(repo):
    ids = []
    for i in range(3):
        created = repo.create(Circuit(id=0, user_id=7, name=f"c{i}", cost=i, structure_json=structure_json(str(i))))
        ids.append(created.id)

    lst = repo.list_by_user(7)
    assert [x.id for x in lst] == sorted(ids, reverse=True)


def test_delete_success_and_false_branch(repo):
    created = repo.create(Circuit(id=0, user_id=1, name="del", cost=0, structure_json=structure_json("del")))
    assert repo.delete(created.id, user_id=1) is True
    assert repo.get_by_id(created.id) is None

    # deleting again -> False (covers rowcount > 0 branch)
    assert repo.delete(created.id, user_id=1) is False


def test_delete_wrong_owner_false_branch(repo):
    created = repo.create(Circuit(id=0, user_id=1, name="owned", cost=0, structure_json=structure_json("owned")))
    assert repo.delete(created.id, user_id=2) is False
    assert repo.get_by_id(created.id) is not None


def test_unique_user_name_constraint(repo):
    repo.create(Circuit(id=0, user_id=5, name="same", cost=1, structure_json=structure_json("a")))
    with pytest.raises(sqlite3.IntegrityError):
        repo.create(Circuit(id=0, user_id=5, name="same", cost=2, structure_json=structure_json("b")))

    # different user_id allowed
    repo.create(Circuit(id=0, user_id=6, name="same", cost=2, structure_json=structure_json("c")))
