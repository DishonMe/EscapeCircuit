#!/usr/bin/env python3
"""
Script to create and publish the Half Adder puzzle in the EscapeCircuit system.
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

def create_half_adder_puzzle():
    """Create the Half Adder puzzle in the system"""

    # Load puzzle configuration from JSON
    with open('riddle_02_half_adder_config.json', 'r') as f:
        puzzle_config = json.load(f)

    # Mock repositories and services (in a real system, these would be properly injected)
    # For this demo, we'll simulate the creation process

    print("🔧 Half Adder Puzzle Setup")
    print("=" * 40)

    print("📋 Puzzle Configuration:")
    print(f"   Name: {puzzle_config['puzzle']['name']}")
    print(f"   Description: {puzzle_config['puzzle']['description']}")
    print(f"   Budget: {puzzle_config['puzzle']['budget']}")
    print(f"   Gate Set: {puzzle_config['puzzle']['default_gate_set']}")
    print(f"   Inputs: {puzzle_config['puzzle']['inputs']}")
    print(f"   Outputs: {puzzle_config['puzzle']['outputs']}")

    print(f"\n🧪 Test Cases ({len(puzzle_config['test_cases'])}):")
    for i, tc in enumerate(puzzle_config['test_cases'], 1):
        inputs = tc['inputs']
        outputs = tc['expected_outputs']
        print(f"   {i}. {inputs} → {outputs}")

    print("\n✅ Puzzle configuration loaded successfully!")
    print("\n📝 To integrate this puzzle into the system:")
    print("   1. Run the backend server")
    print("   2. Use the API to create the puzzle with the above configuration")
    print("   3. Test the puzzle with the provided test cases")

if __name__ == "__main__":
    create_half_adder_puzzle()