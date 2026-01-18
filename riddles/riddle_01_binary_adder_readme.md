# Binary Adder Riddle - Complete Setup Guide

This guide explains how to set up and use the Binary Adder quiz in the EscapeCircuit system.

## 🎯 Overview

The Binary Adder riddle challenges users to design a digital circuit that implements a **full adder** using only AND, NAND, and DELAY gates. A full adder adds three binary digits (two input bits A, B and a carry-in bit C_in) and produces a sum bit (S) and a carry-out bit (C_out).

## 📁 Files Created

### Backend Files
- `src/Backend/DomainLayer/Enums.py` - Added DELAY gate type
- `tests/test_binary_adder.py` - Comprehensive test suite
- `test_user_solution.py` - User solution validation script
- `setup_binary_adder_puzzle.py` - Setup and configuration script

### Frontend Files
- Modified `puzzle-workstation.tsx` - Added DELAY gate support and special instructions
- Modified `workstation-menu.tsx` - Added DELAY gate truth table

### Configuration Files
- `binary_adder_puzzle.json` - Puzzle definition with test cases
- `sample_correct_adder.json` - Example correct solution
- `docs/binary_adder_instructions.md` - Detailed instructions

## 🚀 Setup Instructions

### 1. Backend Setup
```bash
# Run the setup script to see configuration
python setup_binary_adder_puzzle.py

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
  "name": "Binary Adder Quiz",
  "description": "Design a full adder circuit using AND, NAND, and DELAY gates. Implement the sum and carry-out logic for two input bits and a carry-in bit.",
  "budget": 20,
  "default_gate_set": ["AND", "NAND", "DELAY"]
}
```

**Add Test Cases:**
```bash
POST /puzzles/{puzzle_id}/testcases
Content-Type: application/json

{
  "kind": "blackbox",
  "inputs": {"A": 0, "B": 0, "C_in": 0},
  "expected_outputs": {"S": 0, "C_out": 0}
}
```
Repeat for all 8 test cases defined in `binary_adder_puzzle.json`.

**Publish Puzzle:**
```bash
POST /puzzles/{puzzle_id}/publish
```

### 3. Frontend Integration
The frontend automatically supports the Binary Adder puzzle:

- DELAY gate is available in the component palette
- Special instructions appear when viewing puzzle info
- Truth table and hints are displayed for Binary Adder puzzles

## 🧪 Testing

### Run All Tests
```bash
cd /path/to/EscapeCircuit
python -m pytest tests/test_binary_adder.py -v
```

### Test User Solutions
```bash
python test_user_solution.py user_circuit.json
```

### Manual Testing
1. Start the frontend application
2. Navigate to puzzles list
3. Find "Binary Adder Quiz"
4. Click "Solve Puzzle"
5. Use the workstation to design circuits
6. Click "Check Solution" to validate

## 🎮 User Experience

### Puzzle Interface
- **Available Gates**: AND, NAND, DELAY (with costs: AND=10, NAND=12, DELAY=8)
- **Budget Limit**: 20 points
- **Inputs**: A, B, C_in (binary values 0/1)
- **Outputs**: S, C_out (must match truth table)

### Special Features
- **Truth Table Display**: Click puzzle info button to see the full adder truth table
- **Gate Information**: Hover over gates to see truth tables
- **Validation**: Automatic checking against all 8 test cases
- **Hints**: Instructions emphasize NAND universality

### Success Criteria
A solution passes when:
- All 8 input combinations produce correct outputs
- Only allowed gates (AND, NAND, DELAY) are used
- Circuit cost stays within budget
- All inputs and outputs are properly connected

## 🔧 Technical Details

### Circuit Evaluation
- Uses `eval_map` format for circuit representation
- Each test case maps input combinations to expected outputs
- Logic engine validates circuits against truth table

### Gate Specifications
- **AND**: 3 pins (2 inputs, 1 output), cost 10
- **NAND**: 3 pins (2 inputs, 1 output), cost 12
- **DELAY**: 2 pins (1 input, 1 output), cost 8

### Truth Table Reference
```
A B C_in | S C_out
0 0 0    | 0 0
0 0 1    | 1 0
0 1 0    | 1 0
0 1 1    | 0 1
1 0 0    | 1 0
1 0 1    | 0 1
1 1 0    | 0 1
1 1 1    | 1 1
```

## 🎯 Educational Value

This riddle teaches:
- Digital logic design principles
- Full adder implementation
- Universal gates (NAND completeness)
- Circuit optimization within constraints
- Boolean algebra applications

## 🐛 Troubleshooting

### Common Issues
1. **Import Errors**: Run `python setup_binary_adder_puzzle.py` to verify paths
2. **Gate Not Available**: Check that DELAY is added to BASIC_COMPONENTS
3. **Tests Failing**: Ensure `sys.path.insert(0, 'src')` in test files
4. **API Errors**: Verify puzzle is published and has test cases

### Debug Commands
```bash
# Check imports
python -c "import tests.test_binary_adder; print('OK')"

# Run specific test
python -m pytest tests/test_binary_adder.py::test_truth_table_correctness -v

# Validate sample solution
python test_user_solution.py sample_correct_adder.json
```

## 📚 Additional Resources

- `docs/binary_adder_instructions.md` - Detailed puzzle instructions
- `binary_adder_puzzle.json` - Complete puzzle configuration
- `sample_correct_adder.json` - Working solution example
- Test files provide comprehensive validation framework

The Binary Adder riddle is now fully integrated into the EscapeCircuit system! 🎉