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

