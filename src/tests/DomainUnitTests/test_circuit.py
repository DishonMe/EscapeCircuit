import pytest
import json
from datetime import datetime, timezone

from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.Exceptions import ValidationError


class TestCircuitCreation:
    def test_create_circuit_valid(self):
        structure = json.dumps({"gates": ["AND", "OR"], "construction_string": "test"})
        circuit = Circuit(
            id=1,
            user_id=2,
            name="TestCircuit",
            cost=10,
            structure_json=structure
        )
        assert circuit.id == 1
        assert circuit.user_id == 2
        assert circuit.name == "TestCircuit"
        assert circuit.cost == 10
        assert circuit.structure_json == structure

    def test_create_circuit_zero_cost(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(
            id=1,
            user_id=1,
            name="ZeroCost",
            cost=0,
            structure_json=structure
        )
        assert circuit.cost == 0

    def test_create_circuit_negative_id(self):
        structure = json.dumps({"gates": []})
        with pytest.raises(ValidationError) as exc_info:
            Circuit(id=-1, user_id=1, name="Bad", cost=0, structure_json=structure)
        assert "Circuit.id cannot be negative" in str(exc_info.value)

    def test_create_circuit_negative_user_id(self):
        structure = json.dumps({"gates": []})
        with pytest.raises(ValidationError) as exc_info:
            Circuit(id=1, user_id=-1, name="Bad", cost=0, structure_json=structure)
        assert "Circuit.user_id cannot be negative" in str(exc_info.value)

    def test_create_circuit_empty_name(self):
        structure = json.dumps({"gates": []})
        with pytest.raises(ValidationError) as exc_info:
            Circuit(id=1, user_id=1, name="", cost=0, structure_json=structure)
        assert "Circuit.name is required" in str(exc_info.value)

    def test_create_circuit_whitespace_name(self):
        structure = json.dumps({"gates": []})
        with pytest.raises(ValidationError) as exc_info:
            Circuit(id=1, user_id=1, name="   ", cost=0, structure_json=structure)
        assert "Circuit.name is required" in str(exc_info.value)

    def test_create_circuit_negative_cost(self):
        structure = json.dumps({"gates": []})
        with pytest.raises(ValidationError) as exc_info:
            Circuit(id=1, user_id=1, name="Bad", cost=-5, structure_json=structure)
        assert "Circuit.cost cannot be negative" in str(exc_info.value)

    def test_create_circuit_empty_structure_json(self):
        with pytest.raises(ValidationError) as exc_info:
            Circuit(id=1, user_id=1, name="Bad", cost=0, structure_json="")
        assert "Circuit.structure_json is required" in str(exc_info.value)

    def test_create_circuit_invalid_json(self):
        with pytest.raises(ValidationError) as exc_info:
            Circuit(id=1, user_id=1, name="Bad", cost=0, structure_json="not valid json")
        assert "Circuit.structure_json must be valid JSON" in str(exc_info.value)


class TestCircuitGates:
    def test_get_list_of_gates(self):
        structure = json.dumps({"gates": ["AND", "OR", "NOT"]})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        gates = circuit.get_list_of_gates()
        assert gates == ["AND", "OR", "NOT"]

    def test_get_list_of_gates_empty(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        gates = circuit.get_list_of_gates()
        assert gates == []

    def test_get_list_of_gates_missing_key(self):
        structure = json.dumps({})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        gates = circuit.get_list_of_gates()
        assert gates == []


class TestCircuitTruthTable:
    def test_get_truth_table_special_circuit(self):
        truth_table = {"0": "1", "1": "0"}
        structure = json.dumps({
            "is_special": True,
            "truth_table": truth_table
        })
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        result = circuit.get_truth_table()
        assert result == truth_table

    def test_get_truth_table_non_special_circuit(self):
        structure = json.dumps({"is_special": False, "truth_table": {}})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        with pytest.raises(ValidationError) as exc_info:
            circuit.get_truth_table()
        assert "not marked as special" in str(exc_info.value)

    def test_get_truth_table_missing_special_flag(self):
        structure = json.dumps({})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        with pytest.raises(ValidationError):
            circuit.get_truth_table()


class TestCircuitStringRepresentation:
    def test_get_string_representation(self):
        structure = json.dumps({"construction_string": "A AND B OR C"})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        assert circuit.get_string_representation() == "A AND B OR C"

    def test_get_string_representation_empty(self):
        structure = json.dumps({})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        assert circuit.get_string_representation() == ""


class TestCircuitCost:
    def test_calculate_cost_predefined(self):
        structure = json.dumps({"gates": ["AND", "OR"]})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=50, structure_json=structure)
        assert circuit.calculate_cost({}) == 50

    def test_calculate_cost_zero_predefined(self):
        structure = json.dumps({"gates": ["AND", "OR"]})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        # Should calculate: 2 basic gates
        cost = circuit.calculate_cost({})
        assert cost == 2

    def test_calculate_cost_with_basic_gates(self):
        structure = json.dumps({"gates": ["AND", "OR", "NOT", "XOR", "NAND", "NOR", "XNOR"]})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        cost = circuit.calculate_cost({})
        assert cost == 7

    def test_calculate_cost_with_special_gates(self):
        structure = json.dumps({"gates": ["AND", "CUSTOM_GATE"]})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        mock_special = type('obj', (object,), {'calculate_cost': lambda self: 10})()
        cost = circuit.calculate_cost({"CUSTOM_GATE": mock_special})
        assert cost == 11  # 1 basic + 10 special

    def test_calculate_cost_missing_special_gate(self):
        structure = json.dumps({"gates": ["AND", "MISSING_GATE"]})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        with pytest.raises(ValidationError) as exc_info:
            circuit.calculate_cost({})
        assert "MISSING_GATE" in str(exc_info.value)

    def test_calculate_cost_dff_gate(self):
        structure = json.dumps({"gates": ["DFF"]})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        with pytest.raises(ValidationError) as exc_info:
            circuit.calculate_cost({})
        assert "DFF" in str(exc_info.value)


class TestCircuitSetters:
    def test_set_name(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Original", cost=0, structure_json=structure)
        circuit.set_name("Updated")
        assert circuit.get_name() == "Updated"

    def test_set_name_empty(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Original", cost=0, structure_json=structure)
        with pytest.raises(ValidationError):
            circuit.set_name("")

    def test_set_cost(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        circuit.set_cost(100)
        assert circuit.get_cost() == 100

    def test_set_cost_negative(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        with pytest.raises(ValidationError):
            circuit.set_cost(-10)

    def test_set_structure_json(self):
        old_structure = json.dumps({"gates": []})
        new_structure = json.dumps({"gates": ["AND"]})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=old_structure)
        circuit.set_structure_json(new_structure)
        assert circuit.get_structure_json() == new_structure

    def test_set_structure_json_invalid(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        with pytest.raises(ValidationError):
            circuit.set_structure_json("invalid json")


class TestCircuitGetters:
    def test_get_id(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=42, user_id=1, name="Test", cost=0, structure_json=structure)
        assert circuit.get_id() == 42

    def test_get_user_id(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=99, name="Test", cost=0, structure_json=structure)
        assert circuit.get_user_id() == 99

    def test_get_name(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="MyCircuit", cost=0, structure_json=structure)
        assert circuit.get_name() == "MyCircuit"

    def test_get_cost(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=123, structure_json=structure)
        assert circuit.get_cost() == 123

    def test_get_structure_json(self):
        structure = json.dumps({"gates": ["AND", "OR"], "custom_field": "value"})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        assert circuit.get_structure_json() == structure


class TestCircuitSerialization:
    def test_to_dict(self):
        structure = json.dumps({"gates": ["AND"]})
        circuit = Circuit(id=1, user_id=2, name="Test", cost=5, structure_json=structure)
        d = circuit.to_dict()
        assert d["id"] == 1
        assert d["user_id"] == 2
        assert d["name"] == "Test"
        assert d["cost"] == 5
        assert d["structure_json"] == structure

    def test_from_dict(self):
        structure = json.dumps({"gates": ["AND"]})
        d = {
            "id": 1,
            "user_id": 2,
            "name": "Test",
            "cost": 5,
            "structure_json": structure
        }
        circuit = Circuit.from_dict(d)
        assert circuit.id == 1
        assert circuit.user_id == 2
        assert circuit.name == "Test"
        assert circuit.cost == 5
        assert circuit.structure_json == structure

    def test_roundtrip(self):
        structure = json.dumps({"gates": ["AND", "OR"], "construction_string": "A OR B"})
        original = Circuit(id=3, user_id=4, name="Complex", cost=25, structure_json=structure)
        d = original.to_dict()
        restored = Circuit.from_dict(d)
        assert restored.id == original.id
        assert restored.user_id == original.user_id
        assert restored.name == original.name
        assert restored.cost == original.cost
        assert restored.structure_json == original.structure_json

    def test_to_dict_includes_all_fields(self):
        structure = json.dumps({"gates": ["XOR"]})
        circuit = Circuit(id=7, user_id=8, name="Complex", cost=15, structure_json=structure)
        d = circuit.to_dict()
        assert set(d.keys()) == {"id", "user_id", "name", "cost", "structure_json", "num_inputs", "num_outputs", "is_arsenal", "truth_table", "basic_gates", "puzzle_id"}

    def test_from_dict_missing_field_raises_error(self):
        d = {"id": 1, "user_id": 2, "name": "Test"}  # Missing cost and structure_json
        with pytest.raises((KeyError, TypeError)):
            Circuit.from_dict(d)


class TestCircuitEdgeCases:
    def test_large_cost_value(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Expensive", cost=999999, structure_json=structure)
        assert circuit.get_cost() == 999999

    def test_large_id_value(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=999999, user_id=1, name="Test", cost=0, structure_json=structure)
        assert circuit.get_id() == 999999

    def test_set_name_with_special_characters(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Original", cost=0, structure_json=structure)
        circuit.set_name("Test_Circuit-123!@#$%")
        assert circuit.get_name() == "Test_Circuit-123!@#$%"

    def test_cost_zero_with_many_gates(self):
        structure = json.dumps({"gates": ["AND", "OR", "NOT", "XOR", "NAND", "NOR", "XNOR"] * 10})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        cost = circuit.calculate_cost({})
        assert cost == 70  # 7 gates * 10

    def test_calculate_cost_predefined_ignores_gates(self):
        """When cost > 0, calculate_cost should return predefined cost regardless of gates"""
        structure = json.dumps({"gates": ["AND", "OR", "NOT", "XOR", "NAND"]})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=100, structure_json=structure)
        assert circuit.calculate_cost({}) == 100

    def test_calculate_cost_with_mixed_basic_and_special_gates(self):
        structure = json.dumps({"gates": ["AND", "SPECIAL_A", "OR", "SPECIAL_B", "NOT"]})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        special_gates = {
            "SPECIAL_A": type('obj', (object,), {'calculate_cost': lambda self: 5})(),
            "SPECIAL_B": type('obj', (object,), {'calculate_cost': lambda self: 10})()
        }
        cost = circuit.calculate_cost(special_gates)
        assert cost == 18  # 3 basic gates (AND, OR, NOT) + 5 + 10

    def test_set_structure_json_whitespace_only_raises_error(self):
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=1, name="Test", cost=0, structure_json=structure)
        with pytest.raises(ValidationError) as exc_info:
            circuit.set_structure_json("   ")
        assert "required" in str(exc_info.value).lower()

    def test_create_circuit_zero_id(self):
        """Test that id=0 is valid (only negative is invalid)"""
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=0, user_id=1, name="Test", cost=0, structure_json=structure)
        assert circuit.get_id() == 0

    def test_create_circuit_zero_user_id(self):
        """Test that user_id=0 is valid (only negative is invalid)"""
        structure = json.dumps({"gates": []})
        circuit = Circuit(id=1, user_id=0, name="Test", cost=0, structure_json=structure)
        assert circuit.get_user_id() == 0


class TestCircuitArsenalPiece:
    """Test arsenal piece creation and validation"""
    
    def test_create_arsenal_piece_valid(self):
        """Test creating a valid arsenal piece with all required fields"""
        structure = json.dumps({"gates": ["AND", "OR"]})
        basic_gates = json.dumps(["AND", "OR"])
        truth_table = json.dumps({"0": "1", "1": "0"})
        
        circuit = Circuit(
            id=1,
            user_id=1,
            name="ArsenalGate",
            cost=5,
            structure_json=structure,
            is_arsenal=True,
            basic_gates=basic_gates,
            truth_table=truth_table,
            num_inputs=2,
            num_outputs=1
        )
        assert circuit.is_arsenal is True
        assert circuit.basic_gates == basic_gates
        assert circuit.truth_table == truth_table
        assert circuit.num_inputs == 2
        assert circuit.num_outputs == 1
    
    def test_arsenal_piece_missing_basic_gates(self):
        """Test that arsenal piece requires basic_gates"""
        structure = json.dumps({"gates": []})
        truth_table = json.dumps({"0": "1"})
        
        with pytest.raises(ValidationError) as exc_info:
            Circuit(
                id=1,
                user_id=1,
                name="Bad",
                cost=0,
                structure_json=structure,
                is_arsenal=True,
                basic_gates=None,
                truth_table=truth_table
            )
        assert "basic_gates" in str(exc_info.value).lower()
    
    def test_arsenal_piece_empty_basic_gates(self):
        """Test that arsenal piece basic_gates cannot be empty string"""
        structure = json.dumps({"gates": []})
        truth_table = json.dumps({"0": "1"})
        
        with pytest.raises(ValidationError) as exc_info:
            Circuit(
                id=1,
                user_id=1,
                name="Bad",
                cost=0,
                structure_json=structure,
                is_arsenal=True,
                basic_gates="",
                truth_table=truth_table
            )
        assert "basic_gates" in str(exc_info.value).lower()
    
    def test_arsenal_piece_whitespace_basic_gates(self):
        """Test that arsenal piece basic_gates cannot be whitespace only"""
        structure = json.dumps({"gates": []})
        truth_table = json.dumps({"0": "1"})
        
        with pytest.raises(ValidationError) as exc_info:
            Circuit(
                id=1,
                user_id=1,
                name="Bad",
                cost=0,
                structure_json=structure,
                is_arsenal=True,
                basic_gates="   ",
                truth_table=truth_table
            )
        assert "basic_gates" in str(exc_info.value).lower()
    
    def test_arsenal_piece_missing_truth_table(self):
        """Test that arsenal piece requires truth_table"""
        structure = json.dumps({"gates": []})
        basic_gates = json.dumps(["AND"])
        
        with pytest.raises(ValidationError) as exc_info:
            Circuit(
                id=1,
                user_id=1,
                name="Bad",
                cost=0,
                structure_json=structure,
                is_arsenal=True,
                basic_gates=basic_gates,
                truth_table=None
            )
        assert "truth_table" in str(exc_info.value).lower()
    
    def test_arsenal_piece_empty_truth_table(self):
        """Test that arsenal piece truth_table cannot be empty string"""
        structure = json.dumps({"gates": []})
        basic_gates = json.dumps(["AND"])
        
        with pytest.raises(ValidationError) as exc_info:
            Circuit(
                id=1,
                user_id=1,
                name="Bad",
                cost=0,
                structure_json=structure,
                is_arsenal=True,
                basic_gates=basic_gates,
                truth_table=""
            )
        assert "truth_table" in str(exc_info.value).lower()
    
    def test_arsenal_piece_whitespace_truth_table(self):
        """Test that arsenal piece truth_table cannot be whitespace only"""
        structure = json.dumps({"gates": []})
        basic_gates = json.dumps(["AND"])
        
        with pytest.raises(ValidationError) as exc_info:
            Circuit(
                id=1,
                user_id=1,
                name="Bad",
                cost=0,
                structure_json=structure,
                is_arsenal=True,
                basic_gates=basic_gates,
                truth_table="   "
            )
        assert "truth_table" in str(exc_info.value).lower()
    
    def test_arsenal_piece_invalid_basic_gates_json(self):
        """Test that arsenal piece basic_gates must be valid JSON"""
        structure = json.dumps({"gates": []})
        truth_table = json.dumps({"0": "1"})
        
        with pytest.raises(ValidationError) as exc_info:
            Circuit(
                id=1,
                user_id=1,
                name="Bad",
                cost=0,
                structure_json=structure,
                is_arsenal=True,
                basic_gates="not valid json",
                truth_table=truth_table
            )
        assert "basic_gates" in str(exc_info.value).lower()
        assert "json" in str(exc_info.value).lower()
    
    def test_arsenal_piece_basic_gates_not_list(self):
        """Test that arsenal piece basic_gates must be a JSON list"""
        structure = json.dumps({"gates": []})
        truth_table = json.dumps({"0": "1"})
        
        with pytest.raises(ValidationError) as exc_info:
            Circuit(
                id=1,
                user_id=1,
                name="Bad",
                cost=0,
                structure_json=structure,
                is_arsenal=True,
                basic_gates='{"gates": "AND"}',  # dict, not list
                truth_table=truth_table
            )
        assert "list" in str(exc_info.value).lower()
    
    def test_arsenal_piece_invalid_truth_table_json(self):
        """Test that arsenal piece truth_table must be valid JSON"""
        structure = json.dumps({"gates": []})
        basic_gates = json.dumps(["AND"])
        
        with pytest.raises(ValidationError) as exc_info:
            Circuit(
                id=1,
                user_id=1,
                name="Bad",
                cost=0,
                structure_json=structure,
                is_arsenal=True,
                basic_gates=basic_gates,
                truth_table="not valid json"
            )
        assert "truth_table" in str(exc_info.value).lower()
        assert "json" in str(exc_info.value).lower()
    
    def test_arsenal_piece_truth_table_not_dict(self):
        """Test that arsenal piece truth_table must be a JSON dict"""
        structure = json.dumps({"gates": []})
        basic_gates = json.dumps(["AND"])
        
        with pytest.raises(ValidationError) as exc_info:
            Circuit(
                id=1,
                user_id=1,
                name="Bad",
                cost=0,
                structure_json=structure,
                is_arsenal=True,
                basic_gates=basic_gates,
                truth_table='["0", "1"]'  # list, not dict
            )
        assert "dict" in str(exc_info.value).lower()
    
    def test_arsenal_piece_complex_truth_table(self):
        """Test arsenal piece with complex truth table"""
        structure = json.dumps({"gates": ["AND", "OR"]})
        basic_gates = json.dumps(["AND", "OR", "NOT"])
        truth_table = json.dumps({
            "00": "0",
            "01": "1",
            "10": "1",
            "11": "1"
        })
        
        circuit = Circuit(
            id=2,
            user_id=1,
            name="ComplexArsenal",
            cost=10,
            structure_json=structure,
            is_arsenal=True,
            basic_gates=basic_gates,
            truth_table=truth_table,
            num_inputs=2,
            num_outputs=1
        )
        assert circuit.is_arsenal is True
    
    def test_non_arsenal_piece_ignores_basic_gates_and_truth_table(self):
        """Test that non-arsenal pieces don't require basic_gates and truth_table"""
        structure = json.dumps({"gates": ["AND"]})
        
        circuit = Circuit(
            id=1,
            user_id=1,
            name="NonArsenal",
            cost=5,
            structure_json=structure,
            is_arsenal=False,
            basic_gates=None,
            truth_table=None
        )
        assert circuit.is_arsenal is False
    
    def test_arsenal_piece_to_circuit_component(self):
        """Test converting arsenal piece to circuit component format"""
        structure = json.dumps({"gates": ["AND"]})
        basic_gates = json.dumps(["AND"])
        truth_table = json.dumps({"0": "1", "1": "0"})
        
        circuit = Circuit(
            id=99,
            user_id=1,
            name="ArsenalComponent",
            cost=7,
            structure_json=structure,
            is_arsenal=True,
            basic_gates=basic_gates,
            truth_table=truth_table,
            num_inputs=2,
            num_outputs=1
        )
        component = circuit.to_circuit_component()
        
        assert component["id"] == "99"
        assert component["type"] == "ArsenalComponent"
        assert component["cost"] == 7
        assert component["pins"] == 3  # 2 inputs + 1 output
        assert component["is_arsenal"] is True
        assert component["num_inputs"] == 2
        assert component["num_outputs"] == 1
    
    def test_arsenal_piece_with_max_pins(self):
        """Test arsenal piece with maximum pins"""
        structure = json.dumps({"gates": ["AND", "OR"]})
        basic_gates = json.dumps(["AND", "OR"])
        truth_table = json.dumps({})
        
        circuit = Circuit(
            id=1,
            user_id=1,
            name="MaxPins",
            cost=0,
            structure_json=structure,
            is_arsenal=True,
            basic_gates=basic_gates,
            truth_table=truth_table,
            num_inputs=10,
            num_outputs=8
        )
        component = circuit.to_circuit_component()
        assert component["pins"] == 18
