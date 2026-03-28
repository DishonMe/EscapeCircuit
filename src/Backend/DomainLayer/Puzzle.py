from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, List

from Backend import settings
from .Enums import GateType, PuzzleStatus, PuzzleDifficulty
from .Exceptions import ValidationError
from .Utils import utcnow, ensure_non_empty, ensure_non_negative_int, ensure_optional_positive_int, ensure_gate_set

@dataclass(slots=True)
class Puzzle:
    id: int 
    name: str
    creator_user_id: int
    description: str = ""
    instructions: Optional[str] = None
    creator_comment: Optional[str] = None
    status: PuzzleStatus = PuzzleStatus.DRAFT

    budget: int = 0
    creator_budget: Optional[int] = None  # Creator's solution cost (must be < budget when set)
    time_limit_seconds: Optional[int] = None
    difficulty: PuzzleDifficulty = PuzzleDifficulty.EASY
    default_gate_set: Set[GateType] = field(default_factory=set)
    allow_arsenal: bool = True
    allowed_arsenal_component_ids: Optional[List[str]] = None  # JSON list of allowed Arsenal component IDs
    arsenal_component_display_modes: Optional[dict] = None  # JSON dict mapping component ID to display mode ('circuit' or 'description')

    # Constraint fields
    total_gate_count: Optional[int] = None
    min_cycles: Optional[int] = None
    max_cycles: Optional[int] = None
    
    # Board dimensions (None = use defaults)
    board_rows: Optional[int] = None
    board_cols: Optional[int] = None

    rating_count: int = 0
    is_hall_of_fame: bool = False
    avg_difficulty: float = 0.0
    avg_fun: float = 0.0
    avg_clearness: float = 0.0
    avg_difficulty_exp: float = 0.0
    avg_fun_exp: float = 0.0
    avg_clearness_exp: float = 0.0

    created_at: datetime = field(default_factory=utcnow)
    fun_decided: bool = False
    fun_decided_exp: bool = False
    clearness_decided: bool = False
    clearness_decided_exp: bool = False
    rating_count_exp: int = 0

    #### will implement later - not in alpha ###
    # for special gates that the user created for this puzzle
    # special_gates: Set[str] = field(default_factory=set, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("Puzzle.id", self.id)
        if not self.name or not self.name.strip():
            raise ValidationError("Puzzle.name is required")
        self.creator_user_id = ensure_non_negative_int("Puzzle.creator_user_id", self.creator_user_id)
        if self.budget < 0:
            raise ValidationError("Puzzle.budget cannot be negative")
        if self.creator_budget is not None:
            if self.creator_budget < 1:
                raise ValidationError("Puzzle.creator_budget must be >= 1 when set")
            if self.budget > 0 and self.budget <= self.creator_budget:
                raise ValidationError(
                    f"Puzzle.budget ({self.budget}) must be greater than creator_budget ({self.creator_budget})"
                )
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
            "id": str(self.id), # Frontend often expects string IDs or handles both
            "name": self.name,
            "title": self.name, # Alias for frontend
            "creator_user_id": int(self.creator_user_id),
            "description": self.description,
            "instructions": self.instructions,
            "creatorComment": self.creator_comment,
            "status": self.status.value,
            "isPublic": self.status == PuzzleStatus.PUBLISHED,
            "budget": self.budget,
            "budgetLimit": self.budget,
            "creator_budget": self.creator_budget,
            "creatorBudget": self.creator_budget,
            "time_limit_seconds": self.time_limit_seconds,
            "timeLimit": self.time_limit_seconds, # Alias for frontend
            "difficulty": self.difficulty.value, # Creator-set difficulty
            "default_gate_set": [g.value for g in sorted(self.default_gate_set, key=lambda x: x.value)],
            "defaultGateSet": [g.value for g in sorted(self.default_gate_set, key=lambda x: x.value)],
            "allow_arsenal": self.allow_arsenal,
            "allowArsenal": self.allow_arsenal,
            "allowed_arsenal_component_ids": self.allowed_arsenal_component_ids,
            "allowedArsenalComponentIds": self.allowed_arsenal_component_ids,
            "arsenal_component_display_modes": self.arsenal_component_display_modes,
            "arsenalComponentDisplayModes": self.arsenal_component_display_modes,
            "total_gate_count": self.total_gate_count,
            "min_cycles": self.min_cycles,
            "max_cycles": self.max_cycles,
            "board_rows": self.board_rows if self.board_rows is not None else settings.PUZZLE_DEFAULT_BOARD_ROWS,
            "board_cols": self.board_cols if self.board_cols is not None else settings.PUZZLE_DEFAULT_BOARD_COLS,
            "rating": self.avg_difficulty, # Frontend expects 'rating' (number)
            "rating_count": self.rating_count,
            "is_hall_of_fame": self.is_hall_of_fame,
            "isHallOfFame": self.is_hall_of_fame,
            "solvedCount": 0, # Placeholder
            "inputs": [],     # Placeholder
            "outputs": [],    # Placeholder
            "avg_difficulty": self.avg_difficulty,
            "avg_fun": self.avg_fun,
            "avg_clearness": self.avg_clearness,
            "created_at": self.created_at.isoformat(),
            "createdAt": int(self.created_at.timestamp() * 1000), # Frontend expects timestamp (ms)
        }

    @staticmethod
    def from_dict(d: dict) -> "Puzzle":
        from datetime import datetime
        return Puzzle(
            id=int(d.get("id", 0)),
            name=d["name"],
            creator_user_id=int(d["creator_user_id"]),
            description=d.get("description", ""),
            instructions=d.get("instructions"),
            creator_comment=d.get("creator_comment"),
            status=PuzzleStatus(d.get("status", PuzzleStatus.DRAFT.value)),
            budget=int(d.get("budget", 0)),
            creator_budget=int(d["creator_budget"]) if d.get("creator_budget") is not None else (
                int(d["creatorBudget"]) if d.get("creatorBudget") is not None else None
            ),
            time_limit_seconds=d.get("time_limit_seconds", None),
            difficulty=PuzzleDifficulty(d["difficulty"]) if "difficulty" in d else PuzzleDifficulty.EASY,
            default_gate_set={GateType(x) for x in d.get("default_gate_set", [])},
            total_gate_count=d.get("total_gate_count"),
            min_cycles=d.get("min_cycles"),
            max_cycles=d.get("max_cycles"),
            board_rows=d.get("board_rows"),
            board_cols=d.get("board_cols"),
            allow_arsenal=d.get("allow_arsenal", True),
            allowed_arsenal_component_ids=d.get("allowed_arsenal_component_ids") or d.get("allowedArsenalComponentIds"),
            arsenal_component_display_modes=d.get("arsenal_component_display_modes") or d.get("arsenalComponentDisplayModes"),
            rating_count=int(d.get("rating_count", 0)),
            is_hall_of_fame=bool(d.get("is_hall_of_fame", d.get("isHallOfFame", False))),
            avg_difficulty=float(d.get("avg_difficulty", 0.0)),
            avg_fun=float(d.get("avg_fun", 0.0)),
            avg_clearness=float(d.get("avg_clearness", 0.0)),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else utcnow(),
        )
    

    # --- getters ---
    def get_id(self) -> int: return self.id
    def get_name(self) -> str: return self.name
    def get_creator_user_id(self) -> int: return self.creator_user_id
    def get_description(self) -> str: return self.description
    def get_status(self) -> PuzzleStatus: return self.status
    def get_budget(self) -> int: return self.budget
    def get_creator_budget(self) -> Optional[int]: return self.creator_budget
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

    def set_creator_user_id(self, value: int) -> None:
        self.creator_user_id = ensure_non_negative_int("Puzzle.creator_user_id", value)

    def set_description(self, value: str) -> None:
        self.description = value or ""

    def set_status(self, value: PuzzleStatus) -> None:
        if not isinstance(value, PuzzleStatus):
            raise ValidationError("Puzzle.status must be PuzzleStatus")
        self.status = value

    def set_budget(self, value: int) -> None:
        self.budget = ensure_non_negative_int("Puzzle.budget", value)

    def set_creator_budget(self, value: Optional[int]) -> None:
        if value is None:
            self.creator_budget = None
        else:
            v = int(value)
            if v < 1:
                raise ValidationError("Puzzle.creator_budget must be >= 1 when set")
            if self.budget > 0 and self.budget <= v:
                raise ValidationError(
                    f"Puzzle.budget ({self.budget}) must be greater than creator_budget ({v})"
                )
            self.creator_budget = v

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
