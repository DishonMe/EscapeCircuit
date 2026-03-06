import sqlite3
import pytest

from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.DiscussionRepo import DiscussionRepo
from Backend.PersistantLayer.ReplyRepo import ReplyRepo
from Backend.DomainLayer.Discussion import Discussion
from Backend.DomainLayer.Reply import Reply
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole, ThreadCategory


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    c.execute("PRAGMA foreign_keys = ON;")
    return c


@pytest.fixture
def user_repo(conn):
    return UserRepo(conn)


@pytest.fixture
def puzzle_repo(conn):
    """Create puzzles table (needed for FK references)."""
    return PuzzleRepo(conn)


@pytest.fixture
def discussion_repo(conn, user_repo, puzzle_repo):
    user = User(id=0, username="testuser", role=UserRole.SOLVER, xp=0)
    user_repo.create(user, password="pw")
    return DiscussionRepo(conn)


@pytest.fixture
def repo(conn, discussion_repo):
    # Create a discussion to reference
    d = Discussion(id=0, title="Test", body="body", author_id=1, category=ThreadCategory.GENERAL)
    discussion_repo.create(d)
    return ReplyRepo(conn)


def make_reply(discussion_id=1, author_id=1, body="This is a reply", parent_reply_id=None):
    return Reply(
        id=0,
        discussion_id=discussion_id,
        author_id=author_id,
        body=body,
        parent_reply_id=parent_reply_id,
    )


def test_schema_created(conn, repo):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='replies'"
    ).fetchone()
    assert row is not None


def test_create_and_get(repo):
    r = make_reply()
    created = repo.create(r)
    assert created.id > 0

    fetched = repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.body == "This is a reply"
    assert fetched.discussion_id == 1


def test_get_nonexistent(repo):
    assert repo.get_by_id(999) is None


def test_list_by_discussion(repo):
    repo.create(make_reply(body="Reply 1"))
    repo.create(make_reply(body="Reply 2"))
    repo.create(make_reply(body="Reply 3"))

    replies = repo.list_by_discussion(1)
    assert len(replies) == 3


def test_list_top_level(repo):
    r1 = repo.create(make_reply(body="Top level 1"))
    r2 = repo.create(make_reply(body="Top level 2"))
    repo.create(make_reply(body="Child", parent_reply_id=r1.id))

    top = repo.list_top_level(1)
    assert len(top) == 2


def test_list_children(repo):
    parent = repo.create(make_reply(body="Parent"))
    repo.create(make_reply(body="Child 1", parent_reply_id=parent.id))
    repo.create(make_reply(body="Child 2", parent_reply_id=parent.id))

    children = repo.list_children(parent.id)
    assert len(children) == 2


def test_count_by_discussion(repo):
    repo.create(make_reply())
    repo.create(make_reply())
    assert repo.count_by_discussion(1) == 2


def test_update(repo):
    r = repo.create(make_reply())
    updated = repo.update(r.id, {"body": "Updated body"})
    assert updated.body == "Updated body"


def test_delete(repo):
    r = repo.create(make_reply())
    assert repo.delete(r.id)
    assert repo.get_by_id(r.id) is None


def test_delete_nonexistent(repo):
    assert not repo.delete(999)


def test_update_votes(repo):
    r = repo.create(make_reply())
    repo.update_votes(r.id, 5, 2)

    fetched = repo.get_by_id(r.id)
    assert fetched.upvotes == 5
    assert fetched.downvotes == 2


def test_clear_accepted_for_discussion(repo):
    r1 = repo.create(make_reply(body="Reply 1"))
    r2 = repo.create(make_reply(body="Reply 2"))
    repo.update(r1.id, {"is_accepted": True})

    fetched = repo.get_by_id(r1.id)
    assert fetched.is_accepted is True

    repo.clear_accepted_for_discussion(1)

    fetched1 = repo.get_by_id(r1.id)
    fetched2 = repo.get_by_id(r2.id)
    assert fetched1.is_accepted is False
    assert fetched2.is_accepted is False


def test_nested_replies(repo):
    parent = repo.create(make_reply(body="Level 0"))
    child = repo.create(make_reply(body="Level 1", parent_reply_id=parent.id))
    grandchild = repo.create(make_reply(body="Level 2", parent_reply_id=child.id))

    assert grandchild.parent_reply_id == child.id

    children_of_parent = repo.list_children(parent.id)
    assert len(children_of_parent) == 1
    assert children_of_parent[0].id == child.id

    children_of_child = repo.list_children(child.id)
    assert len(children_of_child) == 1
    assert children_of_child[0].id == grandchild.id

class TestReplyRepoGetByIds:
    """Tests for get_by_ids method"""
    
    def test_get_by_ids_single(self, repo):
        r = repo.create(make_reply())
        result = repo.get_by_ids([r.id])
        assert len(result) == 1
        assert result[r.id].body == "This is a reply"

    def test_get_by_ids_multiple(self, repo):
        r1 = repo.create(make_reply(body="Reply 1"))
        r2 = repo.create(make_reply(body="Reply 2"))
        r3 = repo.create(make_reply(body="Reply 3"))
        
        result = repo.get_by_ids([r1.id, r2.id, r3.id])
        assert len(result) == 3

    def test_get_by_ids_empty_list(self, repo):
        result = repo.get_by_ids([])
        assert len(result) == 0

    def test_get_by_ids_partial_exists(self, repo):
        r = repo.create(make_reply())
        result = repo.get_by_ids([r.id, 99999])
        assert len(result) == 1


