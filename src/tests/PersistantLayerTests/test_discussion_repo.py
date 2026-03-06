import sqlite3
import pytest
from datetime import datetime, timezone

from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.DiscussionRepo import DiscussionRepo
from Backend.DomainLayer.Discussion import Discussion
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
def repo(conn, user_repo, puzzle_repo):
    # Create a user first (discussions reference users)
    user = User(id=0, username="testuser", role=UserRole.SOLVER, xp=0)
    user_repo.create(user, password="pw")
    return DiscussionRepo(conn)


def make_discussion(author_id=1, title="Test Discussion", body="This is a test body", category="general", puzzle_id=None):
    return Discussion(
        id=0,
        title=title,
        body=body,
        author_id=author_id,
        puzzle_id=puzzle_id,
        category=ThreadCategory(category),
    )


def test_schema_created(conn, repo):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='discussions'"
    ).fetchone()
    assert row is not None


def test_create_and_get(repo):
    d = make_discussion()
    created = repo.create(d)
    assert created.id > 0
    assert created.title == "Test Discussion"

    fetched = repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.title == "Test Discussion"
    assert fetched.body == "This is a test body"
    assert fetched.category == ThreadCategory.GENERAL


def test_get_nonexistent(repo):
    assert repo.get_by_id(999) is None


def test_list_all_pagination(repo):
    for i in range(5):
        repo.create(make_discussion(title=f"Discussion {i}"))

    all_items = repo.list_all(limit=100)
    assert len(all_items) == 5

    page = repo.list_all(limit=2, offset=0)
    assert len(page) == 2

    page2 = repo.list_all(limit=2, offset=2)
    assert len(page2) == 2


def test_list_filter_by_category(repo):
    repo.create(make_discussion(title="General 1", category="general"))
    repo.create(make_discussion(title="Help 1", category="puzzle_help"))
    repo.create(make_discussion(title="General 2", category="general"))

    general = repo.list_all(category="general")
    assert len(general) == 2

    help_items = repo.list_all(category="puzzle_help")
    assert len(help_items) == 1


def test_count(repo):
    repo.create(make_discussion(title="D1"))
    repo.create(make_discussion(title="D2"))
    repo.create(make_discussion(title="D3", category="puzzle_help"))

    assert repo.count() == 3
    assert repo.count(category="general") == 2
    assert repo.count(category="puzzle_help") == 1


def test_update(repo):
    d = repo.create(make_discussion())
    updated = repo.update(d.id, {"title": "Updated Title", "body": "Updated body"})
    assert updated.title == "Updated Title"
    assert updated.body == "Updated body"


def test_delete(repo):
    d = repo.create(make_discussion())
    assert repo.delete(d.id)
    assert repo.get_by_id(d.id) is None


def test_delete_nonexistent(repo):
    assert not repo.delete(999)


def test_increment_view_count(repo):
    d = repo.create(make_discussion())
    assert d.view_count == 0

    repo.increment_view_count(d.id)
    repo.increment_view_count(d.id)

    fetched = repo.get_by_id(d.id)
    assert fetched.view_count == 2


def test_increment_reply_count(repo):
    d = repo.create(make_discussion())
    repo.increment_reply_count(d.id, 1)
    repo.increment_reply_count(d.id, 1)

    fetched = repo.get_by_id(d.id)
    assert fetched.reply_count == 2

    repo.increment_reply_count(d.id, -1)
    fetched = repo.get_by_id(d.id)
    assert fetched.reply_count == 1


def test_set_accepted_reply(repo):
    d = repo.create(make_discussion())
    assert d.accepted_reply_id is None

    repo.set_accepted_reply(d.id, 42)
    fetched = repo.get_by_id(d.id)
    assert fetched.accepted_reply_id == 42

    repo.set_accepted_reply(d.id, None)
    fetched = repo.get_by_id(d.id)
    assert fetched.accepted_reply_id is None


def test_pinned_first_ordering(repo):
    d1 = repo.create(make_discussion(title="Normal"))
    d2 = repo.create(make_discussion(title="Pinned"))
    repo.update(d2.id, {"is_pinned": True})

    items = repo.list_all()
    assert items[0].title == "Pinned"
    assert items[0].is_pinned is True


def test_list_sort_by_most_replies(repo):
    d1 = repo.create(make_discussion(title="Few"))
    d2 = repo.create(make_discussion(title="Many"))
    repo.increment_reply_count(d2.id, 10)

    items = repo.list_all(sort_by="most_replies")
    # Pinned first (both unpinned), then by reply count
    assert items[0].title == "Many"


