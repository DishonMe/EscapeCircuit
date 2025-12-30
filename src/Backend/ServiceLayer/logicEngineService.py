import json
from typing import Dict

from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.Exceptions import ValidationError


class logicEngineService:
    """
    Minimal evaluator:
    Expects circuit.structure_json to contain:
      - eval_map: { json.dumps(inputs, sort_keys=True): {outputs...} }
    or:
      - truth_table (for special) with same structure
    """

    def evaluate(self, circuit: Circuit, inputs: Dict[str, int]) -> Dict[str, int]:
        try:
            data = json.loads(circuit.structure_json)
        except Exception:
            raise ValidationError("invalid circuit json")

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
