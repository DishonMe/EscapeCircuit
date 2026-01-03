from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .Exceptions import ValidationError
from .Utils import utcnow, clamp_int, ensure_non_negative_int, ensure_non_empty


@dataclass(slots=True)
class Rating:
    id: int 
    puzzle_id: int
    user_id: int

    difficulty: int
    fun: int
    clearness: int

    created_at: datetime = field(default_factory=utcnow)
    is_experienced_at_rating: bool = False # never changes later when user becomes an expert 

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("Rating.id", self.id)
        self.puzzle_id = ensure_non_negative_int("Rating.puzzle_id", self.puzzle_id)
        self.user_id = ensure_non_negative_int("Rating.user_id", self.user_id)

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
            "puzzle_id": int(self.puzzle_id),
            "user_id": int(self.user_id),
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
            puzzle_id=int(d["puzzle_id"]),
            user_id=int(d["user_id"]),
            difficulty=int(d["difficulty"]),
            fun=int(d["fun"]),
            clearness=int(d["clearness"]),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else utcnow(),
            is_experienced_at_rating=bool(d.get("is_experienced_at_rating", False)),
        )

    # --- getters ---
    def get_id(self) -> int: return self.id
    def get_puzzle_id(self) -> int: return self.puzzle_id
    def get_user_id(self) -> int: return self.user_id
    def get_difficulty(self) -> int: return self.difficulty
    def get_fun(self) -> int: return self.fun
    def get_clearness(self) -> int: return self.clearness
    def get_created_at(self): return self.created_at
    def get_is_experienced_at_rating(self) -> bool: return self.is_experienced_at_rating

    # --- setters ---
    def set_user_id(self, value: int) -> None:
        self.user_id = ensure_non_negative_int("Rating.user_id", value)

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