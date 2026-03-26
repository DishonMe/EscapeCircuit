def test_uses_xor_gate(solution):
    """Check specific gate usage"""
    components = solution.get('placedComponents', [])
    components2 = solution.get('placed', [])
    has_xor = any(c.get('componentId') == 'XOR' for c in components + components2)
    if not has_xor:
        raise Exception("Solution must use at least one XOR gate")
    
def run_tests(solution):
    test_uses_xor_gate(solution)


## Note: The above code is a sample test case for a puzzle solution.
## It checks if the solution uses at least one XOR gate.