def test_search_with_percent_wildcard(repo):
    repo.create(make_discussion(title="100% Complete"))
    repo.create(make_discussion(title="Normal Discussion"))
    repo.create(make_discussion(title="50% Done"))

    results = repo.list_all(search="100%")
    assert len(results) == 1
    assert results[0].title == "100% Complete"

    assert repo.count(search="100%") == 1


def test_search_with_underscore_wildcard(repo):
    repo.create(make_discussion(title="test_case_one"))
    repo.create(make_discussion(title="testing something"))
    repo.create(make_discussion(title="test_case_two"))

    results = repo.list_all(search="test_case")
    assert len(results) == 2
    titles = {r.title for r in results}
    assert titles == {"test_case_one", "test_case_two"}


def test_get_by_ids_empty_list(repo):
    """Test get_by_ids with empty list returns empty dict"""
    result = repo.get_by_ids([])
    assert result == {}


def test_get_by_ids_single_id(repo):
    """Test get_by_ids with single ID"""
    d = repo.create(make_discussion(title="Single"))
    result = repo.get_by_ids([d.id])
    assert len(result) == 1
    assert d.id in result
    assert result[d.id].title == "Single"


def test_get_by_ids_multiple_ids(repo):
    """Test get_by_ids with multiple IDs"""
    d1 = repo.create(make_discussion(title="First"))
    d2 = repo.create(make_discussion(title="Second"))
    d3 = repo.create(make_discussion(title="Third"))
    
    result = repo.get_by_ids([d1.id, d2.id, d3.id])
    assert len(result) == 3
    assert result[d1.id].title == "First"
    assert result[d2.id].title == "Second"
    assert result[d3.id].title == "Third"


def test_get_by_ids_with_duplicates(repo):
    """Test get_by_ids with duplicate IDs (should deduplicate)"""
    d = repo.create(make_discussion(title="Duplicate"))
    result = repo.get_by_ids([d.id, d.id, d.id])
    assert len(result) == 1
    assert result[d.id].title == "Duplicate"


def test_get_by_ids_partial_match(repo):
    """Test get_by_ids with some non-existent IDs"""
    d1 = repo.create(make_discussion(title="Exists"))
    result = repo.get_by_ids([d1.id, 999, 1000])
    assert len(result) == 1
    assert d1.id in result


def test_list_all_sort_by_oldest(repo):
    """Test sorting by oldest first"""
    repo.create(make_discussion(title="First"))
    repo.create(make_discussion(title="Second"))
    repo.create(make_discussion(title="Third"))
    
    items = repo.list_all(sort_by="oldest")
    assert items[0].title == "First"
    assert items[-1].title == "Third"


def test_list_all_sort_by_most_upvotes(repo):
    """Test sorting by most upvotes"""
    d1 = repo.create(make_discussion(title="Few Upvotes"))
    d2 = repo.create(make_discussion(title="Many Upvotes"))
    repo.update(d2.id, {"upvotes": 50})
    
    items = repo.list_all(sort_by="most_upvotes")
    assert items[0].title == "Many Upvotes"
    assert items[0].upvotes == 50


def test_list_all_sort_by_trending(repo):
    """Test sorting by trending (upvotes, replies, views weighted)"""
    d1 = repo.create(make_discussion(title="Trending"))
    repo.increment_view_count(d1.id)
    repo.increment_reply_count(d1.id, 5)
    repo.update(d1.id, {"upvotes": 10})
    
    items = repo.list_all(sort_by="trending")
    assert len(items) >= 1


def test_list_all_sort_by_unknown(repo):
    """Test sorting by unknown sort_by value defaults to newest"""
    import time
    d1 = make_discussion(title="First")
    repo.create(d1)
    time.sleep(0.01)  # Ensure different timestamps
    d2 = make_discussion(title="Second")
    repo.create(d2)
    
    items = repo.list_all(sort_by="unknown_sort")
    # Should default to created_at DESC (newest first)
    assert items[0].title == "Second"


def test_list_filter_by_author_id(repo, user_repo):
    """Test filtering discussions by author_id"""
    # Create another user
    user2 = User(id=0, username="user2", role=UserRole.SOLVER, xp=0)
    user2_id = user_repo.create(user2, password="pw2").id
    
    d1 = repo.create(make_discussion(author_id=1, title="User 1 Discussion"))
    d2 = repo.create(make_discussion(author_id=user2_id, title="User 2 Discussion"))
    
    user1_items = repo.list_all(author_id=1)
    assert len(user1_items) == 1
    assert user1_items[0].title == "User 1 Discussion"
    
    user2_items = repo.list_all(author_id=user2_id)
    assert len(user2_items) == 1


