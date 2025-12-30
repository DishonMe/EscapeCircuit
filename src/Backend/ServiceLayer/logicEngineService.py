import json
from typing import Dict, Any, Set

from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.Exceptions import ValidationError


class logicEngineService:
    """
    Minimal evaluator + helpers for:
    - cost calculation
    - gate validation
    - essential conditions (has entry for each official input)
    """

    # ---------- existing evaluate ----------
    def evaluate(self, circuit: Circuit, inputs: Dict[str, int]) -> Dict[str, int]:
        data = self._load(circuit.structure_json)
        key = json.dumps(inputs, sort_keys=True)

        if isinstance(data.get("eval_map"), dict):
            if key not in data["eval_map"]:
                raise ValidationError("no eval_map entry for inputs")
            out = data["eval_map"][key]
            if not isinstance(out, dict):
                raise ValidationError("eval_map output must be dict")
            return {str(k): int(v) for k, v in out.items()}

        if isinstance(data.get("truth_table"), dict):
            tt = data["truth_table"]
            if key not in tt:
                raise ValidationError("truth_table missing entry")
            out = tt[key]
            if not isinstance(out, dict):
                raise ValidationError("truth_table output must be dict")
            return {str(k): int(v) for k, v in out.items()}

        raise ValidationError("logic engine format not supported")

    # ---------- NEW helpers used by services ----------
    def _load(self, structure_json: str) -> Dict[str, Any]:
        try:
            data = json.loads(structure_json)
        except Exception:
            raise ValidationError("invalid circuit json")
        if not isinstance(data, dict):
            raise ValidationError("invalid circuit json")
        return data

    def extract_used_gates(self, structure_json: str) -> Set[str]:
        """
        Flexible extraction to support multiple frontend schemas.
        Supported shapes (any of them):
        - {"used_gates": ["AND","NOT"]}
        - {"gates_counts": {"AND":3,"NOT":2}}
        - {"components":[{"type":"AND"}, ...]}
        """
        data = self._load(structure_json)

        if isinstance(data.get("used_gates"), list):
            return {str(x) for x in data["used_gates"]}

        if isinstance(data.get("gates_counts"), dict):
            return {str(k) for k in data["gates_counts"].keys()}

        if isinstance(data.get("components"), list):
            out = set()
            for c in data["components"]:
                if isinstance(c, dict) and "type" in c:
                    out.add(str(c["type"]))
            return out

        # fallback: no info
        return set()

    def compute_cost(self, structure_json: str) -> int:
        """
        ARD: cost = sum of basic gate counts + nested circuit full cost. :contentReference[oaicite:3]{index=3}
        We support:
        - gates_counts dict => sum(counts)
        - components list => len(components)
        - explicit cost/value fields if exist
        - optional nested_costs list => add them
        """
        data = self._load(structure_json)

        # explicit override if frontend already computed it safely
        for k in ("cost", "value", "computed_cost"):
            if k in data:
                try:
                    return int(data[k])
                except Exception:
                    pass

        total = 0

        if isinstance(data.get("gates_counts"), dict):
            for _, v in data["gates_counts"].items():
                try:
                    total += int(v)
                except Exception:
                    raise ValidationError("invalid gates_counts")

        elif isinstance(data.get("components"), list):
            total += len(data["components"])

        # nested circuits cost (if frontend provides)
        if isinstance(data.get("nested_costs"), list):
            for x in data["nested_costs"]:
                try:
                    total += int(x)
                except Exception:
                    raise ValidationError("invalid nested_costs")

        return int(total)

    def validate_gate_usage(self, structure_json: str, allowed_basic: Set[str]) -> None:
        used = self.extract_used_gates(structure_json)
        if not used:
            # allow empty for now (some puzzles may have 0 inputs)
            return
        illegal = used - set(allowed_basic)
        if illegal:
            raise ValidationError(f"illegal gates: {sorted(illegal)}")

    def has_entry_for_inputs(self, circuit: Circuit, inputs: Dict[str, int]) -> bool:
        data = self._load(circuit.structure_json)
        key = json.dumps(inputs, sort_keys=True)

        if isinstance(data.get("eval_map"), dict):
            return key in data["eval_map"]
        if isinstance(data.get("truth_table"), dict):
            return key in data["truth_table"]
        return False
