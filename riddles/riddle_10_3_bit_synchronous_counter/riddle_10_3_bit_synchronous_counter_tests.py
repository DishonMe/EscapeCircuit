def test_requires_dffs(solution):
    """
    Ensure the user actually used D-Flip-Flops to build the memory.
    A 3-bit counter inherently requires 3 bits of state.
    """
    # Extract the placed components from the solution JSON
    components = solution.get('circuit', {}).get('placed', [])
    
    # Count how many DFFs were used
    dff_count = sum(1 for c in components if c.get('componentId') == 'DFF')
    
    if dff_count < 3:
        raise Exception(f"A 3-bit counter requires at least 3 D-Flip-Flops (DFF) to store the state. You only used {dff_count}. Try rethinking your memory structure!")

def test_no_hardcoded_constants(solution):
    """
    Bonus check: ensure they didn't just wire inputs to specific gates 
    to bypass logic (though stream tests usually catch this).
    """
    components = solution.get('circuit', {}).get('placed', [])
    if len(components) == 0:
        raise Exception("Your circuit is empty!")

# REQUIRED: The main function that the system calls
def run_tests(solution):
    """Main test runner"""
    test_requires_dffs(solution)
    test_no_hardcoded_constants(solution)