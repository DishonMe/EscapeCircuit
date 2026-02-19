# Binary Adder Quiz Instructions

## Objective
Design a digital circuit that implements a **full adder** using only the following gate types:
- AND gate
- NAND gate
- DFF gate

## What is a Full Adder?
A full adder is a digital circuit that adds three binary digits: two input bits (A and B) and a carry-in bit (C_in). It produces two outputs:
- Sum (S): The least significant bit of the sum
- Carry-out (C_out): The carry bit to the next higher position

The truth table for a full adder is:

| A | B | C_in | S | C_out |
|---|---|------|----|--------|
| 0 | 0 | 0    | 0  | 0      |
| 0 | 0 | 1    | 1  | 0      |
| 0 | 1 | 0    | 1  | 0      |
| 0 | 1 | 1    | 0  | 1      |
| 1 | 0 | 0    | 1  | 0      |
| 1 | 0 | 1    | 0  | 1      |
| 1 | 1 | 0    | 0  | 1      |
| 1 | 1 | 1    | 1  | 1      |

## Gate Descriptions
- **AND**: Outputs 1 only if both inputs are 1
- **NAND**: Outputs 0 only if both inputs are 1 (NOT of AND)
- **DFF**: Passes the input signal unchanged but with a one-time-unit delay

## Requirements
- Your circuit must correctly implement the full adder for all 8 possible input combinations
- Use only AND, NAND, and DFF gates
- Minimize the number of gates used (budget constraint may apply)
- The circuit should have inputs: A, B, C_in
- The circuit should have outputs: S, C_out

## Hints
- NAND gates are universal - you can build any logic function with NAND gates
- DFF gates can be used to create feedback or timing-dependent behavior if needed
- Think about how to combine these gates to create XOR and other operations

## Testing
Your solution will be tested against all possible input combinations. All tests must pass for the quiz to be completed successfully.