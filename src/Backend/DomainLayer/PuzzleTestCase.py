from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

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
    gate_name: Optional[str] = None  # For GATE_LIMIT test cases: which gate type (e.g., "AND")
    gate_limit: Optional[int] = None  # For GATE_LIMIT test cases: max count allowed for that gate
    max_gate_count: Optional[int] = None  # For GATE_COUNT_LIMIT: total gate count limit
    min_cycles: Optional[int] = None  # For LATENCY_LIMIT: minimum cycles required
    max_cycles: Optional[int] = None  # For LATENCY_LIMIT: maximum cycles allowed
    created_at: datetime = field(default_factory=utcnow)

    def set_puzzle_id(self, value: int) -> None:
        self.puzzle_id = ensure_non_negative_int("PuzzleTestCase.puzzle_id", value)

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("PuzzleTestCase.id", self.id)
        self.puzzle_id = ensure_non_negative_int("PuzzleTestCase.puzzle_id", self.puzzle_id)
        
        # Gate limit type validation (GATE_LIMIT with gate_name and gate_limit)
        if self.kind == TestCaseKind.GATE_LIMIT:
            if not self.gate_name or not self.gate_limit:
                raise ValidationError("GATE_LIMIT test case must have gate_name and gate_limit specified")
            if self.gate_limit < 0:
                raise ValidationError(f"Gate limit for '{self.gate_name}' must be non-negative integer")
            return
        
        if self.kind == TestCaseKind.GATE_COUNT_LIMIT:
            if self.max_gate_count is None or self.max_gate_count <= 0:
                raise ValidationError("GATE_COUNT_LIMIT test case must have max_gate_count > 0")
            return
        
        if self.kind == TestCaseKind.LATENCY_LIMIT:
            if self.min_cycles is None and self.max_cycles is None:
                raise ValidationError("LATENCY_LIMIT test case must have min_cycles and/or max_cycles specified")
            if self.min_cycles is not None and self.min_cycles < 1:
                raise ValidationError("min_cycles must be >= 1")
            if self.max_cycles is not None and self.max_cycles < 1:
                raise ValidationError("max_cycles must be >= 1")
            if self.min_cycles is not None and self.max_cycles is not None and self.min_cycles > self.max_cycles:
                raise ValidationError("min_cycles cannot be greater than max_cycles")
            return
        
        # Blackbox/Whitebox validation
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
            "gate_name": self.gate_name,
            "gate_limit": self.gate_limit,
            "max_gate_count": self.max_gate_count,
            "min_cycles": self.min_cycles,
            "max_cycles": self.max_cycles,
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
            gate_name=d.get("gate_name"),
            gate_limit=d.get("gate_limit"),
            max_gate_count=d.get("max_gate_count"),
            min_cycles=d.get("min_cycles"),
            max_cycles=d.get("max_cycles"),
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

