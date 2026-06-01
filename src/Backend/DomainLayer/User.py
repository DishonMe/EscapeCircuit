from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .Enums import UserRole
from .Exceptions import ValidationError
from .Utils import utcnow, ensure_non_empty, ensure_non_negative_int


@dataclass(slots=True)
class User:
    id: int
    username: str
    email: str = ""
    role: UserRole = UserRole.SOLVER
    bio: str = ""
    xp: int = 0
    is_discussion_banned: bool = False
    avatar_name: str = "Dinosaur"
    avatar_color: str = "#38bdf8"
    created_at: datetime = field(default_factory=utcnow)
    tutorials_completed: str = ""  # Comma-separated list of completed tutorial names
    # Admin-set overrides for puzzle capacity (None = use level-based default)
    max_published_puzzles: Optional[int] = None
    max_unpublished_puzzles: Optional[int] = None

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("User.id", self.id)
        if not self.username or not self.username.strip():
            raise ValidationError("User.username is required")
        if self.xp < 0:
            raise ValidationError("User.xp cannot be negative")
        if self.max_published_puzzles is not None and self.max_published_puzzles < 0:
            raise ValidationError("User.max_published_puzzles cannot be negative")
        if self.max_unpublished_puzzles is not None and self.max_unpublished_puzzles < 0:
            raise ValidationError("User.max_unpublished_puzzles cannot be negative")

    @property
    def level(self) -> int:
        # Placeholder leveling rule; change later if spec differs
        return 1 + (self.xp // 100)

    @property
    def is_experienced(self) -> bool:
        return self.level >= 5  

    def get_puzzle_capacity(self) -> tuple:
        """Returns (max_published, max_unpublished) for this creator.

        Base capacity is 5/5.  For each level from PUZZLE_CAPACITY_LEVEL_START
        (10) through PUZZLE_CAPACITY_LEVEL_END (15) the capacity increases by
        PUZZLE_CAPACITY_LEVEL_INCREMENT (2).  Admin overrides take priority.
        """
        from Backend import settings
        # Clamp level increments to the range [0, total levels in the bonus window].
        # min(...) caps the bonus at level END; max(..., 0) avoids a negative bonus
        # when the user is below the START level.
        total_bonus_levels = settings.PUZZLE_CAPACITY_LEVEL_END - settings.PUZZLE_CAPACITY_LEVEL_START + 1
        level_steps = max(
            0,
            min(
                self.level - settings.PUZZLE_CAPACITY_LEVEL_START + 1,
                total_bonus_levels,
            ),
        )
        level_bonus = level_steps * settings.PUZZLE_CAPACITY_LEVEL_INCREMENT

        default_published = settings.PUZZLE_BASE_PUBLISHED_PER_CREATOR + level_bonus
        default_unpublished = settings.PUZZLE_BASE_UNPUBLISHED_PER_CREATOR + level_bonus

        eff_published = (
            self.max_published_puzzles
            if self.max_published_puzzles is not None
            else default_published
        )
        eff_unpublished = (
            self.max_unpublished_puzzles
            if self.max_unpublished_puzzles is not None
            else default_unpublished
        )
        return eff_published, eff_unpublished

    def add_xp(self, amount: int) -> None:
        if amount < 0:
            raise ValidationError("XP amount must be non-negative")
        self.xp += amount

    def to_dict(self) -> dict:
        eff_published, eff_unpublished = self.get_puzzle_capacity()
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "bio": self.bio,
            "xp": self.xp,
            "level": self.level,
            "avatar_name": self.avatar_name,
            "avatar_color": self.avatar_color,
            "is_discussion_banned": self.is_discussion_banned,
            "tutorials_completed": self.tutorials_completed,
            "created_at": self.created_at.isoformat(),
            "createdAt": int(self.created_at.timestamp() * 1000),
            "max_published_override": self.max_published_puzzles,
            "max_unpublished_override": self.max_unpublished_puzzles,
            "effective_max_published": eff_published,
            "effective_max_unpublished": eff_unpublished,
        }

    @staticmethod
    def from_dict(d: dict) -> "User":
        from datetime import datetime
        return User(
            id=int(d.get("id", 0)),
            username=d["username"],
            email=d.get("email", ""),
            role=UserRole(d.get("role", UserRole.SOLVER.value)),
            bio=d.get("bio", ""),
            xp=int(d.get("xp", 0)),
            is_discussion_banned=bool(d.get("is_discussion_banned", False)),
            avatar_name=d.get("avatar_name", "Dinosaur"),
            avatar_color=d.get("avatar_color", "#38bdf8"),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else utcnow(),
            tutorials_completed=d.get("tutorials_completed", ""),
            max_published_puzzles=d.get("max_published_puzzles"),
            max_unpublished_puzzles=d.get("max_unpublished_puzzles"),
        )

    # --- getters ---
    def get_id(self) -> int: return self.id
    def get_username(self) -> str: return self.username
    def get_role(self) -> UserRole: return self.role
    def get_xp(self) -> int: return self.xp
    def get_created_at(self): return self.created_at

    # --- setters ---
    def set_username(self, value: str) -> None:
        self.username = ensure_non_empty("User.username", value)

    def set_role(self, value: UserRole) -> None:
        if not isinstance(value, UserRole):
            raise ValidationError("User.role must be UserRole")
        self.role = value

    def set_xp(self, value: int) -> None:
        self.xp = ensure_non_negative_int("User.xp", value)
