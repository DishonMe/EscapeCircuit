import sys
sys.path.insert(0, '../src')

import pytest
import json

# Assuming we have access to the logic engine service
# from Backend.ServiceLayer.logicEngineService import logicEngineService
# from Backend.DomainLayer.Circuit import Circuit

@pytest.fixture
def test_cases():
    """Test cases for sequential adder"""
    return [
        {
            "input_stream": [1, 0, 1, 1, 0],
            "expected": {
                "OUT": [1, 1, 0, 1, 0],
                "C_out": [0, 0, 1, 0, 1]
            }
        },
        {
            "input_stream": [0, 0, 1, 0],
            "expected": {
                "OUT": [0, 0, 1, 1],
                "C_out": [0, 0, 0, 0]
            }
        },
        {
            "input_stream": [1, 1, 1],
            "expected": {
                "OUT": [1, 1, 0],
                "C_out": [0, 0, 1]
            }
        }
    ]

def test_mealy_map_correctness():
    """Verify that our Mealy map matches the sequential adder logic"""
    mealy_map = {
        (0, 0, 0): (0, 0, 0, 0),  # (X, D1, D2) -> (OUT, C_out, D1_next, D2_next)
        (1, 0, 0): (1, 0, 1, 0),
        (0, 0, 1): (1, 0, 0, 0),
        (1, 0, 1): (0, 1, 1, 0),
        (0, 1, 0): (1, 0, 0, 1),
        (1, 1, 0): (1, 0, 1, 1),
        (0, 1, 1): (0, 1, 0, 1),
        (1, 1, 1): (0, 1, 1, 1),
    }

    # Test each state transition
    for (x, d1, d2), (expected_out, expected_cout, expected_d1_next, expected_d2_next) in mealy_map.items():
        # Combinational logic: A=x, B=d1, C_in=d2
        a, b, c_in = x, d1, d2
        u = a | b  # OR
        out = u ^ c_in  # XOR
        cout = u & c_in  # AND

        # State updates
        d1_next = x
        d2_next = d1

        assert out == expected_out, f"OUT calculation failed for ({x},{d1},{d2})"
        assert cout == expected_cout, f"C_out calculation failed for ({x},{d1},{d2})"
        assert d1_next == expected_d1_next, f"D1_next calculation failed for ({x},{d1},{d2})"
        assert d2_next == expected_d2_next, f"D2_next calculation failed for ({x},{d1},{d2})"

def test_sample_correct_sequential_circuit(test_cases):
    """
    Test a sample correct sequential adder implementation by validating the Mealy map
    """
    # Sample circuit JSON with mealy_map for a correct sequential adder
    sample_circuit_json = json.dumps({
        "type": "sequential_riddle",
        "used_gates": ["AND", "NAND", "DFF"],
        "input": ["X"],
        "state": ["D1", "D2"],
        "outputs": ["OUT", "C_out"],
        "initial_state": {"D1": 0, "D2": 0},
        "mealy_map": {
            "{\"X\":0,\"D1\":0,\"D2\":0}": {"OUT":0, "C_out":0, "D1_next":0, "D2_next":0},
            "{\"X\":1,\"D1\":0,\"D2\":0}": {"OUT":1, "C_out":0, "D1_next":1, "D2_next":0},
            "{\"X\":0,\"D1\":0,\"D2\":1}": {"OUT":1, "C_out":0, "D1_next":0, "D2_next":0},
            "{\"X\":1,\"D1\":0,\"D2\":1}": {"OUT":0, "C_out":1, "D1_next":1, "D2_next":0},
            "{\"X\":0,\"D1\":1,\"D2\":0}": {"OUT":1, "C_out":0, "D1_next":0, "D2_next":1},
            "{\"X\":1,\"D1\":1,\"D2\":0}": {"OUT":1, "C_out":0, "D1_next":1, "D2_next":1},
            "{\"X\":0,\"D1\":1,\"D2\":1}": {"OUT":0, "C_out":1, "D1_next":0, "D2_next":1},
            "{\"X\":1,\"D1\":1,\"D2\":1}": {"OUT":0, "C_out":1, "D1_next":1, "D2_next":1}
        }
    })

    # Parse the JSON
    circuit_data = json.loads(sample_circuit_json)

    # Validate structure
    assert circuit_data["type"] == "sequential_riddle"
    assert set(circuit_data["input"]) == {"X"}
    assert set(circuit_data["state"]) == {"D1", "D2"}
    assert set(circuit_data["outputs"]) == {"OUT", "C_out"}
    assert circuit_data["initial_state"] == {"D1": 0, "D2": 0}
    assert set(circuit_data["used_gates"]) == {"AND", "NAND", "DFF"}

    # Validate Mealy map has all required states
    mealy_map = circuit_data["mealy_map"]
    required_states = [
        (0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1),
        (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1)
    ]

    for x, d1, d2 in required_states:
        state_key = f'{{"X":{x},"D1":{d1},"D2":{d2}}}'
        assert state_key in mealy_map, f"Missing state {state_key}"

        transition = mealy_map[state_key]
        required_outputs = {"OUT", "C_out", "D1_next", "D2_next"}
        assert set(transition.keys()) == required_outputs, f"Invalid transition for {state_key}"

    # Simulate sequential behavior manually for test cases
    for test_case in test_cases:
        input_stream = test_case["input_stream"]
        expected_out = test_case["expected"]["OUT"]
        expected_cout = test_case["expected"]["C_out"]

        # Simulate sequential behavior
        current_d1, current_d2 = 0, 0  # Initial state
        actual_out = []
        actual_cout = []

        for x in input_stream:
            # Look up transition in Mealy map
            state_key = f'{{"X":{x},"D1":{current_d1},"D2":{current_d2}}}'
            transition = mealy_map[state_key]

            # Record outputs
            actual_out.append(transition["OUT"])
            actual_cout.append(transition["C_out"])

            # Update state for next cycle
            current_d1 = transition["D1_next"]
            current_d2 = transition["D2_next"]

        # Check that outputs match expected
        assert actual_out == expected_out, f"OUT stream failed. Expected {expected_out}, got {actual_out}"
        assert actual_cout == expected_cout, f"C_out stream failed. Expected {expected_cout}, got {actual_cout}"

    print("✅ Sample sequential adder circuit test passed!")

if __name__ == "__main__":
    # Run the tests
    test_cases_fixture = [
        {
            "input_stream": [1, 0, 1, 1, 0],
            "expected": {
                "OUT": [1, 1, 0, 1, 0],
                "C_out": [0, 0, 1, 0, 1]
            }
        },
        {
            "input_stream": [0, 0, 1, 0],
            "expected": {
                "OUT": [0, 0, 1, 1],
                "C_out": [0, 0, 0, 0]
            }
        },
        {
            "input_stream": [1, 1, 1],
            "expected": {
                "OUT": [1, 1, 0],
                "C_out": [0, 0, 1]
            }
        }
    ]

    test_mealy_map_correctness()
    test_sample_correct_sequential_circuit(test_cases_fixture)

    print("🎉 All sequential adder tests passed!")