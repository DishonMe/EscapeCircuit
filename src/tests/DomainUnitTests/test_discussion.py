import pytest
from datetime import datetime, timezone

from Backend.DomainLayer.Discussion import Discussion
from Backend.DomainLayer.Enums import ThreadCategory
from Backend.DomainLayer.Exceptions import ValidationError


class TestDiscussionCreation:
    def test_create_with_defaults(self):
        d = Discussion(id=1, title="Test", body="Body text", author_id=10)
        assert d.id == 1
        assert d.title == "Test"
        assert d.body == "Body text"
        assert d.author_id == 10
        assert d.puzzle_id is None
        assert d.category == ThreadCategory.GENERAL
        assert d.is_pinned is False
        assert d.is_locked is False
        assert d.view_count == 0
        assert d.reply_count == 0
        assert d.upvotes == 0
        assert d.accepted_reply_id is None
        assert isinstance(d.created_at, datetime)
        assert isinstance(d.updated_at, datetime)

    def test_create_with_all_fields(self):
        now = datetime.now(timezone.utc)
        d = Discussion(
            id=5,
            title="Full Discussion",
            body="Full body",
            author_id=3,
            puzzle_id=42,
            category=ThreadCategory.PUZZLE_HELP,
            is_pinned=True,
            is_locked=True,
            view_count=100,
            reply_count=10,
            upvotes=50,
            accepted_reply_id=7,
            created_at=now,
            updated_at=now,
        )
        assert d.id == 5
        assert d.puzzle_id == 42
        assert d.category == ThreadCategory.PUZZLE_HELP
        assert d.is_pinned is True
        assert d.is_locked is True
        assert d.view_count == 100
        assert d.reply_count == 10
        assert d.upvotes == 50
        assert d.accepted_reply_id == 7
        assert d.created_at == now

    def test_zero_id_is_valid(self):
        d = Discussion(id=0, title="T", body="B", author_id=0)
        assert d.id == 0
        assert d.author_id == 0


class TestDiscussionValidation:
    def test_negative_id_raises(self):
        with pytest.raises(ValidationError):
            Discussion(id=-1, title="T", body="B", author_id=1)

    def test_negative_author_id_raises(self):
        with pytest.raises(ValidationError):
            Discussion(id=1, title="T", body="B", author_id=-1)

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            Discussion(id=1, title="", body="B", author_id=1)

    def test_whitespace_title_raises(self):
        with pytest.raises(ValidationError):
            Discussion(id=1, title="   ", body="B", author_id=1)

    def test_empty_body_raises(self):
        with pytest.raises(ValidationError):
            Discussion(id=1, title="T", body="", author_id=1)

    def test_whitespace_body_raises(self):
        with pytest.raises(ValidationError):
            Discussion(id=1, title="T", body="   ", author_id=1)

    def test_negative_puzzle_id_raises(self):
        with pytest.raises(ValidationError):
            Discussion(id=1, title="T", body="B", author_id=1, puzzle_id=-5)

    def test_none_puzzle_id_is_valid(self):
        d = Discussion(id=1, title="T", body="B", author_id=1, puzzle_id=None)
        assert d.puzzle_id is None

    def test_category_coerced_from_string(self):
        d = Discussion(id=1, title="T", body="B", author_id=1, category="puzzle_help")
        assert d.category == ThreadCategory.PUZZLE_HELP


class TestDiscussionSerialization:
    def test_to_dict(self):
        now = datetime.now(timezone.utc)
        d = Discussion(
            id=1,
            title="Test",
            body="Body",
            author_id=10,
            puzzle_id=42,
            category=ThreadCategory.BUG_REPORT,
            is_pinned=True,
            is_locked=False,
            view_count=5,
            reply_count=3,
            upvotes=2,
            accepted_reply_id=99,
            created_at=now,
            updated_at=now,
        )
        result = d.to_dict()
        assert result["id"] == "1"
        assert result["title"] == "Test"
        assert result["body"] == "Body"
        assert result["author_id"] == 10
        assert result["puzzle_id"] == 42
        assert result["category"] == "bug_report"
        assert result["is_pinned"] is True
        assert result["is_locked"] is False
        assert result["view_count"] == 5
        assert result["reply_count"] == 3
        assert result["upvotes"] == 2
        assert result["accepted_reply_id"] == 99
        assert result["created_at"] == now.isoformat()
        assert result["updated_at"] == now.isoformat()
        assert result["createdAt"] == int(now.timestamp() * 1000)

    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        data = {
            "id": 5,
            "title": "From Dict",
            "body": "Body from dict",
            "author_id": 3,
            "puzzle_id": 10,
            "category": "solutions",
            "is_pinned": True,
            "is_locked": True,
            "view_count": 50,
            "reply_count": 7,
            "upvotes": 20,
            "accepted_reply_id": 42,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        d = Discussion.from_dict(data)
        assert d.id == 5
        assert d.title == "From Dict"
        assert d.body == "Body from dict"
        assert d.author_id == 3
        assert d.puzzle_id == 10
        assert d.category == ThreadCategory.SOLUTIONS
        assert d.is_pinned is True
        assert d.is_locked is True
        assert d.view_count == 50
        assert d.reply_count == 7
        assert d.upvotes == 20
        assert d.accepted_reply_id == 42

    def test_from_dict_defaults(self):
        data = {
            "title": "Minimal",
            "body": "Just body",
            "author_id": 1,
        }
        d = Discussion.from_dict(data)
        assert d.id == 0
        assert d.puzzle_id is None
        assert d.category == ThreadCategory.GENERAL
        assert d.is_pinned is False
        assert d.is_locked is False
        assert d.view_count == 0
        assert d.reply_count == 0
        assert d.upvotes == 0
        assert d.accepted_reply_id is None

    def test_roundtrip(self):
        now = datetime.now(timezone.utc)
        original = Discussion(
            id=1,
            title="Roundtrip",
            body="Roundtrip body",
            author_id=10,
            puzzle_id=5,
            category=ThreadCategory.FEATURE_REQUEST,
            is_pinned=True,
            view_count=10,
            reply_count=2,
            upvotes=7,
            accepted_reply_id=3,
            created_at=now,
            updated_at=now,
        )
        d = original.to_dict()
        restored = Discussion.from_dict(d)
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.body == original.body
        assert restored.author_id == original.author_id
        assert restored.puzzle_id == original.puzzle_id
        assert restored.category == original.category
        assert restored.is_pinned == original.is_pinned
        assert restored.view_count == original.view_count
        assert restored.reply_count == original.reply_count
        assert restored.upvotes == original.upvotes
        assert restored.accepted_reply_id == original.accepted_reply_id