def test_count_filter_by_author_id(repo, user_repo):
    """Test count with author_id filter"""
    user2 = User(id=0, username="user2author", role=UserRole.SOLVER, xp=0)
    user2_id = user_repo.create(user2, password="pw2").id
    
    repo.create(make_discussion(author_id=1))
    repo.create(make_discussion(author_id=1))
    repo.create(make_discussion(author_id=user2_id))
    
    assert repo.count(author_id=1) == 2
    assert repo.count(author_id=user2_id) == 1


def test_list_filter_by_puzzle_id(repo, puzzle_repo):
    """Test filtering discussions by puzzle_id"""
    # Create puzzles
    from Backend.DomainLayer.Puzzle import Puzzle
    p1 = Puzzle(id=0, name="Puzzle 1", creator_user_id=1)
    p1 = puzzle_repo.create(p1)
    p2 = Puzzle(id=0, name="Puzzle 2", creator_user_id=1)
    p2 = puzzle_repo.create(p2)
    
    d1 = repo.create(make_discussion(title="About P1", puzzle_id=p1.id))
    d2 = repo.create(make_discussion(title="About P2", puzzle_id=p2.id))
    d3 = repo.create(make_discussion(title="General", puzzle_id=None))
    
    p1_items = repo.list_all(puzzle_id=p1.id)
    assert len(p1_items) == 1
    assert p1_items[0].title == "About P1"
    
    p2_items = repo.list_all(puzzle_id=p2.id)
    assert len(p2_items) == 1


def test_count_filter_by_puzzle_id(repo, puzzle_repo):
    """Test count with puzzle_id filter"""
    from Backend.DomainLayer.Puzzle import Puzzle
    p = Puzzle(id=0, name="Test Puzzle", creator_user_id=1)
    p = puzzle_repo.create(p)
    
    repo.create(make_discussion(puzzle_id=p.id))
    repo.create(make_discussion(puzzle_id=p.id))
    repo.create(make_discussion(puzzle_id=None))
    
    assert repo.count(puzzle_id=p.id) == 2


def test_list_combined_filters(repo):
    """Test list_all with multiple filters combined"""
    repo.create(make_discussion(title="D1", category="general", author_id=1))
    repo.create(make_discussion(title="D2", category="puzzle_help", author_id=1))
    repo.create(make_discussion(title="D3", category="general", author_id=1))
    
    items = repo.list_all(category="general", author_id=1)
    assert len(items) == 2
    for item in items:
        assert item.category == ThreadCategory.GENERAL
        assert item.author_id == 1


def test_count_combined_filters(repo):
    """Test count with multiple filters"""
    repo.create(make_discussion(title="D1", category="general"))
    repo.create(make_discussion(title="D2", category="puzzle_help"))
    repo.create(make_discussion(title="D3", category="general"))
    
    assert repo.count(category="general") == 2
    assert repo.count(category="puzzle_help") == 1


def test_search_in_body(repo):
    """Test that search finds matches in body text"""
    repo.create(make_discussion(title="Title 1", body="searching for this keyword"))
    repo.create(make_discussion(title="Title 2", body="different content"))
    
    results = repo.list_all(search="keyword")
    assert len(results) == 1
    assert "keyword" in results[0].body


def test_update_is_pinned(repo):
    """Test updating is_pinned boolean field"""
    d = repo.create(make_discussion())
    assert not d.is_pinned
    
    updated = repo.update(d.id, {"is_pinned": True})
    assert updated.is_pinned is True
    
    updated2 = repo.update(d.id, {"is_pinned": False})
    assert updated2.is_pinned is False


def test_update_is_locked(repo):
    """Test updating is_locked boolean field"""
    d = repo.create(make_discussion())
    assert not d.is_locked
    
    updated = repo.update(d.id, {"is_locked": True})
    assert updated.is_locked is True


def test_update_category(repo):
    """Test updating category field"""
    d = repo.create(make_discussion(category="general"))
    assert d.category == ThreadCategory.GENERAL
    
    updated = repo.update(d.id, {"category": "puzzle_help"})
    assert updated.category == ThreadCategory.PUZZLE_HELP


def test_update_upvotes(repo):
    """Test updating upvotes field"""
    d = repo.create(make_discussion())
    assert d.upvotes == 0
    
    updated = repo.update(d.id, {"upvotes": 42})
    assert updated.upvotes == 42


