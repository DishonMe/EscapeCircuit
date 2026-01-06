import sys
sys.path.insert(0, '../src')

import pytest
import json

# Assuming we have access to the logic engine service
from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.DomainLayer.Circuit import Circuit

@pytest.fixture
def test_cases():
    """Test cases for half adder"""
    return [
        {"inputs": {"A": 0, "B": 0}, "expected": {"S": 0, "C_out": 0}},
        {"inputs": {"A": 0, "B": 1}, "expected": {"S": 1, "C_out": 0}},
        {"inputs": {"A": 1, "B": 0}, "expected": {"S": 1, "C_out": 0}},
        {"inputs": {"A": 1, "B": 1}, "expected": {"S": 0, "C_out": 1}},
    ]

def test_truth_table_correctness(test_cases):
    """Verify that our test cases match the mathematical definition of a half adder"""
    for test_case in test_cases:
        a, b = test_case["inputs"]["A"], test_case["inputs"]["B"]
        expected_s, expected_c_out = test_case["expected"]["S"], test_case["expected"]["C_out"]

        # Mathematical calculation: S = A XOR B, C_out = A AND B
        calculated_s = (a ^ b)
        calculated_c_out = (a & b)

        assert calculated_s == expected_s, f"Sum calculation failed for inputs {a},{b}"
        assert calculated_c_out == expected_c_out, f"Carry calculation failed for inputs {a},{b}"

def test_sample_correct_circuit(test_cases):
    """
    Test a sample correct half adder implementation to verify the testing framework works
    """
    logic_engine = logicEngineService()

    # Sample circuit JSON with eval_map for a correct half adder
    sample_circuit_json = json.dumps({
        "eval_map": {
            '{"A": 0, "B": 0}': {"S": 0, "C_out": 0},
            '{"A": 0, "B": 1}': {"S": 1, "C_out": 0},
            '{"A": 1, "B": 0}': {"S": 1, "C_out": 0},
            '{"A": 1, "B": 1}': {"S": 0, "C_out": 1}
        },
        "used_gates": ["AND", "NAND", "DFF"],
        "inputs": ["A", "B"],
        "outputs": ["S", "C_out"]
    })

    # Create a mock circuit object
    circuit = Circuit(
        id=1,
        user_id=1,
        name="Half Adder Solution",
        structure_json=sample_circuit_json,
        cost=0
    )

    # Test the sample circuit against all test cases
    for test_case in test_cases:
        inputs = test_case["inputs"]
        expected = test_case["expected"]

        # Evaluate the circuit with the inputs
        actual_outputs = logic_engine.evaluate(circuit, inputs)

        # Check that all expected outputs match
        for output_name, expected_value in expected.items():
            assert output_name in actual_outputs, f"Missing output: {output_name}"
            assert actual_outputs[output_name] == expected_value, \
                f"Failed for inputs {inputs}: expected {output_name}={expected_value}, got {actual_outputs[output_name]}"

    # Test gate constraints
    allowed_gates = {"AND", "NAND", "DFF"}
    used_gates = logic_engine.extract_used_gates(sample_circuit_json)
    for gate in used_gates:
        assert gate in allowed_gates, f"Disallowed gate used: {gate}"

    # Test input/output structure
    data = logic_engine._load(sample_circuit_json)
    required_inputs = {"A", "B"}
    required_outputs = {"S", "C_out"}

    if "inputs" in data:
        circuit_inputs = set(data["inputs"])
        assert circuit_inputs == required_inputs, f"Expected inputs {required_inputs}, got {circuit_inputs}"

    if "outputs" in data:
        circuit_outputs = set(data["outputs"])
        assert circuit_outputs == required_outputs, f"Expected outputs {required_outputs}, got {circuit_outputs}"

    print("✅ Sample half adder circuit test passed!")

if __name__ == "__main__":
    # Run the tests
    test_cases_fixture = [
        {"inputs": {"A": 0, "B": 0}, "expected": {"S": 0, "C_out": 0}},
        {"inputs": {"A": 0, "B": 1}, "expected": {"S": 1, "C_out": 0}},
        {"inputs": {"A": 1, "B": 0}, "expected": {"S": 1, "C_out": 0}},
        {"inputs": {"A": 1, "B": 1}, "expected": {"S": 0, "C_out": 1}},
    ]

    test_truth_table_correctness(test_cases_fixture)
    test_sample_correct_circuit(test_cases_fixture)

    print("🎉 All half adder tests passed!")