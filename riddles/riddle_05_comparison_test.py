import sys
sys.path.insert(0, '../src')

import pytest
import json

@pytest.fixture
def test_cases():
    """Test cases for 2-bit Comparator"""
    cases = []
    for a in range(4):
        for b in range(4):
            # Parse bits
            a1 = (a >> 1) & 1
            a0 = a & 1
            b1 = (b >> 1) & 1
            b0 = b & 1
            
            # Logic
            gt = 1 if a > b else 0
            eq = 1 if a == b else 0
            lt = 1 if a < b else 0
            
            cases.append({
                "inputs": {"A1": a1, "A0": a0, "B1": b1, "B0": b0},
                "expected": {"GT": gt, "EQ": eq, "LT": lt}
            })
    return cases

def test_truth_table_correctness(test_cases):
    """Verify comparator logic"""
    for case in test_cases:
        i = case["inputs"]
        val_a = (i["A1"] << 1) | i["A0"]
        val_b = (i["B1"] << 1) | i["B0"]
        
        e = case["expected"]
        
        assert e["GT"] == (1 if val_a > val_b else 0)
        assert e["EQ"] == (1 if val_a == val_b else 0)
        assert e["LT"] == (1 if val_a < val_b else 0)
