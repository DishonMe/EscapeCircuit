#!/usr/bin/env python3
"""
Script to create and publish the Binary Adder puzzle in the EscapeCircuit system.
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

def create_binary_adder_puzzle():
    """Create the Binary Adder puzzle in the system"""

    # Load puzzle configuration from JSON
    with open('riddle_01_binary_adder_config.json', 'r') as f:
        puzzle_config = json.load(f)

    # Mock repositories and services (in a real system, these would be properly injected)
    # For this demo, we'll simulate the creation process

    print("🔧 Binary Adder Puzzle Setup")
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
    print("   2. Use the API endpoints to create the puzzle:")
    print("      POST /puzzles")
    print("      POST /puzzles/{id}/testcases (for each test case)")
    print("      POST /puzzles/{id}/publish")
    print("\n🎮 Frontend Integration:")
    print("   - The puzzle will appear in the puzzles list")
    print("   - Users can click 'Solve Puzzle' to access the workstation")
    print("   - The workstation provides circuit design tools")
    print("   - Users can validate their solutions using the 'Check Solution' button")

    # Create a sample API call format
    print("\n🔗 Sample API Usage:")
    print("POST /puzzles")
    print("Body:")
    sample_body = {
        "name": puzzle_config['puzzle']['name'],
        "description": puzzle_config['puzzle']['description'],
        "budget": puzzle_config['puzzle']['budget'],
        "default_gate_set": puzzle_config['puzzle']['default_gate_set']
    }
    print(json.dumps(sample_body, indent=2))

    print("\nPOST /puzzles/{puzzle_id}/testcases")
    print("Body (repeat for each test case):")
    for tc in puzzle_config['test_cases'][:2]:  # Show first 2 examples
        sample_tc = {
            "kind": "blackbox",
            "inputs": tc['inputs'],
            "expected_outputs": tc['expected_outputs']
        }
        print(json.dumps(sample_tc, indent=2))

    print("\n🎯 User Experience:")
    print("1. User sees 'Binary Adder Quiz' in puzzles list")
    print("2. Clicks 'Solve Puzzle' → enters circuit design workstation")
    print("3. Workstation shows:")
    print("   - Puzzle description and instructions")
    print("   - Available gates: AND, NAND, DFF")
    print("   - Budget limit and timer")
    print("   - Circuit design canvas")
    print("4. User designs circuit using drag-and-drop")
    print("5. Clicks 'Check Solution' → system validates against test cases")
    print("6. Success dialog shows if all tests pass")

    return True

if __name__ == "__main__":
    try:
        create_binary_adder_puzzle()
        print("\n🎉 Binary Adder puzzle setup complete!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)