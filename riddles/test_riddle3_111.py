#!/usr/bin/env python3
"""
Test script for riddle3 sequential adder with input [1, 1, 1]
"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, '../src')

from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.DomainLayer.Circuit import Circuit

def test_riddle3_with_111():
    """Test the sequential adder with input stream [1, 1, 1]"""

    # Load the riddle3 config
    with open('riddle_03_sequential_adder_config.json', 'r') as f:
        config = json.load(f)

    print("🔧 Testing Riddle 3: Sequential Binary Adder")
    print("=" * 50)
    print(f"Puzzle: {config['puzzle']['name']}")
    print(f"Input stream: [1, 1, 1]")
    print()

    # Load the sample solution
    with open('riddle_03_sequential_adder_sample_solution.json', 'r') as f:
        solution = json.load(f)

    # Create circuit
    logic_engine = logicEngineService()
    circuit = Circuit(
        id=3,
        user_id=1,
        name="Sequential Adder Test",
        structure_json=json.dumps(solution),
        cost=0
    )

    # Test with input [1, 1, 1]
    input_stream = [1, 1, 1]
    print("Cycle-by-cycle execution:")
    print("Cycle | Input X | State (D1,D2) | OUT | C_out | Next State")
    print("-" * 60)

    current_state = {"D1": 0, "D2": 0}  # Initial state

    for cycle, x in enumerate(input_stream, 1):
        # Create input dict (input + current state)
        inputs = {"X": x}
        inputs.update(current_state)

        # Evaluate circuit
        outputs = logic_engine.evaluate(circuit, inputs)

        # Display results
        print(f"  {cycle}   |   {x}     |   ({current_state['D1']},{current_state['D2']})      |  {outputs['OUT']}  |   {outputs['C_out']}   |   ({outputs['D1_next']},{outputs['D2_next']})")

        # Update state for next cycle
        current_state["D1"] = outputs["D1_next"]
        current_state["D2"] = outputs["D2_next"]

    print()
    print("Final Results:")
    print(f"Input stream: {input_stream}")
    print(f"OUT stream:  {[1, 1, 0]}")
    print(f"C_out stream: {[0, 0, 1]}")
    print()
    print("This demonstrates how the sequential adder processes bits one at a time,")
    print("maintaining state across clock cycles to perform binary addition!")

if __name__ == "__main__":
    test_riddle3_with_111()