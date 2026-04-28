import json
from collections import defaultdict

from Backend.DomainLayer.Circuit import Circuit
from Backend.ServiceLayer.logicEngineService import logicEngineService


def _extract_runtime_structure(solution):
    """Support both frontend/runtime payload shape and sample-solution shape."""
    if not isinstance(solution, dict):
        return {"placedComponents": [], "components": [], "wires": []}

    placed_top = solution.get("placedComponents") or solution.get("components")
    if isinstance(placed_top, list):
        structure = {
            "placedComponents": placed_top,
            "components": placed_top,
            "wires": solution.get("wires") or [],
        }
        if isinstance(solution.get("_arsenal_pieces"), dict):
            structure["_arsenal_pieces"] = solution["_arsenal_pieces"]
        return structure

    circuit = solution.get("circuit", {})
    if isinstance(circuit, dict):
        placed_nested = (
            circuit.get("placedComponents")
            or circuit.get("components")
            or circuit.get("placed")
            or []
        )
        return {
            "placedComponents": placed_nested,
            "components": placed_nested,
            "wires": circuit.get("wires") or [],
        }

    return {"placedComponents": [], "components": [], "wires": []}


def _simulate_output_sequence(solution, steps=16):
    structure = _extract_runtime_structure(solution)
    placed = structure.get("placedComponents", [])

    dff_ids = [
        component.get("id")
        for component in placed
        if component.get("componentId") == "DFF" and component.get("id")
    ]

    if len(dff_ids) < 4:
        raise Exception(
            f"This puzzle requires state. Use at least 4 DFFs; found {len(dff_ids)}."
        )

    circuit = Circuit(
        id=0,
        user_id=0,
        name="debruijn_candidate",
        cost=int(solution.get("totalCost", 0) or 0),
        structure_json=json.dumps(structure),
    )
    engine = logicEngineService()

    state = {dff_id: 0 for dff_id in dff_ids}
    bits = []

    for _ in range(steps):
        result = engine.evaluate(circuit, state)

        y = result.get("Y")
        if y not in (0, 1):
            raise Exception("Output Y must be binary (0 or 1) on every cycle.")

        bits.append(str(int(y)))

        next_state = {}
        for key, value in result.items():
            if isinstance(key, str) and key.endswith("_next"):
                next_state[key[:-5]] = int(value) if value is not None else 0

        for dff_id in dff_ids:
            state[dff_id] = next_state.get(dff_id, state[dff_id])

    return "".join(bits)


def verify_debruijn(sequence, n=4):
    if len(sequence) != 2**n:
        all_patterns = {format(i, f"0{n}b") for i in range(2**n)}
        return False, all_patterns, set()

    seen = defaultdict(int)
    length = len(sequence)

    for i in range(length):
        if i + n <= length:
            pattern = sequence[i : i + n]
        else:
            pattern = sequence[i:] + sequence[: i + n - length]
        seen[pattern] += 1

    all_patterns = {format(i, f"0{n}b") for i in range(2**n)}
    missing = all_patterns - set(seen.keys())
    duplicates = {pattern for pattern, count in seen.items() if count > 1}

    return len(missing) == 0 and len(duplicates) == 0, missing, duplicates


def verify_prefer_one_construction(sequence):
    seen_states = {"0000"}
    current = "0000"

    for bit in sequence:
        try_one = current[1:] + "1"

        if try_one not in seen_states:
            if bit != "1":
                return False
            current = try_one
        else:
            if bit != "0":
                return False
            current = current[1:] + "0"

        seen_states.add(current)

    return len(seen_states) == 16


# REQUIRED ENTRY POINT

def run_tests(solution):
    sequence = _simulate_output_sequence(solution, steps=16)

    valid, missing, duplicates = verify_debruijn(sequence, n=4)
    if not valid:
        raise Exception(
            "Output is not a valid order-4 De Bruijn sequence. "
            f"sequence={sequence}, missing={sorted(missing)}, duplicates={sorted(duplicates)}"
        )

    if not verify_prefer_one_construction(sequence):
        raise Exception(
            "Sequence is De Bruijn but does not follow prefer-one construction from state 0000. "
            f"sequence={sequence}"
        )
