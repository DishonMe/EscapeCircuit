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


class TestCircuitArsenalOperations:
    """Test list_arsenal_by_user() method with various scenarios"""

    def test_list_arsenal_by_user_empty_no_circuits(self, repo):
        """Arsenal list is empty when user has no circuits at all"""
        assert repo.list_arsenal_by_user(999) == []

    def test_list_arsenal_by_user_empty_no_arsenal(self, repo):
        """Arsenal list is empty when user has circuits but none marked as arsenal"""
        repo.create(Circuit(id=0, user_id=1, name="regular", cost=5, structure_json=structure_json("x"), is_arsenal=False))
        repo.create(Circuit(id=0, user_id=1, name="regular2", cost=3, structure_json=structure_json("x"), is_arsenal=False))
        assert repo.list_arsenal_by_user(1) == []

    def test_list_arsenal_by_user_single_arsenal(self, repo):
        """Returns single arsenal piece"""
        repo.create(Circuit(id=0, user_id=1, name="regular", cost=5, structure_json=structure_json("x"), is_arsenal=False))
        arsenal = repo.create(Circuit(
            id=0, user_id=1, name="arsenal1", cost=2, structure_json=structure_json("a"), 
            is_arsenal=True, basic_gates='["AND"]', truth_table='{"0": "1"}', num_inputs=1, num_outputs=1
        ))
        
        result = repo.list_arsenal_by_user(1)
        assert len(result) == 1
        assert result[0].is_arsenal is True
        assert result[0].id == arsenal.id

    def test_list_arsenal_by_user_multiple_mixed(self, repo):
        """Filters correctly when user has mix of arsenal and regular circuits"""
        repo.create(Circuit(id=0, user_id=1, name="c1", cost=1, structure_json=structure_json("x"), is_arsenal=False))
        ar1 = repo.create(Circuit(
            id=0, user_id=1, name="a1", cost=2, structure_json=structure_json("x"), 
            is_arsenal=True, basic_gates='["AND"]', truth_table='{"0": "1"}', num_inputs=1, num_outputs=1
        ))
        repo.create(Circuit(id=0, user_id=1, name="c2", cost=3, structure_json=structure_json("x"), is_arsenal=False))
        ar2 = repo.create(Circuit(
            id=0, user_id=1, name="a2", cost=4, structure_json=structure_json("x"), 
            is_arsenal=True, basic_gates='["OR"]', truth_table='{"1": "0"}', num_inputs=1, num_outputs=1
        ))
        
        result = repo.list_arsenal_by_user(1)
        assert len(result) == 2
        assert all(c.is_arsenal for c in result)
        assert [c.id for c in result] == sorted([ar1.id, ar2.id], reverse=True)

    def test_list_arsenal_by_user_different_users_isolated(self, repo):
        """Arsenal pieces from other users are not returned"""
        ar1_user1 = repo.create(Circuit(
            id=0, user_id=1, name="a", cost=1, structure_json=structure_json("x"), 
            is_arsenal=True, basic_gates='["AND"]', truth_table='{"0": "1"}', num_inputs=1, num_outputs=1
        ))
        ar1_user2 = repo.create(Circuit(
            id=0, user_id=2, name="a", cost=1, structure_json=structure_json("x"), 
            is_arsenal=True, basic_gates='["AND"]', truth_table='{"0": "1"}', num_inputs=1, num_outputs=1
        ))
        
        result1 = repo.list_arsenal_by_user(1)
        result2 = repo.list_arsenal_by_user(2)
        
        assert len(result1) == 1
        assert result1[0].id == ar1_user1.id
        assert len(result2) == 1
        assert result2[0].id == ar1_user2.id

    def test_list_arsenal_by_user_order_desc(self, repo):
        """Arsenal pieces are returned in DESC order by id"""
        ids = []
        for i in range(3):
            c = repo.create(Circuit(
                id=0, user_id=1, name=f"a{i}", cost=i, structure_json=structure_json(str(i)), 
                is_arsenal=True, basic_gates='["AND"]', truth_table='{"0": "1"}', num_inputs=1, num_outputs=1
            ))
            ids.append(c.id)
        
        result = repo.list_arsenal_by_user(1)
        assert [c.id for c in result] == sorted(ids, reverse=True)