def test_update_with_invalid_fields(repo):
    """Test that invalid fields are ignored during update"""
    d = repo.create(make_discussion(title="Original"))
    # Try to update with invalid field and valid one
    updated = repo.update(d.id, {"title": "New Title", "author_id": 999, "created_at": "invalid"})
    assert updated.title == "New Title"
    # author_id should be ignored (not in allowed list)
    assert updated.author_id == 1


def test_update_no_fields(repo):
    """Test update with no allowed fields just returns current state"""
    d = repo.create(make_discussion(title="Test"))
    updated = repo.update(d.id, {"author_id": 999})  # invalid field
    assert updated.title == "Test"


def test_update_always_updates_updated_at(repo):
    """Test that updated_at is automatically updated"""
    d = repo.create(make_discussion())
    original_updated_at = d.updated_at
    
    import time
    time.sleep(0.01)  # Small delay to ensure time difference
    
    updated = repo.update(d.id, {"title": "New Title"})
    assert updated.updated_at != original_updated_at


def test_update_nonexistent_discussion(repo):
    """Test updating non-existent discussion"""
    result = repo.update(999, {"title": "New Title"})
    assert result is None


def test_sync_upvotes_from_votes(conn, repo):
    """Test sync_upvotes_from_votes when vote table exists"""
    # Create discussion_votes table needed for sync
    conn.execute("""
        CREATE TABLE IF NOT EXISTS discussion_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discussion_id INTEGER NOT NULL REFERENCES discussions(id),
            user_id INTEGER NOT NULL,
            value INTEGER NOT NULL
        )
    """)
    
    d = repo.create(make_discussion())
    
    # Add some votes
    conn.execute("INSERT INTO discussion_votes(discussion_id, user_id, value) VALUES(?, ?, ?)", 
                 (d.id, 1, 1))
    conn.execute("INSERT INTO discussion_votes(discussion_id, user_id, value) VALUES(?, ?, ?)", 
                 (d.id, 2, 1))
    conn.execute("INSERT INTO discussion_votes(discussion_id, user_id, value) VALUES(?, ?, ?)", 
                 (d.id, 3, -1))
    conn.commit()
    
    result = repo.sync_upvotes_from_votes(d.id)
    assert result["upvotes"] == 2
    assert result["downvotes"] == 1
    
    # Verify it updated the discussion
    fetched = repo.get_by_id(d.id)
    assert fetched.upvotes == 2


def test_sync_upvotes_no_votes(conn, repo):
    """Test sync_upvotes_from_votes with no votes"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS discussion_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discussion_id INTEGER NOT NULL REFERENCES discussions(id),
            user_id INTEGER NOT NULL,
            value INTEGER NOT NULL
        )
    """)
    
    d = repo.create(make_discussion())
    
    result = repo.sync_upvotes_from_votes(d.id)
    assert result["upvotes"] == 0
    assert result["downvotes"] == 0


def test_sync_upvotes_no_commit(conn, repo):
    """Test sync_upvotes_from_votes with commit=False"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS discussion_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discussion_id INTEGER NOT NULL REFERENCES discussions(id),
            user_id INTEGER NOT NULL,
            value INTEGER NOT NULL
        )
    """)
    
    d = repo.create(make_discussion())
    conn.execute("INSERT INTO discussion_votes(discussion_id, user_id, value) VALUES(?, ?, ?)", 
                 (d.id, 1, 1))
    
    # Call with commit=False
    result = repo.sync_upvotes_from_votes(d.id, commit=False)
    assert result["upvotes"] == 1
    
    # The transaction is still in progress, so we can verify it works


def test_increment_reply_count_no_commit(repo):
    """Test increment_reply_count with commit=False"""
    d = repo.create(make_discussion())
    
    repo.increment_reply_count(d.id, 2, commit=False)
    # Don't commit, so we can't verify directly


def test_create_with_all_optional_fields(repo):
    """Test creating discussion with all optional fields set"""
    d = Discussion(
        id=0,
        title="Full Discussion",
        body="Complete body",
        author_id=1,
        puzzle_id=None,
        category=ThreadCategory.GENERAL,
        is_pinned=True,
        is_locked=True,
        view_count=100,
        reply_count=50,
        upvotes=25,
        accepted_reply_id=42
    )
    
    created = repo.create(d)
    assert created.id > 0
    assert created.is_pinned is True
    assert created.is_locked is True
    assert created.view_count == 100
    assert created.reply_count == 50
    assert created.upvotes == 25
    assert created.accepted_reply_id == 42
    
    fetched = repo.get_by_id(created.id)
    assert fetched.is_pinned is True
    assert fetched.is_locked is True
    assert fetched.accepted_reply_id == 42
