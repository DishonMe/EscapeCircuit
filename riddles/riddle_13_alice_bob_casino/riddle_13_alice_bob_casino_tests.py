import json

from Backend.DomainLayer.Circuit import Circuit
from Backend.ServiceLayer.logicEngineService import logicEngineService


def _extract_structure(solution):
    if not isinstance(solution, dict):
        return {"placedComponents": [], "components": [], "wires": []}

    placed_top = solution.get("placedComponents") or solution.get("components")
    if isinstance(placed_top, list):
        return {
            "placedComponents": placed_top,
            "components": placed_top,
            "wires": solution.get("wires") or [],
        }

    nested = solution.get("circuit", {})
    if isinstance(nested, dict):
        placed_nested = (
            nested.get("placedComponents")
            or nested.get("components")
            or nested.get("placed")
            or []
        )
        return {
            "placedComponents": placed_nested,
            "components": placed_nested,
            "wires": nested.get("wires") or [],
        }

    return {"placedComponents": [], "components": [], "wires": []}


def _get_or_create_circuit_and_engine(solution):
    """Cache circuit and engine to avoid recreating them for every stream."""
    if not hasattr(_get_or_create_circuit_and_engine, 'cache'):
        structure = _extract_structure(solution)
        circuit = Circuit(
            id=0,
            user_id=0,
            name="alice_bob_casino_candidate",
            cost=int(solution.get("totalCost", 0) or 0),
            structure_json=json.dumps(structure),
        )
        engine = logicEngineService()
        _get_or_create_circuit_and_engine.cache = (circuit, engine)
    return _get_or_create_circuit_and_engine.cache


def _simulate_stream(solution, stream, circuit=None, engine=None):
    if circuit is None or engine is None:
        circuit, engine = _get_or_create_circuit_and_engine(solution)

    state = {}
    outputs = []

    for step in stream:
        step_inputs = dict(step)
        step_inputs.update(state)
        result = engine.evaluate(circuit, step_inputs)

        outputs.append(int(result.get("A", 0)))

        next_state = {}
        for key, value in result.items():
            if isinstance(key, str) and key.endswith("_next"):
                next_state[key[:-5]] = int(value) if value is not None else 0
        state.update(next_state)

    return outputs


def _assert_stream(solution, stream, expected):
    actual = _simulate_stream(solution, stream)
    if actual != expected:
        raise Exception(f"Unexpected stream output. expected={expected}, actual={actual}")


def test_requires_stateful_solution(solution):
    structure = _extract_structure(solution)
    dff_count = sum(
        1 for component in structure.get("placedComponents", [])
        if component.get("componentId") == "DFF"
    )
    if dff_count < 1:
        raise Exception("This sequential puzzle needs at least one DFF for memory.")


def test_rounds_are_binary(solution):
    stream = [
        {"B": 0, "C": 0},
        {"B": 1, "C": 1},
        {"B": 0, "C": 0},
        {"B": 1, "C": 1},
        {"B": 0, "C": 0},
        {"B": 1, "C": 1},
        {"B": 0, "C": 0},
    ]

    outputs = _simulate_stream(solution, stream)
    if len(outputs) != 7:
        raise Exception(f"Expected 7 output cycles, got {len(outputs)}.")
    if any(bit not in (0, 1) for bit in outputs):
        raise Exception(f"Alice output must be binary, got {outputs}.")


def test_known_streams(solution):
    _assert_stream(
        solution,
        [{"B": 0, "C": 0}] * 7,
        [0, 0, 0, 0, 0, 0, 0],
    )
    _assert_stream(
        solution,
        [{"B": 1, "C": 1}] * 7,
        [0, 1, 1, 1, 1, 1, 1],
    )
    _assert_stream(
        solution,
        [
            {"B": 0, "C": 0},
            {"B": 1, "C": 1},
            {"B": 0, "C": 0},
            {"B": 1, "C": 1},
            {"B": 0, "C": 0},
            {"B": 1, "C": 1},
            {"B": 0, "C": 0},
        ],
        [0, 0, 1, 0, 0, 1, 0],
    )


