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
    created_at: datetime = field(default_factory=utcnow)
    # Admin-set overrides for puzzle capacity (None = use level-based default)
    max_published_puzzles: Optional[int] = None
    max_unpublished_puzzles: Optional[int] = None

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("User.id", self.id)
        if not self.username or not self.username.strip():
            raise ValidationError("User.username is required")
        if self.xp < 0:
            raise ValidationError("User.xp cannot be negative")

    @property
    def level(self) -> int:
        # Placeholder leveling rule; change later if spec differs
        return 1 + (self.xp // 100)

    @property
    def is_experienced(self) -> bool:
        return self.level >= 5

    @staticmethod
    def _default_puzzle_capacity(level: int) -> int:
        """Compute default puzzle capacity from level.
        
        Starts at 5 for levels ≤ 10, increases by 2 per level above 10.
        """
        from Backend import settings
        base = settings.PUZZLE_DEFAULT_MAX_PUBLISHED
        extra = max(0, level - settings.PUZZLE_CAPACITY_BASE_LEVEL)
        return base + extra * settings.PUZZLE_CAPACITY_LEVEL_INCREMENT

    @property
    def effective_max_published(self) -> int:
        """Effective published-puzzle limit (admin override or level-based default)."""
        if self.max_published_puzzles is not None:
            return self.max_published_puzzles
        return self._default_puzzle_capacity(self.level)

    @property
    def effective_max_unpublished(self) -> int:
        """Effective unpublished-puzzle limit (admin override or level-based default)."""
        if self.max_unpublished_puzzles is not None:
            return self.max_unpublished_puzzles
        return self._default_puzzle_capacity(self.level)

    def add_xp(self, amount: int) -> None:
        if amount < 0:
            raise ValidationError("XP amount must be non-negative")
        self.xp += amount

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "bio": self.bio,
            "xp": self.xp,
            "level": self.level,
            "is_discussion_banned": self.is_discussion_banned,
            "created_at": self.created_at.isoformat(),
            "createdAt": int(self.created_at.timestamp() * 1000),
            "max_published_puzzles": self.max_published_puzzles,
            "max_unpublished_puzzles": self.max_unpublished_puzzles,
            "effective_max_published": self.effective_max_published,
            "effective_max_unpublished": self.effective_max_unpublished,
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
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else utcnow(),
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
