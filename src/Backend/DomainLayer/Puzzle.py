from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set

from .Enums import GateType, PuzzleStatus
from .Exceptions import ValidationError
from .Utils import utcnow, ensure_non_empty, ensure_non_negative_int, ensure_optional_positive_int, ensure_gate_set

@dataclass(slots=True)
class Puzzle:
    id: int 
    name: str
    creator_user_id: str
    description: str = ""
    status: PuzzleStatus = PuzzleStatus.DRAFT

    budget: int = 0
    time_limit_seconds: Optional[int] = None
    default_gate_set: Set[GateType] = field(default_factory=set)

    rating_count: int = 0
    avg_difficulty: float = 0.0
    avg_fun: float = 0.0
    avg_clearness: float = 0.0

    created_at: datetime = field(default_factory=utcnow)

    #### will implement later - not in alpha ###
    # for special gates that the user created for this puzzle
    # special_gates: Set[str] = field(default_factory=set, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("Puzzle.id", self.id)
        if not self.name or not self.name.strip():
            raise ValidationError("Puzzle.name is required")
        if not self.creator_user_id:
            raise ValidationError("Puzzle.creator_user_id is required")
        if self.budget < 0:
            raise ValidationError("Puzzle.budget cannot be negative")
        if self.time_limit_seconds is not None and self.time_limit_seconds <= 0:
            raise ValidationError("Puzzle.time_limit_seconds must be > 0 when set")

    def enforce_budget(self, circuit_cost: int) -> None:
        if circuit_cost > self.budget:
            raise ValidationError(f"Circuit cost {circuit_cost} exceeds puzzle budget {self.budget}")

    def publish(self) -> None:
        # Add stronger checks later (self-solve, testcases exist, unique name, etc.)
        self.status = PuzzleStatus.PUBLISHED

    def unpublish(self) -> None:
        if self.status == PuzzleStatus.PUBLISHED:
            self.status = PuzzleStatus.UNPUBLISHED

    def to_dict(self) -> dict:
        return {
            "id": int(self.id),
            "name": self.name,
            "creator_user_id": self.creator_user_id,
            "description": self.description,
            "status": self.status.value,
            "budget": self.budget,
            "time_limit_seconds": self.time_limit_seconds,
            "default_gate_set": [g.value for g in sorted(self.default_gate_set, key=lambda x: x.value)],
            "rating_count": self.rating_count,
            "avg_difficulty": self.avg_difficulty,
            "avg_fun": self.avg_fun,
            "avg_clearness": self.avg_clearness,
            "created_at": self.created_at.isoformat(),
        }

    @staticmethod
    def from_dict(d: dict) -> "Puzzle":
        from datetime import datetime
        return Puzzle(
            id=int(d.get("id", 0)),
            name=d["name"],
            creator_user_id=d["creator_user_id"],
            description=d.get("description", ""),
            status=PuzzleStatus(d.get("status", PuzzleStatus.DRAFT.value)),
            budget=int(d.get("budget", 0)),
            time_limit_seconds=d.get("time_limit_seconds", None),
            default_gate_set={GateType(x) for x in d.get("default_gate_set", [])},
            rating_count=int(d.get("rating_count", 0)),
            avg_difficulty=float(d.get("avg_difficulty", 0.0)),
            avg_fun=float(d.get("avg_fun", 0.0)),
            avg_clearness=float(d.get("avg_clearness", 0.0)),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else utcnow(),
        )
    

    # --- getters ---
    def get_id(self) -> int: return self.id
    def get_name(self) -> str: return self.name
    def get_creator_user_id(self) -> str: return self.creator_user_id
    def get_description(self) -> str: return self.description
    def get_status(self) -> PuzzleStatus: return self.status
    def get_budget(self) -> int: return self.budget
    def get_time_limit_seconds(self): return self.time_limit_seconds
    def get_default_gate_set(self): return self.default_gate_set
    def get_rating_count(self) -> int: return self.rating_count
    def get_avg_difficulty(self) -> float: return self.avg_difficulty
    def get_avg_fun(self) -> float: return self.avg_fun
    def get_avg_clearness(self) -> float: return self.avg_clearness
    def get_created_at(self): return self.created_at

    # --- setters ---
    def set_name(self, value: str) -> None:
        self.name = ensure_non_empty("Puzzle.name", value)

    def set_creator_user_id(self, value: str) -> None:
        self.creator_user_id = ensure_non_empty("Puzzle.creator_user_id", value)

    def set_description(self, value: str) -> None:
        self.description = value or ""

    def set_status(self, value: PuzzleStatus) -> None:
        if not isinstance(value, PuzzleStatus):
            raise ValidationError("Puzzle.status must be PuzzleStatus")
        self.status = value

    def set_budget(self, value: int) -> None:
        self.budget = ensure_non_negative_int("Puzzle.budget", value)

    def set_time_limit_seconds(self, value) -> None:
        self.time_limit_seconds = ensure_optional_positive_int("Puzzle.time_limit_seconds", value)

    def set_default_gate_set(self, value) -> None:
        self.default_gate_set = ensure_gate_set("Puzzle.default_gate_set", value)

    def set_rating_count(self, value: int) -> None:
        self.rating_count = ensure_non_negative_int("Puzzle.rating_count", value)

    def set_avg_difficulty(self, value: float) -> None:
        self.avg_difficulty = float(value)

    def set_avg_fun(self, value: float) -> None:
        self.avg_fun = float(value)

    def set_avg_clearness(self, value: float) -> None:
        self.avg_clearness = float(value)