def _clear_circuit_cache():
    """Clear the cached circuit and engine."""
    if hasattr(_get_or_create_circuit_and_engine, 'cache'):
        delattr(_get_or_create_circuit_and_engine, 'cache')


def test_all_bob_sequences(solution):
    """
    For each of the 2^7 casino sequences, find the best Bob sequence.
    Verify that Alice's circuit achieves at least 4 wins with the optimal Bob strategy.
    
    Bob's strategy:
    - B₀ = majority(C₁, C₂, C₃) — encodes which bit to use for rounds 1-3
    - B₁, B₂, B₃ — may be all the same (unanimous) or have 1 different (outlier)
      The differing bit signals Alice what to output for rounds 4-6
    - B₄ = majority(C₄, C₅, C₆) — encodes signal for final rounds
    - B₅, B₆ — may be unanimous or have 1 outlier
    
    Alice's decoding:
    - A₁-A₃: output delayed Bob (A_i = B_{i-1})
    - A₄-A₆: decode B₁,B₂,B₃
      - If unanimous: output that value
      - If one outlier: output the outlier value
    
    This validates that Alice's circuit correctly interprets Bob's encoded signal.
    """
    _clear_circuit_cache()
    circuit, engine = _get_or_create_circuit_and_engine(solution)

    # Pre-compute all bit sequences (MSB-first: bit 0 is leftmost/most significant)
    bit_sequences = {i: [(i >> (6 - j)) & 1 for j in range(7)] for i in range(128)}

    # Generate all 2^7 Casino sequences
    for casino_int in range(128):
        casino_bits = bit_sequences[casino_int]
        best_wins = 0
        best_bob_int = -1

        # Try all 2^7 Bob sequences for this casino
        for bob_int in range(128):
            bob_bits = bit_sequences[bob_int]

            # Evaluate circuit for this (bob, casino) pair
            state = {}
            wins = 0
            try:
                for i in range(7):
                    # Prepare input for this cycle
                    step_inputs = {"B": bob_bits[i], "C": casino_bits[i]}
                    step_inputs.update(state)
                    
                    # Evaluate circuit
                    result = engine.evaluate(circuit, step_inputs)
                    
                    # Get output and verify binary
                    output_bit = int(result.get("A", 0))
                    if output_bit not in (0, 1):
                        raise Exception(
                            f"Output {output_bit} is not binary at cycle {i} "
                            f"(bob={bob_int:07b}, casino={casino_int:07b})"
                        )
                    
                    # Count wins: round is won if A == B == C
                    if output_bit == bob_bits[i] == casino_bits[i]:
                        wins += 1
                    
                    # Update state for next cycle
                    for key, value in result.items():
                        if isinstance(key, str) and key.endswith("_next"):
                            state[key[:-5]] = int(value) if value is not None else 0

            except Exception as e:
                raise Exception(
                    f"Circuit evaluation failed for bob={bob_int:07b}, casino={casino_int:07b}: {str(e)}"
                )

            # Track best Bob sequence for this casino
            if wins > best_wins:
                best_wins = wins
                best_bob_int = bob_int

        # Verify this casino has at least one Bob sequence achieving 4+ wins
        if best_wins < 4:
            raise Exception(
                f"Casino sequence {casino_int:07b} has no Bob strategy winning 4+/7 "
                f"(best achievable: {best_wins}/7 with Bob={best_bob_int:07b})"
            )
    
    _clear_circuit_cache()


def run_tests(solution):
    test_requires_stateful_solution(solution)
    _clear_circuit_cache()
    test_rounds_are_binary(solution)
    _clear_circuit_cache()
    test_known_streams(solution)
    _clear_circuit_cache()
    test_all_bob_sequences(solution)