from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .Exceptions import ValidationError
from .Utils import utcnow, ensure_non_negative_int, ensure_non_empty


@dataclass(slots=True)
class SolveAttempt:
    id: int 
    puzzle_id: int
    user_id: int
    circuit_id: Optional[int] = None
    time_used_seconds: Optional[int] = None
    cost_used: Optional[int] = None
    submitted_structure_json: Optional[str] = None

    started_at: datetime = field(default_factory=utcnow)
    submitted_at: Optional[datetime] = None

    passed: Optional[bool] = None
    fail_reason: Optional[str] = None

    clues_used: int = 0
    clue_penalty_seconds: int = 0

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("SolveAttempt.id", self.id)
        self.puzzle_id = ensure_non_negative_int("SolveAttempt.puzzle_id", self.puzzle_id)
        self.user_id = ensure_non_negative_int("SolveAttempt.user_id", self.user_id)

    def mark_submitted(self, passed: bool, circuit_id: Optional[str] = None, fail_reason: Optional[str] = None) -> None:
        # Safety check: don't mark as submitted if no circuit_id is set
        if not circuit_id and not self.circuit_id:
            raise ValueError("Cannot mark attempt as submitted without a circuit_id")
        self.submitted_at = utcnow()
        self.passed = bool(passed)
        self.circuit_id = circuit_id or self.circuit_id
        self.fail_reason = None if passed else (fail_reason or "unknown")

    @property
    def elapsed_seconds(self) -> Optional[int]:
        if self.submitted_at is None:
            return None
        delta = self.submitted_at - self.started_at
        return max(0, int(delta.total_seconds()))

    def attempted_minutes(self) -> float:
        end = self.submitted_at or utcnow()
        delta = end - self.started_at
        return max(0.0, delta.total_seconds() / 60.0)

    def to_dict(self) -> dict:
        return {
            "id": int(self.id),
            "puzzle_id": int(self.puzzle_id),
            "user_id": int(self.user_id),
            "circuit_id": self.circuit_id,
            "started_at": self.started_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "passed": self.passed,
            "fail_reason": self.fail_reason,
            "submitted_structure_json": self.submitted_structure_json,
            "clues_used": int(self.clues_used or 0),
            "clue_penalty_seconds": int(self.clue_penalty_seconds or 0),
        }

    @staticmethod
    def from_dict(d: dict) -> "SolveAttempt":
        from datetime import datetime
        return SolveAttempt(
            id=int(d.get("id", 0)),
            puzzle_id=int(d["puzzle_id"]),
            user_id=int(d["user_id"]),
            circuit_id=d.get("circuit_id"),
            started_at=datetime.fromisoformat(d["started_at"]) if "started_at" in d else utcnow(),
            submitted_at=datetime.fromisoformat(d["submitted_at"]) if d.get("submitted_at") else None,
            passed=d.get("passed"),
            fail_reason=d.get("fail_reason"),
            submitted_structure_json=d.get("submitted_structure_json"),
        )

    # --- getters ---
    def get_id(self) -> int: return self.id
    def get_puzzle_id(self) -> int: return self.puzzle_id
    def get_user_id(self) -> int: return self.user_id
    def get_circuit_id(self): return self.circuit_id
    def get_started_at(self): return self.started_at
    def get_submitted_at(self): return self.submitted_at
    def get_passed(self): return self.passed
    def get_fail_reason(self): return self.fail_reason

    # --- setters ---
    def set_puzzle_id(self, value: int) -> None:
        self.puzzle_id = ensure_non_negative_int("SolveAttempt.puzzle_id", value)

    def set_user_id(self, value: int) -> None:
        self.user_id = ensure_non_negative_int("SolveAttempt.user_id", value)

    def set_circuit_id(self, value) -> None:
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValidationError("SolveAttempt.circuit_id must be a non-empty string or None")
        self.circuit_id = value

    def set_started_at(self, value) -> None:
        self.started_at = value

    def set_submitted_at(self, value) -> None:
        self.submitted_at = value

    def set_passed(self, value) -> None:
        if value is not None and not isinstance(value, bool):
            raise ValidationError("SolveAttempt.passed must be bool or None")
        self.passed = value

    def set_fail_reason(self, value) -> None:
        if value is not None and not isinstance(value, str):
            raise ValidationError("SolveAttempt.fail_reason must be str or None")
        self.fail_reason = value
