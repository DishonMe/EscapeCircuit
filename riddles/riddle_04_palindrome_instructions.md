# Palindrome Detector Instructions

## Objective
Design a digital circuit that checks if a 4-bit input sequence ($b_1, b_2, b_3, b_4$) is a palindrome.

## What is a Palindrome?
A palindrome is a sequence that reads the same forwards and backwards.
For a 4-bit sequence $b_1 b_2 b_3 b_4$, it is a palindrome if:
- $b_1 = b_4$
- AND
- $b_2 = b_3$

## Examples
- `0110` -> **True** (reads 0110 backwards)
- `1001` -> **True** (reads 1001 backwards)
- `0000` -> **True**
- `1100` -> **False** (reads 0011 backwards)
- `1010` -> **False** (reads 0101 backwards)

## Outputs
- **is_palindrome**: 1 if the input is a palindrome, 0 otherwise.
