import sys
sys.path.insert(0, '../src')

import pytest
import json

@pytest.fixture
def test_cases():
    """Test cases for Palindrome Detector"""
    cases = []
    for i in range(16):
        # Convert to 4-bit binary
        b1 = (i >> 3) & 1
        b2 = (i >> 2) & 1
        b3 = (i >> 1) & 1
        b4 = i & 1
        
        # Check palindrome property
        is_palindrome = 1 if (b1 == b4 and b2 == b3) else 0
        
        cases.append({
            "inputs": {"b1": b1, "b2": b2, "b3": b3, "b4": b4},
            "expected": {"is_palindrome": is_palindrome}
        })
    return cases

def test_truth_table_correctness(test_cases):
    """Verify that generated test cases are correct"""
    for case in test_cases:
        inputs = case["inputs"]
        b1, b2, b3, b4 = inputs["b1"], inputs["b2"], inputs["b3"], inputs["b4"]
        
        expected = (1 if ((b1 == b4) and (b2 == b3)) else 0)
        assert case["expected"]["is_palindrome"] == expected
