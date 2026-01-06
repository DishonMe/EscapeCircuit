#!/usr/bin/env python3
"""
Script to create and publish the Sequential Binary Adder puzzle in the EscapeCircuit system.
Run this script to add the puzzle to the database.
"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, '../src')

from Backend.ServiceLayer.PuzzleService import PuzzleService
from Backend.ServiceLayer.AuthService import AuthService
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.DomainLayer.Enums import GateType

def create_sequential_adder_puzzle():
    """Create the Sequential Binary Adder puzzle in the system"""

    # Load puzzle configuration from JSON
    with open('riddle_03_sequential_adder_config.json', 'r') as f:
        puzzle_config = json.load(f)

    # Mock repositories and services (in a real system, these would be properly injected)
    # For this demo, we'll simulate the creation process

    print("🔧 Sequential Binary Adder Puzzle Setup")
    print("=" * 50)

    print("📋 Puzzle Configuration:")
    print(f"   Name: {puzzle_config['puzzle']['name']}")
    print(f"   Description: {puzzle_config['puzzle']['description']}")
    print(f"   Budget: {puzzle_config['puzzle']['budget']}")
    print(f"   Gate Set: {puzzle_config['puzzle']['default_gate_set']}")
    print(f"   Input: {puzzle_config['puzzle']['input']}")
    print(f"   State: {puzzle_config['puzzle']['state']}")
    print(f"   Outputs: {puzzle_config['puzzle']['outputs']}")
    print(f"   Initial State: {puzzle_config['puzzle']['initial_state']}")
    print(f"   Type: {puzzle_config['puzzle']['type']}")

    print(f"\n🧪 Test Cases ({len(puzzle_config['test_cases'])}):")
    for i, tc in enumerate(puzzle_config['test_cases'], 1):
        input_stream = tc['input_stream']
        out_stream = tc['expected_output_stream']['OUT']
        cout_stream = tc['expected_output_stream']['C_out']
        print(f"   {i}. Input: {input_stream}")
        print(f"      OUT: {out_stream}")
        print(f"      C_out: {cout_stream}")

    print("\n✅ Puzzle configuration loaded successfully!")
    print("\n📝 To integrate this puzzle into the system:")
    print("   1. Run the backend server")
    print("   2. Use the API to create the puzzle with the above configuration")
    print("   3. Test the puzzle with the provided test cases")

if __name__ == "__main__":
    create_sequential_adder_puzzle()