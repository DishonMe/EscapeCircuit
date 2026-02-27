import pytest
from datetime import datetime, timezone

from Backend.DomainLayer.Reply import Reply
from Backend.DomainLayer.Exceptions import ValidationError


class TestReplyCreation:
    def test_create_with_defaults(self):
        r = Reply(id=1, discussion_id=10, author_id=5, body="Reply text")
        assert r.id == 1
        assert r.discussion_id == 10
        assert r.author_id == 5
        assert r.body == "Reply text"
        assert r.parent_reply_id is None
        assert r.upvotes == 0
        assert r.downvotes == 0
        assert r.is_accepted is False
        assert isinstance(r.created_at, datetime)
        assert isinstance(r.updated_at, datetime)

    def test_create_with_all_fields(self):
        now = datetime.now(timezone.utc)
        r = Reply(
            id=5,
            discussion_id=3,
            author_id=7,
            body="Full reply",
            parent_reply_id=2,
            upvotes=10,
            downvotes=3,
            is_accepted=True,
            created_at=now,
            updated_at=now,
        )
        assert r.id == 5
        assert r.discussion_id == 3
        assert r.author_id == 7
        assert r.body == "Full reply"
        assert r.parent_reply_id == 2
        assert r.upvotes == 10
        assert r.downvotes == 3
        assert r.is_accepted is True
        assert r.created_at == now

    def test_zero_ids_valid(self):
        r = Reply(id=0, discussion_id=0, author_id=0, body="B")
        assert r.id == 0
        assert r.discussion_id == 0
        assert r.author_id == 0


class TestReplyValidation:
    def test_negative_id_raises(self):
        with pytest.raises(ValidationError):
            Reply(id=-1, discussion_id=1, author_id=1, body="B")

    def test_negative_discussion_id_raises(self):
        with pytest.raises(ValidationError):
            Reply(id=1, discussion_id=-1, author_id=1, body="B")

    def test_negative_author_id_raises(self):
        with pytest.raises(ValidationError):
            Reply(id=1, discussion_id=1, author_id=-1, body="B")

    def test_empty_body_raises(self):
        with pytest.raises(ValidationError):
            Reply(id=1, discussion_id=1, author_id=1, body="")

    def test_whitespace_body_raises(self):
        with pytest.raises(ValidationError):
            Reply(id=1, discussion_id=1, author_id=1, body="   ")

    def test_negative_parent_reply_id_raises(self):
        with pytest.raises(ValidationError):
            Reply(id=1, discussion_id=1, author_id=1, body="B", parent_reply_id=-1)

    def test_none_parent_reply_id_is_valid(self):
        r = Reply(id=1, discussion_id=1, author_id=1, body="B", parent_reply_id=None)
        assert r.parent_reply_id is None

    def test_zero_parent_reply_id_is_valid(self):
        r = Reply(id=1, discussion_id=1, author_id=1, body="B", parent_reply_id=0)
        assert r.parent_reply_id == 0


class TestReplySerialization:
    def test_to_dict(self):
        now = datetime.now(timezone.utc)
        r = Reply(
            id=1,
            discussion_id=10,
            author_id=5,
            body="Reply body",
            parent_reply_id=3,
            upvotes=7,
            downvotes=2,
            is_accepted=True,
            created_at=now,
            updated_at=now,
        )
        result = r.to_dict()
        assert result["id"] == "1"
        assert result["discussion_id"] == 10
        assert result["author_id"] == 5
        assert result["body"] == "Reply body"
        assert result["parent_reply_id"] == 3
        assert result["upvotes"] == 7
        assert result["downvotes"] == 2
        assert result["is_accepted"] is True
        assert result["created_at"] == now.isoformat()
        assert result["updated_at"] == now.isoformat()
        assert result["createdAt"] == int(now.timestamp() * 1000)

    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        data = {
            "id": 5,
            "discussion_id": 10,
            "author_id": 3,
            "body": "From dict",
            "parent_reply_id": 2,
            "upvotes": 4,
            "downvotes": 1,
            "is_accepted": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        r = Reply.from_dict(data)
        assert r.id == 5
        assert r.discussion_id == 10
        assert r.author_id == 3
        assert r.body == "From dict"
        assert r.parent_reply_id == 2
        assert r.upvotes == 4
        assert r.downvotes == 1
        assert r.is_accepted is True

    def test_from_dict_defaults(self):
        data = {
            "discussion_id": 1,
            "author_id": 1,
            "body": "Minimal",
        }
        r = Reply.from_dict(data)
        assert r.id == 0
        assert r.parent_reply_id is None
        assert r.upvotes == 0
        assert r.downvotes == 0
        assert r.is_accepted is False

    def test_roundtrip(self):
        now = datetime.now(timezone.utc)
        original = Reply(
            id=1,
            discussion_id=10,
            author_id=5,
            body="Roundtrip reply",
            parent_reply_id=3,
            upvotes=7,
            downvotes=2,
            is_accepted=True,
            created_at=now,
            updated_at=now,
        )
        d = original.to_dict()
        restored = Reply.from_dict(d)
        assert restored.id == original.id
        assert restored.discussion_id == original.discussion_id
        assert restored.author_id == original.author_id
        assert restored.body == original.body
        assert restored.parent_reply_id == original.parent_reply_id
        assert restored.upvotes == original.upvotes
        assert restored.downvotes == original.downvotes
        assert restored.is_accepted == original.is_accepted
