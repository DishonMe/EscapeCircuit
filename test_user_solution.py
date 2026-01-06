#!/usr/bin/env python3
"""
Script to test a user's binary adder circuit solution.
Usage: python test_user_solution.py <circuit_json_file>
"""

import sys
import json
import os

# Add src to path
sys.path.insert(0, 'src')

from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.DomainLayer.Circuit import Circuit

def test_user_circuit(circuit_json_file):
    """Test a user's circuit solution against the binary adder requirements"""

    # Load the user's circuit JSON
    if not os.path.exists(circuit_json_file):
        print(f"Error: File {circuit_json_file} not found")
        return False

    with open(circuit_json_file, 'r') as f:
        circuit_data = json.load(f)

    # Convert to JSON string as expected by the system
    circuit_json = json.dumps(circuit_data)

    # Create circuit object
    circuit = Circuit(
        id=1,
        user_id=1,
        name="User Binary Adder Solution",
        structure_json=circuit_json,
        cost=0
    )

    logic_engine = logicEngineService()

    # Test cases for full adder
    test_cases = [
        {"inputs": {"A": 0, "B": 0, "C_in": 0}, "expected": {"S": 0, "C_out": 0}},
        {"inputs": {"A": 0, "B": 0, "C_in": 1}, "expected": {"S": 1, "C_out": 0}},
        {"inputs": {"A": 0, "B": 1, "C_in": 0}, "expected": {"S": 1, "C_out": 0}},
        {"inputs": {"A": 0, "B": 1, "C_in": 1}, "expected": {"S": 0, "C_out": 1}},
        {"inputs": {"A": 1, "B": 0, "C_in": 0}, "expected": {"S": 1, "C_out": 0}},
        {"inputs": {"A": 1, "B": 0, "C_in": 1}, "expected": {"S": 0, "C_out": 1}},
        {"inputs": {"A": 1, "B": 1, "C_in": 0}, "expected": {"S": 0, "C_out": 1}},
        {"inputs": {"A": 1, "B": 1, "C_in": 1}, "expected": {"S": 1, "C_out": 1}},
    ]

    print("Testing Binary Adder Circuit Solution")
    print("=" * 40)

    # Check gate constraints
    allowed_gates = {"AND", "NAND", "DELAY"}
    used_gates = logic_engine.extract_used_gates(circuit_json)
    invalid_gates = used_gates - allowed_gates

    if invalid_gates:
        print(f"❌ FAIL: Invalid gates used: {invalid_gates}")
        print(f"   Allowed gates: {allowed_gates}")
        return False
    else:
        print(f"✅ PASS: Gate constraints (used: {used_gates})")

    # Check input/output structure
    data = logic_engine._load(circuit_json)
    required_inputs = {"A", "B", "C_in"}
    required_outputs = {"S", "C_out"}

    if "inputs" in data:
        circuit_inputs = set(data["inputs"])
        if circuit_inputs != required_inputs:
            print(f"❌ FAIL: Wrong inputs. Expected {required_inputs}, got {circuit_inputs}")
            return False
    else:
        print("❌ FAIL: No inputs specified in circuit")
        return False

    if "outputs" in data:
        circuit_outputs = set(data["outputs"])
        if circuit_outputs != required_outputs:
            print(f"❌ FAIL: Wrong outputs. Expected {required_outputs}, got {circuit_outputs}")
            return False
    else:
        print("❌ FAIL: No outputs specified in circuit")
        return False

    print("✅ PASS: Input/Output structure")

    # Test all cases
    all_passed = True
    for i, test_case in enumerate(test_cases):
        inputs = test_case["inputs"]
        expected = test_case["expected"]

        try:
            actual_outputs = logic_engine.evaluate(circuit, inputs)

            # Check each output
            for output_name, expected_value in expected.items():
                if output_name not in actual_outputs:
                    print(f"❌ FAIL: Test {i+1} - Missing output '{output_name}' for inputs {inputs}")
                    all_passed = False
                    break
                elif actual_outputs[output_name] != expected_value:
                    print(f"❌ FAIL: Test {i+1} - Expected {output_name}={expected_value}, got {actual_outputs[output_name]} for inputs {inputs}")
                    all_passed = False
                    break
            else:
                print(f"✅ PASS: Test {i+1} - Inputs {inputs} -> Outputs {actual_outputs}")

        except Exception as e:
            print(f"❌ FAIL: Test {i+1} - Evaluation error for inputs {inputs}: {e}")
            all_passed = False

    print("=" * 40)
    if all_passed:
        print("🎉 SUCCESS: All tests passed! Your binary adder circuit is correct.")
        return True
    else:
        print("❌ FAILURE: Some tests failed. Please check your circuit implementation.")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_user_solution.py <circuit_json_file>")
        print("Example: python test_user_solution.py my_adder_circuit.json")
        sys.exit(1)

    circuit_file = sys.argv[1]
    success = test_user_circuit(circuit_file)
    sys.exit(0 if success else 1)