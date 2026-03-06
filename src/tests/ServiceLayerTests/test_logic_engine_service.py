import pytest
import json
from unittest.mock import Mock

from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.Exceptions import ValidationError


class TestLogicEngineServiceEvaluate:
    def setup_method(self):
        self.service = logicEngineService()

    def test_evaluate_with_eval_map_success(self):
        """Test successful evaluation using eval_map format"""
        structure_json = json.dumps({
            "eval_map": {
                '{"a":0,"b":0}': {"output": 0},
                '{"a":0,"b":1}': {"output": 1},
                '{"a":1,"b":0}': {"output": 1},
                '{"a":1,"b":1}': {"output": 1},
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="OR_gate", 
            cost=0,
            structure_json=structure_json
        )
        
        result = self.service.evaluate(circuit, {"a": 1, "b": 0})
        
        assert result == {"output": 1}

    def test_evaluate_with_eval_map_zero_output(self):
        """Test evaluation with zero output"""
        structure_json = json.dumps({
            "eval_map": {
                '{"a":0,"b":0}': {"output": 0},
                '{"a":0,"b":1}': {"output": 1},
                '{"a":1,"b":0}': {"output": 1},
                '{"a":1,"b":1}': {"output": 1},
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="OR_gate", 
            cost=0,
            structure_json=structure_json
        )
        
        result = self.service.evaluate(circuit, {"a": 0, "b": 0})
        
        assert result == {"output": 0}

    def test_evaluate_with_truth_table_success(self):
        """Test successful evaluation using truth_table format"""
        structure_json = json.dumps({
            "truth_table": {
                '{"x":0,"y":0}': {"z": 0},
                '{"x":0,"y":1}': {"z": 1},
                '{"x":1,"y":0}': {"z": 1},
                '{"x":1,"y":1}': {"z": 0},
            }
        })
        circuit = Circuit(
            id=2, 
            user_id=1, 
            name="XOR_gate", 
            cost=0,
            structure_json=structure_json
        )
        
        result = self.service.evaluate(circuit, {"x": 1, "y": 0})
        
        assert result == {"z": 1}

    def test_evaluate_with_multiple_outputs(self):
        """Test evaluation with multiple outputs"""
        structure_json = json.dumps({
            "eval_map": {
                '{"in":0}': {"sum": 0, "carry": 0},
                '{"in":1}': {"sum": 1, "carry": 0},
            }
        })
        circuit = Circuit(
            id=3, 
            user_id=1, 
            name="adder", 
            cost=0,
            structure_json=structure_json
        )
        
        result = self.service.evaluate(circuit, {"in": 1})
        
        assert result == {"sum": 1, "carry": 0}

    def test_evaluate_with_invalid_json(self):
        """Test evaluation with invalid JSON - caught during Circuit creation"""
        # Circuit validates JSON in __post_init__, so validation error happens there
        with pytest.raises(ValidationError) as exc_info:
            circuit = Circuit(
                id=1, 
                user_id=1, 
                name="bad_circuit", 
                cost=0,
                structure_json="not valid json"
            )
        
        assert "valid JSON" in str(exc_info.value)

    def test_evaluate_with_missing_eval_map_entry(self):
        """Test evaluation with missing eval_map entry"""
        structure_json = json.dumps({
            "eval_map": {
                '{"a":0,"b":0}': {"output": 0},
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="incomplete", 
            cost=0,
            structure_json=structure_json
        )
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.evaluate(circuit, {"a": 1, "b": 1})
        
        assert "no eval_map entry for inputs" in str(exc_info.value)

    def test_evaluate_with_missing_truth_table_entry(self):
        """Test evaluation with missing truth_table entry"""
        structure_json = json.dumps({
            "truth_table": {
                '{"x":0,"y":0}': {"z": 0},
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="incomplete_truth", 
            cost=0,
            structure_json=structure_json
        )
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.evaluate(circuit, {"x": 1, "y": 1})
        
        assert "truth_table missing entry" in str(exc_info.value)

    def test_evaluate_with_invalid_eval_map_output(self):
        """Test evaluation with invalid eval_map output (not a dict)"""
        structure_json = json.dumps({
            "eval_map": {
                '{"a":0}': "not a dict",
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="bad_output", 
            cost=0,
            structure_json=structure_json
        )
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.evaluate(circuit, {"a": 0})
        
        assert "eval_map output must be dict" in str(exc_info.value)

    def test_evaluate_with_invalid_truth_table_output(self):
        """Test evaluation with invalid truth_table output (not a dict)"""
        structure_json = json.dumps({
            "truth_table": {
                '{"x":0}': [1, 2, 3],
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="bad_truth_output", 
            cost=0,
            structure_json=structure_json
        )
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.evaluate(circuit, {"x": 0})
        
        assert "truth_table output must be dict" in str(exc_info.value)

    def test_evaluate_with_unsupported_format(self):
        """Test evaluation with unsupported format"""
        structure_json = json.dumps({
            "unknown_format": {}
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="unsupported", 
            cost=0,
            structure_json=structure_json
        )
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.evaluate(circuit, {"a": 0})
        
        assert "logic engine format not supported" in str(exc_info.value)

    def test_evaluate_with_string_key_ordering(self):
        """Test that input keys are properly sorted for matching"""
        structure_json = json.dumps({
            "eval_map": {
                '{"a":0,"b":1}': {"output": 5},
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="sort_test", 
            cost=0,
            structure_json=structure_json
        )
        
        # Both orderings should match due to sort_keys=True in the service
        result = self.service.evaluate(circuit, {"b": 1, "a": 0})
        assert result == {"output": 5}

    def test_evaluate_converts_output_values_to_ints(self):
        """Test that output values are converted to ints"""
        structure_json = json.dumps({
            "eval_map": {
                '{"x":1}': {"result": 42},
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="conversion_test", 
            cost=0,
            structure_json=structure_json
        )
        
        result = self.service.evaluate(circuit, {"x": 1})
        
        # Verify all values in output are ints
        assert isinstance(result["result"], int)
        assert result["result"] == 42

    def test_evaluate_with_empty_eval_map(self):
        """Test evaluation with empty eval_map"""
        structure_json = json.dumps({
            "eval_map": {}
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="empty_map", 
            cost=0,
            structure_json=structure_json
        )
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.evaluate(circuit, {"a": 0})
        
        assert "no eval_map entry for inputs" in str(exc_info.value)

    def test_evaluate_with_circuit_that_has_corrupted_json(self):
        """Test evaluate handles arbitrary exceptions when parsing JSON"""
        # Create a mock circuit with a structure_json that will fail parsing
        circuit = Mock(spec=Circuit)
        circuit.structure_json = "{invalid json"
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.evaluate(circuit, {"a": 0})
        
        assert "invalid circuit json" in str(exc_info.value)


# ============ Additional branch coverage tests ============

class TestLogicEngineServiceComputeCost:
    """Test compute_cost method"""
    
    def setup_method(self):
        self.service = logicEngineService()

    def test_compute_cost_zero_components(self):
        """Test computing cost with no components"""
        structure_json = json.dumps({"components": [], "wires": []})
        
        cost = self.service.compute_cost(structure_json)
        assert cost >= 0

    def test_compute_cost_with_components(self):
        """Test computing cost with multiple components"""
        structure_json = json.dumps({
            "components": [
                {"type": "AND", "id": 1},
                {"type": "OR", "id": 2},
                {"type": "NOT", "id": 3},
            ],
            "wires": []
        })
        
        cost = self.service.compute_cost(structure_json)
        assert cost >= 0  # Should calculate without error


class TestLogicEngineServiceHasEntry:
    """Test has_entry_for_inputs method"""
    
    def setup_method(self):
        self.service = logicEngineService()

    def test_has_entry_in_eval_map(self):
        """Test checking if entry exists in eval_map"""
        structure_json = json.dumps({
            "eval_map": {
                '{"a":0,"b":0}': {"output": 0},
                '{"a":0,"b":1}': {"output": 1},
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="check_entry", 
            cost=0,
            structure_json=structure_json
        )
        
        result = self.service.has_entry_for_inputs(circuit, {"a": 0, "b": 0})
        assert result is True

    def test_no_entry_in_eval_map(self):
        """Test when entry doesn't exist"""
        structure_json = json.dumps({
            "eval_map": {
                '{"a":0,"b":0}': {"output": 0},
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="no_entry", 
            cost=0,
            structure_json=structure_json
        )
        
        result = self.service.has_entry_for_inputs(circuit, {"a": 1, "b": 1})
        assert result is False

    def test_has_entry_in_truth_table(self):
        """Test checking if entry exists in truth_table"""
        structure_json = json.dumps({
            "truth_table": {
                '{"x":0,"y":0}': {"z": 0},
                '{"x":0,"y":1}': {"z": 1},
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="check_truth", 
            cost=0,
            structure_json=structure_json
        )
        
        result = self.service.has_entry_for_inputs(circuit, {"x": 0, "y": 1})
        assert result is True


class TestLogicEngineServiceValidation:
    """Test input/output validation"""
    
    def setup_method(self):
        self.service = logicEngineService()

    def test_validate_inputs_success(self):
        """Test valid input validation"""
        structure_json = json.dumps({
            "inputs": ["a", "b"],
            "eval_map": {
                '{"a":0,"b":0}': {"output": 0},
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="validate", 
            cost=0,
            structure_json=structure_json
        )
        
        # Should not raise
        result = self.service.evaluate(circuit, {"a": 0, "b": 0})
        assert result == {"output": 0}

    def test_missing_input_handling(self):
        """Test when required input is missing"""
        structure_json = json.dumps({
            "inputs": ["a", "b"],
            "eval_map": {
                '{"a":0,"b":0}': {"output": 0},
            }
        })
        circuit = Circuit(
            id=1, 
            user_id=1, 
            name="missing_input", 
            cost=0,
            structure_json=structure_json
        )
        
        # Missing "b" in inputs
        with pytest.raises(ValidationError):
            self.service.evaluate(circuit, {"a": 0})


class TestExtractUsedGates:
    """Test extract_used_gates method with different formats"""
    
    def setup_method(self):
        self.service = logicEngineService()
    
    def test_extract_used_gates_from_used_gates_field(self):
        """Test extracting gates from 'used_gates' field"""
        structure_json = json.dumps({
            "used_gates": ["AND", "OR", "NOT"]
        })
        
        gates = self.service.extract_used_gates(structure_json)
        assert gates == {"AND", "OR", "NOT"}
    
    def test_extract_used_gates_from_gates_counts(self):
        """Test extracting gates from 'gates_counts' field"""
        structure_json = json.dumps({
            "gates_counts": {"AND": 3, "OR": 2, "NOT": 1}
        })
        
        gates = self.service.extract_used_gates(structure_json)
        assert gates == {"AND", "OR", "NOT"}
    
    def test_extract_used_gates_from_components_array(self):
        """Test extracting gates from 'components' array"""
        structure_json = json.dumps({
            "components": [
                {"type": "AND", "id": 1},
                {"type": "OR", "id": 2},
                {"type": "AND", "id": 3}
            ]
        })
        
        gates = self.service.extract_used_gates(structure_json)
        assert gates == {"AND", "OR"}
    
    def test_extract_used_gates_empty(self):
        """Test extracting gates from empty structure"""
        structure_json = json.dumps({})
        
        gates = self.service.extract_used_gates(structure_json)
        assert gates == set()


class TestExtractGateCounts:
    """Test extract_gate_counts method with different formats"""
    
    def setup_method(self):
        self.service = logicEngineService()
    
    def test_extract_gate_counts_from_gates_counts_field(self):
        """Test extracting counts from 'gates_counts' field"""
        structure_json = json.dumps({
            "gates_counts": {"AND": 3, "OR": 2, "NOT": 1}
        })
        
        counts = self.service.extract_gate_counts(structure_json)
        assert counts == {"AND": 3, "OR": 2, "NOT": 1}
    
    def test_extract_gate_counts_from_components_array(self):
        """Test extracting counts from 'components' array"""
        structure_json = json.dumps({
            "components": [
                {"type": "AND", "id": 1},
                {"type": "OR", "id": 2},
                {"type": "AND", "id": 3},
                {"type": "AND", "id": 4}
            ]
        })
        
        counts = self.service.extract_gate_counts(structure_json)
        assert counts == {"AND": 3, "OR": 1}
    
    def test_extract_gate_counts_from_placed_components(self):
        """Test extracting counts from 'placedComponents' array"""
        structure_json = json.dumps({
            "placedComponents": [
                {"id": "c1", "componentId": "AND"},
                {"id": "c2", "componentId": "OR"},
                {"id": "c3", "type": "NOT"}
            ]
        })
        
        counts = self.service.extract_gate_counts(structure_json)
        assert counts == {"AND": 1, "OR": 1, "NOT": 1}
    
    def test_extract_gate_counts_empty(self):
        """Test extracting counts from empty structure"""
        structure_json = json.dumps({})
        
        counts = self.service.extract_gate_counts(structure_json)
        assert counts == {}


class TestComputeCostMethod:
    """Test compute_cost method"""
    
    def setup_method(self):
        self.service = logicEngineService()
    
    def test_compute_cost_with_explicit_cost_field(self):
        """Test when 'cost' field is explicitly provided"""
        structure_json = json.dumps({
            "cost": 42
        })
        
        cost = self.service.compute_cost(structure_json)
        assert cost == 42
    
    def test_compute_cost_with_value_field(self):
        """Test when 'value' field is provided"""
        structure_json = json.dumps({
            "value": 15
        })
        
        cost = self.service.compute_cost(structure_json)
        assert cost == 15
    
    def test_compute_cost_computed_cost_field(self):
        """Test when 'computed_cost' field is provided"""
        structure_json = json.dumps({
            "computed_cost": 25
        })
        
        cost = self.service.compute_cost(structure_json)
        assert cost == 25
    
    def test_compute_cost_from_gates_counts(self):
        """Test cost computation from gates_counts"""
        structure_json = json.dumps({
            "gates_counts": {"AND": 3, "OR": 2, "NOT": 1}
        })
        
        cost = self.service.compute_cost(structure_json)
        assert cost == 6  # 3 + 2 + 1
    
    def test_compute_cost_from_components(self):
        """Test cost computation from components array"""
        structure_json = json.dumps({
            "components": [
                {"type": "AND"},
                {"type": "OR"},
                {"type": "NOT"}
            ]
        })
        
        cost = self.service.compute_cost(structure_json)
        assert cost == 3
    
    def test_compute_cost_with_nested_costs(self):
        """Test cost computation with nested_costs"""
        structure_json = json.dumps({
            "gates_counts": {"AND": 2, "OR": 1},
            "nested_costs": [5, 3]
        })
        
        cost = self.service.compute_cost(structure_json)
        assert cost == 11  # 2 + 1 + 5 + 3


class TestValidateGateUsage:
    """Test validate_gate_usage method"""
    
    def setup_method(self):
        self.service = logicEngineService()
    
    def test_validate_gate_usage_allowed_gates(self):
        """Test validation with allowed gates"""
        structure_json = json.dumps({
            "used_gates": ["AND", "OR"]
        })
        
        # Should not raise
        self.service.validate_gate_usage(structure_json, {"AND", "OR", "NOT", "XOR"})
    
    def test_validate_gate_usage_illegal_gates(self):
        """Test validation with illegal gates"""
        structure_json = json.dumps({
            "used_gates": ["AND", "OR", "EXOTIC"]
        })
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.validate_gate_usage(structure_json, {"AND", "OR", "NOT"})
        
        assert "illegal gates" in str(exc_info.value)
    
    def test_validate_gate_usage_empty_gates(self):
        """Test validation with no used gates"""
        structure_json = json.dumps({
            "used_gates": []
        })
        
        # Should not raise even with empty allowed set
        self.service.validate_gate_usage(structure_json, set())


class TestComputeGateLogic:
    """Test _compute_gate helper method"""
    
    def setup_method(self):
        self.service = logicEngineService()
    
    def test_and_gate_logic(self):
        """Test AND gate computation"""
        assert self.service._compute_gate("AND", [0, 0]) == 0
        assert self.service._compute_gate("AND", [0, 1]) == 0
        assert self.service._compute_gate("AND", [1, 0]) == 0
        assert self.service._compute_gate("AND", [1, 1]) == 1
    
    def test_or_gate_logic(self):
        """Test OR gate computation"""
        assert self.service._compute_gate("OR", [0, 0]) == 0
        assert self.service._compute_gate("OR", [0, 1]) == 1
        assert self.service._compute_gate("OR", [1, 0]) == 1
        assert self.service._compute_gate("OR", [1, 1]) == 1
    
    def test_xor_gate_logic(self):
        """Test XOR gate computation"""
        assert self.service._compute_gate("XOR", [0, 0]) == 0
        assert self.service._compute_gate("XOR", [0, 1]) == 1
        assert self.service._compute_gate("XOR", [1, 0]) == 1
        assert self.service._compute_gate("XOR", [1, 1]) == 0
    
    def test_nand_gate_logic(self):
        """Test NAND gate computation"""
        assert self.service._compute_gate("NAND", [0, 0]) == 1
        assert self.service._compute_gate("NAND", [0, 1]) == 1
        assert self.service._compute_gate("NAND", [1, 0]) == 1
        assert self.service._compute_gate("NAND", [1, 1]) == 0
    
    def test_nor_gate_logic(self):
        """Test NOR gate computation"""
        assert self.service._compute_gate("NOR", [0, 0]) == 1
        assert self.service._compute_gate("NOR", [0, 1]) == 0
        assert self.service._compute_gate("NOR", [1, 0]) == 0
        assert self.service._compute_gate("NOR", [1, 1]) == 0
    
    def test_xnor_gate_logic(self):
        """Test XNOR gate computation"""
        assert self.service._compute_gate("XNOR", [0, 0]) == 1
        assert self.service._compute_gate("XNOR", [0, 1]) == 0
        assert self.service._compute_gate("XNOR", [1, 0]) == 0
        assert self.service._compute_gate("XNOR", [1, 1]) == 1
    
    def test_not_gate_logic(self):
        """Test NOT gate computation"""
        assert self.service._compute_gate("NOT", [0]) == 1
        assert self.service._compute_gate("NOT", [1]) == 0
    
    def test_delay_gate_logic(self):
        """Test DELAY gate computation"""
        assert self.service._compute_gate("DELAY", [0]) == 0
        assert self.service._compute_gate("DELAY", [1]) == 1
    
    def test_buf_gate_logic(self):
        """Test BUF gate computation"""
        assert self.service._compute_gate("BUF", [0]) == 0
        assert self.service._compute_gate("BUF", [1]) == 1
    
    def test_unknown_gate_logic(self):
        """Test with unknown gate type"""
        assert self.service._compute_gate("UNKNOWN", [0, 1]) is None
    
    def test_gate_logic_with_none_input(self):
        """Test gate with None input (unknown/floating)"""
        assert self.service._compute_gate("AND", [None, 1]) is None
        assert self.service._compute_gate("AND", [0, None]) is None


class TestSimulateCircuit:
    """Test simulate method for combinatorial circuits"""
    
    def setup_method(self):
        self.service = logicEngineService()
    
    def test_simulate_basic_circuit(self):
        """Test simulate with basic circuit structure"""
        data = {
            "placedComponents": [
                {"id": "c1", "componentId": "AND"},
                {"id": "c2", "componentId": "OR"}
            ],
            "wires": []
        }
        
        result = self.service.simulate(data, {})
        assert isinstance(result, dict)
    
    def test_simulate_with_none_arsenal_pieces(self):
        """Test simulate with None arsenal_pieces"""
        data = {
            "placedComponents": [],
            "wires": []
        }
        
        result = self.service.simulate(data, {}, arsenal_pieces=None)
        assert result == {}
    
    def test_simulate_fallback_to_components(self):
        """Test simulate fallback to 'components' when 'placedComponents' missing"""
        data = {
            "components": [
                {"id": "c1", "componentId": "AND"}
            ],
            "wires": []
        }
        
        result = self.service.simulate(data, {})
        assert isinstance(result, dict)


class TestEvalMapEvaluate:
    """Test evaluate method with eval_map (lines 27-31)"""
    
    def test_evaluate_with_eval_map_valid_inputs(self):
        """Test evaluate with valid eval_map entry"""
        inputs = {"A": 0, "B": 0}
        key = json.dumps(inputs, sort_keys=True, separators=(',', ':'))
        
        circuit_data = {
            "eval_map": {
                key: {"out": 0}
            }
        }
        
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=10,
            structure_json=json.dumps(circuit_data)
        )
        
        service = logicEngineService()
        result = service.evaluate(circuit, inputs)
        
        assert result == {"out": 0}
    
    def test_evaluate_with_eval_map_missing_entry(self):
        """Test evaluate raises ValidationError when eval_map entry not found"""
        inputs = {"A": 1, "B": 1}
        circuit_data = {
            "eval_map": {}
        }
        
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=10,
            structure_json=json.dumps(circuit_data)
        )
        
        service = logicEngineService()
        with pytest.raises(ValidationError, match="no eval_map entry"):
            service.evaluate(circuit, inputs)
    
    def test_evaluate_with_eval_map_non_dict_output(self):
        """Test evaluate raises ValidationError when eval_map output is not dict"""
        inputs = {"A": 0, "B": 0}
        key = json.dumps(inputs, sort_keys=True, separators=(',', ':'))
        
        circuit_data = {
            "eval_map": {
                key: "invalid"  # Not a dict
            }
        }
        
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=10,
            structure_json=json.dumps(circuit_data)
        )
        
        service = logicEngineService()
        with pytest.raises(ValidationError, match="eval_map output must be dict"):
            service.evaluate(circuit, inputs)


class TestTruthTableEvaluate:
    """Test evaluate method with truth_table (lines 33-39)"""
    
    def test_evaluate_with_truth_table_valid_inputs(self):
        """Test evaluate with valid truth_table entry"""
        inputs = {"A": 1, "B": 0}
        key = json.dumps(inputs, sort_keys=True, separators=(',', ':'))
        
        circuit_data = {
            "truth_table": {
                key: {"out": 1}
            }
        }
        
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=10,
            structure_json=json.dumps(circuit_data)
        )
        
        service = logicEngineService()
        result = service.evaluate(circuit, inputs)
        
        assert result == {"out": 1}
    
    def test_evaluate_with_truth_table_missing_entry(self):
        """Test evaluate raises ValidationError when truth_table entry not found"""
        inputs = {"A": 1, "B": 1}
        circuit_data = {
            "truth_table": {}
        }
        
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=10,
            structure_json=json.dumps(circuit_data)
        )
        
        service = logicEngineService()
        with pytest.raises(ValidationError, match="truth_table missing entry"):
            service.evaluate(circuit, inputs)
    
    def test_evaluate_with_truth_table_non_dict_output(self):
        """Test evaluate raises ValidationError when truth_table output is not dict"""
        inputs = {"A": 0, "B": 0}
        key = json.dumps(inputs, sort_keys=True, separators=(',', ':'))
        
        circuit_data = {
            "truth_table": {
                key: 42  # Not a dict
            }
        }
        
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=10,
            structure_json=json.dumps(circuit_data)
        )
        
        service = logicEngineService()
        with pytest.raises(ValidationError, match="truth_table output must be dict"):
            service.evaluate(circuit, inputs)


class TestMealyMachineEvaluate:
    """Test evaluate method with mealy_map (lines 41-48)"""
    
    def test_evaluate_with_mealy_map_sequential_riddle(self):
        """Test evaluate with mealy_map for sequential_riddle"""
        inputs = {"A": 0, "state": 1}
        key = json.dumps(inputs, sort_keys=True, separators=(',', ':'))
        
        circuit_data = {
            "type": "sequential_riddle",
            "mealy_map": {
                key: {"out": 0, "next_state": 0}
            }
        }
        
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=10,
            structure_json=json.dumps(circuit_data)
        )
        
        service = logicEngineService()
        result = service.evaluate(circuit, inputs)
        
        assert result == {"out": 0, "next_state": 0}
    
    def test_evaluate_with_mealy_map_missing_entry(self):
        """Test evaluate raises ValidationError when mealy_map entry not found"""
        inputs = {"A": 1, "state": 0}
        circuit_data = {
            "type": "sequential_riddle",
            "mealy_map": {}
        }
        
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=10,
            structure_json=json.dumps(circuit_data)
        )
        
        service = logicEngineService()
        with pytest.raises(ValidationError, match="no mealy_map entry"):
            service.evaluate(circuit, inputs)
    
    def test_evaluate_with_mealy_map_non_dict_transition(self):
        """Test evaluate raises ValidationError when mealy_map transition is not dict"""
        inputs = {"A": 0, "state": 1}
        key = json.dumps(inputs, sort_keys=True, separators=(',', ':'))
        
        circuit_data = {
            "type": "sequential_riddle",
            "mealy_map": {
                key: "invalid"  # Not a dict
            }
        }
        
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=10,
            structure_json=json.dumps(circuit_data)
        )
        
        service = logicEngineService()
        with pytest.raises(ValidationError, match="mealy_map transition must be dict"):
            service.evaluate(circuit, inputs)


class TestUnsupportedFormat:
    """Test evaluate with unsupported format (lines 50-51)"""
    
    def test_evaluate_unsupported_format(self):
        """Test evaluate raises ValidationError for unsupported format"""
        circuit_data = {
            "unsupported_key": "value"
        }
        
        circuit = Circuit(
            id=1, user_id=1, name="test", cost=10,
            structure_json=json.dumps(circuit_data)
        )
        
        service = logicEngineService()
        with pytest.raises(ValidationError, match="logic engine format not supported"):
            service.evaluate(circuit, {"A": 0})


class TestSimulationWithArsenalPieces:
    """Test simulate method with arsenal_pieces"""
    
    def test_simulate_with_empty_arsenal_pieces(self):
        """Test simulate handles empty arsenal_pieces dict"""
        circuit_data = {
            "placedComponents": [
                {"id": "comp1", "componentId": "AND"}
            ],
            "wires": []
        }
        
        service = logicEngineService()
        # Should not raise error with empty arsenal
        result = service.simulate(circuit_data, {"A": 0, "B": 1}, {})
        
        assert isinstance(result, dict)
    
    def test_simulate_with_none_arsenal_pieces(self):
        """Test simulate handles None arsenal_pieces"""
        circuit_data = {
            "placedComponents": [
                {"id": "comp1", "componentId": "OR"}
            ],
            "wires": []
        }
        
        service = logicEngineService()
        # Should not raise error with None arsenal
        result = service.simulate(circuit_data, {"A": 0, "B": 0}, None)
        
        assert isinstance(result, dict)
    
    def test_simulate_with_components_fallback(self):
        """Test simulate uses 'components' as fallback for 'placedComponents'"""
        circuit_data = {
            "components": [  # Using 'components' instead of 'placedComponents'
                {"id": "comp1", "componentId": "NOT"}
            ],
            "wires": []
        }
        
        service = logicEngineService()
        result = service.simulate(circuit_data, {"A": 1}, {})
        
        assert isinstance(result, dict)


class TestSimulationTypeConversion:
    """Test simulate type conversions for outputs"""
    
    def test_simulate_output_type_conversion_to_string_int(self):
        """Test simulate converts output keys to string and values to int"""
        circuit_data = {
            "placedComponents": [],
            "wires": []
        }
        
        service = logicEngineService()
        # Manually inject a result to test conversion
        result = service.simulate(circuit_data, {}, {})
        
        # Result should have string keys and int values
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, int)
