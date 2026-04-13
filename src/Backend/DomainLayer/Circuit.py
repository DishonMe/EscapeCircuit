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
    is_arsenal: bool = False
    basic_gates: str = ""  # JSON list of basic gates used
    truth_table: str = ""  # JSON dict of truth table
    num_inputs: int = 0  # Number of inputs (for arsenal pieces)
    num_outputs: int = 0  # Number of outputs (for arsenal pieces)
    puzzle_id: int | None = None  # For puzzle-specific custom pieces
    description: str = ""  # Description of the component (for Arsenal pieces)

    def __post_init__(self) -> None:
        if self.id < 0:
            raise ValidationError("Circuit.id cannot be negative")
        if self.user_id < 0:
            raise ValidationError("Circuit.user_id cannot be negative")
        if not self.name or not self.name.strip():
            raise ValidationError("Circuit.name is required")
        if self.cost < 0:
            raise ValidationError("Circuit.cost cannot be negative")
        
        # For puzzle-specific custom pieces (puzzle_id is set), structure_json can be empty
        if self.puzzle_id is None:
            if not self.structure_json or not self.structure_json.strip():
                raise ValidationError("Circuit.structure_json is required")
            try:
                json.loads(self.structure_json)
            except (json.JSONDecodeError, ValueError):
                raise ValidationError("Circuit.structure_json must be valid JSON")
        
        # Validate arsenal-specific fields if it's an arsenal piece
        if self.is_arsenal:
            # For puzzle-specific custom pieces, basic_gates and structure_json can be empty
            if self.puzzle_id is None:
                if not self.basic_gates or not self.basic_gates.strip():
                    raise ValidationError("Circuit.basic_gates is required for arsenal pieces")
                try:
                    gates = json.loads(self.basic_gates)
                    if not isinstance(gates, list):
                        raise ValidationError("Circuit.basic_gates must be a JSON list")
                except (json.JSONDecodeError, ValueError):
                    raise ValidationError("Circuit.basic_gates must be valid JSON")
            
            if not self.truth_table or not self.truth_table.strip():
                raise ValidationError("Circuit.truth_table is required for arsenal pieces")
            try:
                tt = json.loads(self.truth_table)
                if not isinstance(tt, dict):
                    raise ValidationError("Circuit.truth_table must be a JSON dict")
            except (json.JSONDecodeError, ValueError):
                raise ValidationError("Circuit.truth_table must be valid JSON")

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
            "is_arsenal": self.is_arsenal,
            "basic_gates": self.basic_gates,
            "truth_table": self.truth_table,
            "num_inputs": self.num_inputs,
            "num_outputs": self.num_outputs,
            "puzzle_id": self.puzzle_id,
            "description": self.description,
        }

    def to_circuit_component(self) -> dict:
        """Convert arsenal piece or custom piece to CircuitComponent format for display/placement"""
        total_pins = self.num_inputs + self.num_outputs
        
        # Parse basic_gates to get list of gate types
        used_basic_types = []
        if self.basic_gates:
            try:
                gates = json.loads(self.basic_gates)
                used_basic_types = gates if isinstance(gates, list) else []
            except (json.JSONDecodeError, ValueError):
                used_basic_types = []
        
        # Parse solution from structure_json
        solution = None
        try:
            structure = json.loads(self.structure_json) if self.structure_json else {}
            solution = structure
        except (json.JSONDecodeError, ValueError):
            solution = None
        
        return {
            "id": str(self.id),  # Use circuit ID as component ID for placement
            "type": self.name,  # Use circuit name as the type/label
            "cost": int(self.cost),
            "pins": total_pins,
            "basic_gates": self.basic_gates,
            "truth_table": self.truth_table,
            "is_arsenal": True,
            "num_inputs": self.num_inputs,
            "num_outputs": self.num_outputs,
            "puzzle_id": self.puzzle_id,  # Non-null indicates custom piece, null indicates arsenal piece
            "used_basic_types": used_basic_types,  # Array of gate types
            "solution": solution,  # The component's internal structure
            "hide_internal_structure": False,  # Default: show internal structure (can be customized later)
            "description": self.description,  # Component description from database
        }

    @staticmethod
    def from_dict(d: dict) -> "Circuit":
        return Circuit(
            id=int(d.get("id", 0)),
            user_id=d["user_id"],
            name=d["name"],
            cost=d["cost"],
            structure_json=d["structure_json"],
            is_arsenal=d.get("is_arsenal", False),
            basic_gates=d.get("basic_gates", ""),
            truth_table=d.get("truth_table", ""),
            num_inputs=d.get("num_inputs", 0),
            num_outputs=d.get("num_outputs", 0),
            puzzle_id=d.get("puzzle_id"),
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