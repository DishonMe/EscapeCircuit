# Half Adder Riddle - Complete Setup Guide

This guide explains how to set up and use the Half Adder quiz in the EscapeCircuit system.

## 🎯 Overview

The Half Adder riddle challenges users to design a digital circuit that implements a **half adder** using only AND, NAND, and DFF gates. A half adder adds two binary digits (two input bits A and B) and produces a sum bit (S) and a carry-out bit (C_out).

## 📁 Files Created

### Backend Files
- `src/Backend/DomainLayer/Enums.py` - Added DFF gate type
- `tests/test_half_adder.py` - Comprehensive test suite
- `test_user_solution.py` - User solution validation script
- `setup_half_adder_puzzle.py` - Setup and configuration script

### Frontend Files
- Modified `puzzle-workstation.tsx` - Added DFF gate support and special instructions
- Modified `workstation-menu.tsx` - Added DFF gate truth table

### Configuration Files
- `half_adder_puzzle.json` - Puzzle definition with test cases
- `sample_correct_half_adder.json` - Example correct solution
- `docs/half_adder_instructions.md` - Detailed instructions

## 🚀 Setup Instructions

### 1. Backend Setup
```bash
# Run the setup script to see configuration
python setup_half_adder_puzzle.py

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
  "name": "Half Adder Quiz",
  "description": "Design a half adder circuit using AND, NAND, and DFF gates. Implement the sum and carry-out logic for two input bits.",
  "budget": 10,
  "default_gate_set": ["AND", "NAND", "DFF"]
}