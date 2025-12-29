from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .Exceptions import ValidationError
from .Utils import utcnow, clamp_int, ensure_non_negative_int, ensure_non_empty


@dataclass(slots=True)
class Rating:
    id: int 
    puzzle_id: str
    user_id: str

    difficulty: int
    fun: int
    clearness: int

    created_at: datetime = field(default_factory=utcnow)
    is_experienced_at_rating: bool = False # never changes later when user becomes an expert 

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("Rating.id", self.id)
        if not self.puzzle_id:
            raise ValidationError("Rating.puzzle_id is required")
        if not self.user_id:
            raise ValidationError("Rating.user_id is required")

        self.difficulty = clamp_int("difficulty", self.difficulty, 1, 5)
        self.fun = clamp_int("fun", self.fun, 1, 5)
        self.clearness = clamp_int("clearness", self.clearness, 1, 5)

        if not isinstance(self.is_experienced_at_rating, bool):
            raise ValidationError("Rating.is_experienced_at_rating must be bool")

    @property
    def is_experienced(self) -> bool:
        return self.is_experienced_at_rating

    def to_dict(self) -> dict:
        return {
            "id": int(self.id),
            "puzzle_id": self.puzzle_id,
            "user_id": self.user_id,
            "difficulty": self.difficulty,
            "fun": self.fun,
            "clearness": self.clearness,
            "created_at": self.created_at.isoformat(),
            "is_experienced_at_rating": self.is_experienced_at_rating,
        }

    @staticmethod
    def from_dict(d: dict) -> "Rating":
        from datetime import datetime
        return Rating(
            id=int(d.get("id", 0)),
            puzzle_id=d["puzzle_id"],
            user_id=d["user_id"],
            difficulty=int(d["difficulty"]),
            fun=int(d["fun"]),
            clearness=int(d["clearness"]),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else utcnow(),
            is_experienced_at_rating=bool(d.get("is_experienced_at_rating", False)),
        )

    # --- getters ---
    def get_id(self) -> int: return self.id
    def get_puzzle_id(self) -> str: return self.puzzle_id
    def get_user_id(self) -> str: return self.user_id
    def get_difficulty(self) -> int: return self.difficulty
    def get_fun(self) -> int: return self.fun
    def get_clearness(self) -> int: return self.clearness
    def get_created_at(self): return self.created_at
    def get_is_experienced_at_rating(self) -> bool: return self.is_experienced_at_rating

    # --- setters ---
    def set_user_id(self, value: str) -> None:
        self.user_id = ensure_non_empty("Rating.user_id", value)

    def set_difficulty(self, value: int) -> None:
        self.difficulty = clamp_int("difficulty", value, 1, 5)

    def set_fun(self, value: int) -> None:
        self.fun = clamp_int("fun", value, 1, 5)

    def set_clearness(self, value: int) -> None:
        self.clearness = clamp_int("clearness", value, 1, 5)

    def set_is_experienced_at_rating(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValidationError("Rating.is_experienced_at_rating must be bool")
        self.is_experienced_at_rating = value