class TestCircuitUpdate:
    """Test update() method with various field mutations"""

    def test_update_success(self, repo):
        """Update returns True on successful update"""
        circuit = repo.create(Circuit(id=0, user_id=1, name="original", cost=5, structure_json=structure_json("original")))
        circuit.name = "updated"
        circuit.cost = 10
        
        result = repo.update(circuit)
        assert result is True

    def test_update_name_persists(self, repo):
        """Updated name persists in database"""
        circuit = repo.create(Circuit(id=0, user_id=1, name="orig", cost=5, structure_json=structure_json("x")))
        circuit.name = "new_name"
        repo.update(circuit)
        
        fetched = repo.get_by_id(circuit.id)
        assert fetched.name == "new_name"

    def test_update_cost_persists(self, repo):
        """Updated cost persists in database"""
        circuit = repo.create(Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x")))
        circuit.cost = 20
        repo.update(circuit)
        
        fetched = repo.get_by_id(circuit.id)
        assert fetched.cost == 20

    def test_update_structure_json_persists(self, repo):
        """Updated structure_json persists"""
        circuit = repo.create(Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("old")))
        new_struct = structure_json("new")
        circuit.structure_json = new_struct
        repo.update(circuit)
        
        fetched = repo.get_by_id(circuit.id)
        assert fetched.structure_json == new_struct

    def test_update_is_arsenal_persists(self, repo):
        """Updated is_arsenal flag persists"""
        circuit = repo.create(Circuit(
            id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x"), 
            is_arsenal=False, basic_gates="", truth_table=""
        ))
        circuit.is_arsenal = True
        circuit.basic_gates = '["AND"]'
        circuit.truth_table = '{"0": "1"}'
        circuit.num_inputs = 1
        circuit.num_outputs = 1
        repo.update(circuit)
        
        fetched = repo.get_by_id(circuit.id)
        assert fetched.is_arsenal is True

    def test_update_basic_gates_persists(self, repo):
        """Updated basic_gates persists"""
        circuit = repo.create(Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x"), basic_gates="[]"))
        circuit.basic_gates = '["AND", "OR"]'
        repo.update(circuit)
        
        fetched = repo.get_by_id(circuit.id)
        assert fetched.basic_gates == '["AND", "OR"]'

    def test_update_truth_table_persists(self, repo):
        """Updated truth_table persists"""
        circuit = repo.create(Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x"), truth_table="{}"))
        new_table = '{"0": "1"}'
        circuit.truth_table = new_table
        repo.update(circuit)
        
        fetched = repo.get_by_id(circuit.id)
        assert fetched.truth_table == new_table

    def test_update_num_inputs_persists(self, repo):
        """Updated num_inputs persists"""
        circuit = repo.create(Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x"), num_inputs=0))
        circuit.num_inputs = 3
        repo.update(circuit)
        
        fetched = repo.get_by_id(circuit.id)
        assert fetched.num_inputs == 3

    def test_update_num_outputs_persists(self, repo):
        """Updated num_outputs persists"""
        circuit = repo.create(Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x"), num_outputs=0))
        circuit.num_outputs = 2
        repo.update(circuit)
        
        fetched = repo.get_by_id(circuit.id)
        assert fetched.num_outputs == 2

    def test_update_all_fields_at_once(self, repo):
        """Update with all fields changed simultaneously"""
        circuit = repo.create(Circuit(
            id=0, user_id=1, name="orig", cost=1, 
            structure_json=structure_json("orig"),
            is_arsenal=False, basic_gates="[]", truth_table="{}",
            num_inputs=0, num_outputs=0
        ))
        
        new_struct = structure_json("new")
        circuit.name = "updated"
        circuit.cost = 99
        circuit.structure_json = new_struct
        circuit.is_arsenal = True
        circuit.basic_gates = '["AND"]'
        circuit.truth_table = '{"key": "val"}'
        circuit.num_inputs = 5
        circuit.num_outputs = 3
        
        repo.update(circuit)
        fetched = repo.get_by_id(circuit.id)
        
        assert fetched.name == "updated"
        assert fetched.cost == 99
        assert fetched.structure_json == new_struct
        assert fetched.is_arsenal is True
        assert fetched.basic_gates == '["AND"]'
        assert fetched.truth_table == '{"key": "val"}'
        assert fetched.num_inputs == 5
        assert fetched.num_outputs == 3

    def test_update_wrong_owner_false_branch(self, repo):
        """Update returns False when circuit_id exists but user_id doesn't match"""
        circuit = repo.create(Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x")))
        circuit.user_id = 2  # change to wrong owner
        circuit.name = "updated"
        
        result = repo.update(circuit)
        assert result is False

    def test_update_wrong_owner_no_change(self, repo):
        """Wrong owner update leaves data unchanged"""
        circuit = repo.create(Circuit(id=0, user_id=1, name="orig", cost=5, structure_json=structure_json("x")))
        circuit.user_id = 2
        circuit.name = "updated"
        
        repo.update(circuit)
        fetched = repo.get_by_id(circuit.id)
        assert fetched.name == "orig"  # should not have changed

    def test_update_nonexistent_circuit(self, repo):
        """Update on non-existent circuit returns False"""
        circuit = Circuit(id=999999, user_id=1, name="fake", cost=0, structure_json=structure_json("x"))
        result = repo.update(circuit)
        assert result is False


class TestCircuitFields:
    """Test persistence of all circuit fields"""

    def test_create_with_all_fields_persists(self, repo):
        """All circuit fields are persisted and retrieved correctly"""
        circuit = Circuit(
            id=0, user_id=10, name="complete",
            cost=50, structure_json=structure_json("test"),
            is_arsenal=True, basic_gates='["AND", "OR", "XOR"]',
            truth_table='{"a": 1, "b": 2}',
            num_inputs=4, num_outputs=2
        )
        created = repo.create(circuit)
        fetched = repo.get_by_id(created.id)
        
        assert fetched.user_id == 10
        assert fetched.name == "complete"
        assert fetched.cost == 50
        assert fetched.structure_json == structure_json("test")
        assert fetched.is_arsenal is True
        assert fetched.basic_gates == '["AND", "OR", "XOR"]'
        assert fetched.truth_table == '{"a": 1, "b": 2}'
        assert fetched.num_inputs == 4
        assert fetched.num_outputs == 2

    def test_is_arsenal_false_by_default(self, repo):
        """is_arsenal defaults to False when not specified"""
        circuit = Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x"))
        created = repo.create(circuit)
        fetched = repo.get_by_id(created.id)
        assert fetched.is_arsenal is False

    def test_basic_gates_empty_string_by_default(self, repo):
        """basic_gates defaults to empty string when not specified"""
        circuit = Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x"))
        created = repo.create(circuit)
        fetched = repo.get_by_id(created.id)
        assert fetched.basic_gates == ""

    def test_truth_table_empty_string_by_default(self, repo):
        """truth_table defaults to empty string when not specified"""
        circuit = Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x"))
        created = repo.create(circuit)
        fetched = repo.get_by_id(created.id)
        assert fetched.truth_table == ""

    def test_num_inputs_zero_by_default(self, repo):
        """num_inputs defaults to 0 when not specified"""
        circuit = Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x"))
        created = repo.create(circuit)
        fetched = repo.get_by_id(created.id)
        assert fetched.num_inputs == 0

    def test_num_outputs_zero_by_default(self, repo):
        """num_outputs defaults to 0 when not specified"""
        circuit = Circuit(id=0, user_id=1, name="c", cost=5, structure_json=structure_json("x"))
        created = repo.create(circuit)
        fetched = repo.get_by_id(created.id)
        assert fetched.num_outputs == 0
