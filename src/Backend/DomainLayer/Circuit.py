import json
from dataclasses import dataclass

from .Exceptions import ValidationError
from .Utils import ensure_non_empty, ensure_non_negative_int
from .Enums import GateType


@dataclass(slots=True)
class Circuit:
    id: int 
    user_id: int
    name: str
    cost: int
    structure_json: str

    def __post_init__(self) -> None:
        if self.id < 0:
            raise ValidationError("Circuit.id cannot be negative")
        if self.user_id < 0:
            raise ValidationError("Circuit.user_id cannot be negative")
        if not self.name or not self.name.strip():
            raise ValidationError("Circuit.name is required")
        if self.cost < 0:
            raise ValidationError("Circuit.cost cannot be negative")
        if not self.structure_json or not self.structure_json.strip():
            raise ValidationError("Circuit.structure_json is required")
        try:
            json.loads(self.structure_json)
        except (json.JSONDecodeError, ValueError):
            raise ValidationError("Circuit.structure_json must be valid JSON")

    def get_list_of_gates(self) -> list:
        structure = json.loads(self.structure_json)
        return structure.get("gates", [])

    def get_truth_table(self) -> dict:
        structure = json.loads(self.structure_json)
        if not structure.get("is_special", False):
            raise ValidationError("Circuit is not marked as special; truth table not available")
        return structure.get("truth_table", {})

    def get_string_representation(self) -> str:
        structure = json.loads(self.structure_json)
        return structure.get("construction_string", "")

    def calculate_cost(self, special_gates: dict) -> int:
        if self.cost > 0:
            return self.cost

        structure = json.loads(self.structure_json)
        gates = structure.get("gates", [])

        if GateType.DFF.value in gates:
            raise ValidationError("Circuit contains action 'DFF'circuit cannot have an action gate")
        
        num_basic_gates = len([gate for gate in gates if gate in [g.value for g in GateType]])
        cost = num_basic_gates
        
        special = [gate for gate in gates if gate not in [g.value for g in GateType]]
        for gate in special:
            if gate not in special_gates:
                raise ValidationError(f"Special gate '{gate}' not found in special_gates dictionary")
            cost += special_gates[gate].calculate_cost()
        
        return cost

    def to_dict(self) -> dict:
        return {
            "id": int(self.id),
            "user_id": self.user_id,
            "name": self.name,
            "cost": self.cost,
            "structure_json": self.structure_json,
        }

    @staticmethod
    def from_dict(d: dict) -> "Circuit":
        return Circuit(
            id=int(d.get("id", 0)),
            user_id=d["user_id"],
            name=d["name"],
            cost=d["cost"],
            structure_json=d["structure_json"],
        )

    # --- getters ---
    def get_id(self) -> int:
        return self.id

    def get_user_id(self) -> int:
        return self.user_id

    def get_name(self) -> str:
        return self.name

    def get_cost(self) -> int:
        return self.cost

    def get_structure_json(self) -> str:
        return self.structure_json

    # --- setters ---
    def set_name(self, value: str) -> None:
        self.name = ensure_non_empty("Circuit.name", value)

    def set_cost(self, value: int) -> None:
        self.cost = ensure_non_negative_int("Circuit.cost", value)

    def set_structure_json(self, value: str) -> None:
        value = ensure_non_empty("Circuit.structure_json", value)
        try:
            json.loads(value)
        except (json.JSONDecodeError, ValueError):
            raise ValidationError("Circuit.structure_json must be valid JSON")
        self.structure_json = value