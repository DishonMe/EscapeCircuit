from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

from .Enums import TestCaseKind
from .Exceptions import ValidationError
from .Utils import utcnow, ensure_non_negative_int, ensure_non_empty, ensure_bit_dict


@dataclass(slots=True)
class PuzzleTestCase:
    id: int
    puzzle_id: int
    kind: TestCaseKind
    inputs: Dict[str, int]
    expected_outputs: Dict[str, int]
    input_stream: list = field(default_factory=list)
    expected_output_stream: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)

    def set_puzzle_id(self, value: int) -> None:
        self.puzzle_id = ensure_non_negative_int("PuzzleTestCase.puzzle_id", value)

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("PuzzleTestCase.id", self.id)
        self.puzzle_id = ensure_non_negative_int("PuzzleTestCase.puzzle_id", self.puzzle_id)
        
        # Either combinatorial (inputs/expected_outputs) or sequential (input_stream/expected_output_stream)
        is_combinatorial = self.inputs or self.expected_outputs
        is_sequential = self.input_stream or self.expected_output_stream
        
        if not is_combinatorial and not is_sequential:
            raise ValidationError("PuzzleTestCase must have either inputs/expected_outputs or input_stream/expected_output_stream")

        # Validate combinatorial format if present
        if is_combinatorial:
            if not self.inputs:
                raise ValidationError("PuzzleTestCase.inputs cannot be empty for combinatorial test case")
            if not self.expected_outputs:
                raise ValidationError("PuzzleTestCase.expected_outputs cannot be empty for combinatorial test case")

            for k, v in self.inputs.items():
                if isinstance(v, list):
                    if not all(x in (0, 1) for x in v):
                         raise ValidationError(f"Input '{k}' list must contain only 0/1")
                elif v not in (0, 1):
                    raise ValidationError(f"Input '{k}' must be 0/1")
            for k, v in self.expected_outputs.items():
                if isinstance(v, list):
                    if not all(x in (0, 1) for x in v):
                         raise ValidationError(f"Output '{k}' list must contain only 0/1")
                elif v not in (0, 1):
                    raise ValidationError(f"Output '{k}' must be 0/1")
        
        # Validate sequential format if present
        if is_sequential:
            if not self.input_stream:
                raise ValidationError("PuzzleTestCase.input_stream cannot be empty for sequential test case")
            if not self.expected_output_stream:
                raise ValidationError("PuzzleTestCase.expected_output_stream cannot be empty for sequential test case")
            
            # Validate input_stream
            for item in self.input_stream:
                if isinstance(item, dict):
                    for k, v in item.items():
                        if v not in (0, 1):
                            raise ValidationError(f"Input stream value '{k}' must be 0/1")
                elif item not in (0, 1):
                    raise ValidationError(f"Input stream value must be 0/1")
            
            # Validate expected_output_stream
            for k, v_list in self.expected_output_stream.items():
                if isinstance(v_list, list):
                    if not all(x in (0, 1) for x in v_list):
                        raise ValidationError(f"Output stream '{k}' must contain only 0/1")


    def to_dict(self) -> dict:
        return {
            "id": int(self.id),
            "puzzle_id": int(self.puzzle_id),
            "kind": self.kind.value,
            "inputs": dict(self.inputs),
            "expected_outputs": dict(self.expected_outputs),
            "input_stream": self.input_stream,
            "expected_output_stream": self.expected_output_stream,
            "created_at": self.created_at.isoformat(),
        }

    @staticmethod
    def from_dict(d: dict) -> "PuzzleTestCase":
        from datetime import datetime
        return PuzzleTestCase(
            id=int(d.get("id", 0)),
            puzzle_id=int(d["puzzle_id"]),
            kind=TestCaseKind(d["kind"]),
            inputs=dict(d.get("inputs", {})),
            expected_outputs=dict(d.get("expected_outputs", {})),
            input_stream=d.get("input_stream", []),
            expected_output_stream=d.get("expected_output_stream", {}),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else utcnow(),
        )

    # --- getters ---
    def get_id(self) -> int: return self.id
    def get_puzzle_id(self) -> int: return self.puzzle_id
    def get_kind(self) -> TestCaseKind: return self.kind
    def get_inputs(self) -> dict: return self.inputs
    def get_expected_outputs(self) -> dict: return self.expected_outputs
    def get_created_at(self) -> datetime: return self.created_at

    # --- setters ---
    def set_kind(self, value: TestCaseKind) -> None:
        if not isinstance(value, TestCaseKind):
            raise ValidationError("PuzzleTestCase.kind must be TestCaseKind")
        self.kind = value

    def set_inputs(self, value: dict) -> None:
        self.inputs = ensure_bit_dict("PuzzleTestCase.inputs", value)

    def set_expected_outputs(self, value: dict) -> None:
        self.expected_outputs = ensure_bit_dict("PuzzleTestCase.expected_outputs", value)