class TestReplyRepoPagination:
    """Tests for pagination in list operations"""
    
    def test_list_by_discussion_pagination(self, repo):
        for i in range(5):
            repo.create(make_reply(body=f"Reply {i}"))
        
        page1 = repo.list_by_discussion(1, limit=2, offset=0)
        page2 = repo.list_by_discussion(1, limit=2, offset=2)
        
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    def test_list_top_level_pagination(self, repo):
        for i in range(3):
            repo.create(make_reply(body=f"Top {i}"))
        
        page = repo.list_top_level(1, limit=1, offset=0)
        assert len(page) == 1


class TestReplyRepoVoting:
    """Tests for upvote/downvote functionality"""
    
    def test_update_votes_increment(self, repo):
        r = repo.create(make_reply())
        repo.update_votes(r.id, 10, 2)
        
        fetched = repo.get_by_id(r.id)
        assert fetched.upvotes == 10
        assert fetched.downvotes == 2

    def test_update_votes_zero(self, repo):
        r = repo.create(make_reply())
        repo.update_votes(r.id, 0, 0)
        
        fetched = repo.get_by_id(r.id)
        assert fetched.upvotes == 0
        assert fetched.downvotes == 0

    def test_update_votes_large_numbers(self, repo):
        r = repo.create(make_reply())
        repo.update_votes(r.id, 1000, 500)
        
        fetched = repo.get_by_id(r.id)
        assert fetched.upvotes == 1000
        assert fetched.downvotes == 500


class TestReplyRepoUpdateCommit:
    """Tests for update method variants"""
    
    def test_update_with_empty_fields(self, repo):
        """Test update with empty fields dict returns current reply"""
        r = repo.create(make_reply(body="Original"))
        
        # Call update with no fields (empty dict)
        result = repo.update(r.id, {})
        
        # Should return the unchanged reply
        assert result is not None
        assert result.body == "Original"

    def test_update_body_with_updated_at(self, repo):
        """Test update automatically adds updated_at when not provided"""
        r = repo.create(make_reply(body="Original"))
        
        result = repo.update(r.id, {"body": "Updated"})
        assert result.body == "Updated"


class TestReplyRepoCommitControl:
    """Tests for methods with commit parameter"""
    
    def test_delete_with_commit_false(self, repo):
        """Test delete with commit=False does not auto-commit"""
        r = repo.create(make_reply())
        # Calling delete with commit=False should not auto-commit
        result = repo.delete(r.id, commit=False)
        assert result is True

    def test_update_votes_with_commit_false(self, repo):
        """Test update_votes with commit=False does not auto-commit"""
        r = repo.create(make_reply())
        # Calling update_votes with commit=False should not auto-commit
        repo.update_votes(r.id, 5, 2, commit=False)
        # Should still work without commit
        fetched = repo.get_by_id(r.id)
        assert fetched is not None


class TestReplyRepoAcceptance:
    """Tests for accepted answer functionality"""
    
    def test_set_accepted(self, repo):
        r = repo.create(make_reply())
        repo.update(r.id, {"is_accepted": True})
        
        fetched = repo.get_by_id(r.id)
        assert fetched.is_accepted is True

    def test_clear_accepted_for_discussion_comprehensive(self, repo):
        r1 = repo.create(make_reply(body="R1"))
        r2 = repo.create(make_reply(body="R2"))
        r3 = repo.create(make_reply(body="R3"))
        
        repo.update(r1.id, {"is_accepted": True})
        repo.update(r2.id, {"is_accepted": True})
        
        repo.clear_accepted_for_discussion(1)
        
        assert repo.get_by_id(r1.id).is_accepted is False
        assert repo.get_by_id(r2.id).is_accepted is False
        assert repo.get_by_id(r3.id).is_accepted is False


class TestReplyRepoUpdateOperations:
    """Tests for update operations"""
    
    def test_update_body(self, repo):
        r = repo.create(make_reply(body="Original"))
        repo.update(r.id, {"body": "Updated"})
        fetched = repo.get_by_id(r.id)
        assert fetched.body == "Updated"

    def test_update_multiple_fields(self, repo):
        r = repo.create(make_reply(body="Original"))
        repo.update(r.id, {"body": "Updated", "is_accepted": True})
        fetched = repo.get_by_id(r.id)
        assert fetched.body == "Updated"
        assert fetched.is_accepted is True


class TestReplyRepoCountByDiscussion:
    """Tests for count_by_discussion method"""
    
    def test_count_by_discussion_empty(self, repo):
        count = repo.count_by_discussion(999)
        assert count == 0

    def test_count_by_discussion_multiple(self, repo):
        for i in range(3):
            repo.create(make_reply())
        count = repo.count_by_discussion(1)
        assert count == 3