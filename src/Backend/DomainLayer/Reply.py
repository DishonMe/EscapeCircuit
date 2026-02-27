from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .Exceptions import ValidationError
from .Utils import utcnow, ensure_non_empty, ensure_non_negative_int


@dataclass(slots=True)
class Reply:
    id: int
    discussion_id: int
    author_id: int
    body: str
    parent_reply_id: Optional[int] = None
    upvotes: int = 0
    downvotes: int = 0
    is_accepted: bool = False
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.id = ensure_non_negative_int("Reply.id", self.id)
        self.discussion_id = ensure_non_negative_int("Reply.discussion_id", self.discussion_id)
        self.author_id = ensure_non_negative_int("Reply.author_id", self.author_id)
        ensure_non_empty("Reply.body", self.body)
        if self.parent_reply_id is not None:
            self.parent_reply_id = ensure_non_negative_int("Reply.parent_reply_id", self.parent_reply_id)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "discussion_id": self.discussion_id,
            "parent_reply_id": self.parent_reply_id,
            "author_id": self.author_id,
            "body": self.body,
            "upvotes": self.upvotes,
            "downvotes": self.downvotes,
            "is_accepted": self.is_accepted,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "createdAt": int(self.created_at.timestamp() * 1000),
        }

    @staticmethod
    def from_dict(d: dict) -> "Reply":
        from datetime import datetime as dt
        return Reply(
            id=int(d.get("id", 0)),
            discussion_id=int(d["discussion_id"]),
            author_id=int(d["author_id"]),
            body=d["body"],
            parent_reply_id=int(d["parent_reply_id"]) if d.get("parent_reply_id") is not None else None,
            upvotes=int(d.get("upvotes", 0)),
            downvotes=int(d.get("downvotes", 0)),
            is_accepted=bool(d.get("is_accepted", False)),
            created_at=dt.fromisoformat(d["created_at"]) if "created_at" in d else utcnow(),
            updated_at=dt.fromisoformat(d["updated_at"]) if "updated_at" in d else utcnow(),
        )
