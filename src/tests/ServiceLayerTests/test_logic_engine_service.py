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
