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
    created_at: datetime = field(default_factory=utcnow)

    def set_puzzle_id(self, value: int) -> None:
        self.puzzle_id = ensure_non_negative_int("PuzzleTestCase.puzzle_id", value)

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("PuzzleTestCase.id", self.id)
        self.puzzle_id = ensure_non_negative_int("PuzzleTestCase.puzzle_id", self.puzzle_id)
        if not self.inputs:
            raise ValidationError("PuzzleTestCase.inputs cannot be empty")
        if not self.expected_outputs:
            raise ValidationError("PuzzleTestCase.expected_outputs cannot be empty")

        for k, v in self.inputs.items():
            if v not in (0, 1):
                raise ValidationError(f"Input '{k}' must be 0/1")
        for k, v in self.expected_outputs.items():
            if v not in (0, 1):
                raise ValidationError(f"Output '{k}' must be 0/1")

    def to_dict(self) -> dict:
        return {
            "id": int(self.id),
            "puzzle_id": int(self.puzzle_id),
            "kind": self.kind.value,
            "inputs": dict(self.inputs),
            "expected_outputs": dict(self.expected_outputs),
            "created_at": self.created_at.isoformat(),
        }

    @staticmethod
    def from_dict(d: dict) -> "PuzzleTestCase":
        from datetime import datetime
        return PuzzleTestCase(
            id=int(d.get("id", 0)),
            puzzle_id=int(d["puzzle_id"]),
            kind=TestCaseKind(d["kind"]),
            inputs=dict(d["inputs"]),
            expected_outputs=dict(d["expected_outputs"]),
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

