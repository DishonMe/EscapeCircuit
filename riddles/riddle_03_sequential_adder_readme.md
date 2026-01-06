# Sequential Binary Adder Riddle - Complete Setup Guide

This guide explains how to set up and use the Sequential Binary Adder quiz in the EscapeCircuit system.

## 🎯 Overview

The Sequential Binary Adder riddle challenges users to design a digital circuit that implements a **bit-serial binary adder** using only AND, NAND, and DFF gates. This is a Mealy machine that processes one bit per clock cycle, using DFFs to maintain state across cycles.

## 📁 Files Created

### Backend Files
- `src/Backend/DomainLayer/Enums.py` - Added DFF gate type
- `tests/test_sequential_adder.py` - Comprehensive test suite for sequential behavior
- `test_user_solution.py` - User solution validation script
- `setup_sequential_adder_puzzle.py` - Setup and configuration script

### Frontend Files
- Modified `puzzle-workstation.tsx` - Added DFF gate support and sequential instructions
- Modified `workstation-menu.tsx` - Added DFF gate truth table and sequential state display

### Configuration Files
- `sequential_adder_puzzle.json` - Puzzle definition with sequential test cases
- `sample_correct_sequential_adder.json` - Example correct solution with Mealy map
- `docs/sequential_adder_instructions.md` - Detailed instructions for sequential logic

## 🚀 Setup Instructions

### 1. Backend Setup
```bash
# Run the setup script to see configuration
python setup_sequential_adder_puzzle.py

# Start the backend server
# (Follow your normal backend startup procedure)
```

### 2. Create the Puzzle via API
Use the API endpoints to create the puzzle:

**Create Puzzle:**
```bash
POST /puzzles
Content-Type: application/json

{
  "name": "Sequential Binary Adder Quiz",
  "description": "Design a sequential circuit that adds binary numbers bit by bit over multiple clock cycles using DFF gates for state. Each cycle receives one input bit X, and produces sum (OUT) and carry (C_out) outputs.",
  "budget": 15,
  "default_gate_set": ["AND", "NAND", "DFF"],
  "type": "sequential_riddle"
}