from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .Enums import ThreadCategory
from .Exceptions import ValidationError
from .Utils import utcnow, ensure_non_empty, ensure_non_negative_int


@dataclass(slots=True)
class Discussion:
    id: int
    title: str
    body: str
    author_id: int
    puzzle_id: Optional[int] = None
    category: ThreadCategory = ThreadCategory.GENERAL
    is_pinned: bool = False
    is_locked: bool = False
    view_count: int = 0
    reply_count: int = 0
    upvotes: int = 0
    accepted_reply_id: Optional[int] = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("Discussion.id", self.id)
        self.author_id = ensure_non_negative_int("Discussion.author_id", self.author_id)
        ensure_non_empty("Discussion.title", self.title)
        ensure_non_empty("Discussion.body", self.body)
        if self.puzzle_id is not None:
            self.puzzle_id = ensure_non_negative_int("Discussion.puzzle_id", self.puzzle_id)
        if not isinstance(self.category, ThreadCategory):
            self.category = ThreadCategory(self.category)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "title": self.title,
            "body": self.body,
            "author_id": self.author_id,
            "puzzle_id": self.puzzle_id,
            "category": self.category.value,
            "is_pinned": self.is_pinned,
            "is_locked": self.is_locked,
            "view_count": self.view_count,
            "reply_count": self.reply_count,
            "upvotes": self.upvotes,
            "accepted_reply_id": self.accepted_reply_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "createdAt": int(self.created_at.timestamp() * 1000),
        }

    @staticmethod
    def from_dict(d: dict) -> "Discussion":
        from datetime import datetime as dt
        return Discussion(
            id=int(d.get("id", 0)),
            title=d["title"],
            body=d["body"],
            author_id=int(d["author_id"]),
            puzzle_id=int(d["puzzle_id"]) if d.get("puzzle_id") is not None else None,
            category=ThreadCategory(d.get("category", "general")),
            is_pinned=bool(d.get("is_pinned", False)),
            is_locked=bool(d.get("is_locked", False)),
            view_count=int(d.get("view_count", 0)),
            reply_count=int(d.get("reply_count", 0)),
            upvotes=int(d.get("upvotes", 0)),
            accepted_reply_id=int(d["accepted_reply_id"]) if d.get("accepted_reply_id") is not None else None,
            created_at=dt.fromisoformat(d["created_at"]) if "created_at" in d else utcnow(),
            updated_at=dt.fromisoformat(d["updated_at"]) if "updated_at" in d else utcnow(),
        )
