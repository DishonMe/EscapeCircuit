# Sequential Binary Adder Quiz Instructions

## Objective
Design a sequential digital circuit that implements a **bit-serial binary adder** using only the following gate types:
- AND gate
- NAND gate
- DFF gate

## What is a Sequential Binary Adder?
This is a Mealy machine that adds binary numbers one bit at a time over multiple clock cycles. Each cycle:
- Receives one input bit X
- Uses two DFFs to store state: D1 (previous bit) and D2 (two cycles ago)
- Produces two outputs: OUT (sum bit) and C_out (carry bit)

## Circuit Structure
**State Elements (DFFs):**
- D1: Stores the previous input bit (X[t-1])
- D2: Stores the input bit from two cycles ago (X[t-2])

**Combinational Logic (each cycle):**
- A = X (current input)
- B = D1 (previous input)
- C_in = D2 (input from two cycles ago)

**Logic Equations:**
- U = A OR B
- OUT = U XOR C_in
- C_out = U AND C_in

**State Updates (each clock cycle):**
- D1_next = X
- D2_next = D1

## Gate Descriptions
- **AND**: Outputs 1 only if both inputs are 1
- **NAND**: Outputs 0 only if both inputs are 1 (NOT of AND)
- **DFF**: D Flip-Flop that stores input value with one clock cycle delay

## Mealy Machine Truth Table
The circuit behavior is defined by the Mealy map over (X, D1, D2):

| X | D1 | D2 | OUT | C_out | D1_next | D2_next |
|---|---|----|-----|-------|---------|---------|
| 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1 | 0 | 0 | 1 | 0 | 1 | 0 |
| 0 | 0 | 1 | 1 | 0 | 0 | 0 |
| 1 | 0 | 1 | 0 | 1 | 1 | 0 |
| 0 | 1 | 0 | 1 | 0 | 0 | 1 |
| 1 | 1 | 0 | 1 | 0 | 1 | 1 |
| 0 | 1 | 1 | 0 | 1 | 0 | 1 |
| 1 | 1 | 1 | 0 | 1 | 1 | 1 |

## Requirements
- Your circuit must correctly implement the sequential adder for all state transitions
- Use only AND, NAND, and DFF gates
- Minimize the number of gates used (budget constraint may apply)
- Initial state: D1=0, D2=0
- Input: X (one bit per cycle)
- Outputs: OUT (sum), C_out (carry)

## Example Test Cases

**Example 1:**
Input stream: [1, 0, 1, 1, 0]
OUT stream: [1, 1, 0, 1, 0]
C_out stream: [0, 0, 1, 0, 1]

**Example 2:**
Input stream: [0, 0, 1, 0]
OUT stream: [0, 0, 1, 1]
C_out stream: [0, 0, 0, 0]

## Testing
Your solution will be tested against multiple input streams. Each test simulates the sequential behavior over several clock cycles, starting from the initial state. All tests must pass for the quiz to be completed successfully.