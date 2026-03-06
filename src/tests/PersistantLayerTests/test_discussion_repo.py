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

    bookmark_row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='bookmarked_discussions'"
    ).fetchone()
    assert bookmark_row is not None


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


def test_add_and_remove_bookmark(repo):
    d = repo.create(make_discussion())

    added = repo.add_bookmark(user_id=1, discussion_id=d.id)
    assert added is True
    assert repo.is_bookmarked(user_id=1, discussion_id=d.id) is True

    removed = repo.remove_bookmark(user_id=1, discussion_id=d.id)
    assert removed is True
    assert repo.is_bookmarked(user_id=1, discussion_id=d.id) is False


def test_get_user_bookmarks(repo):
    d1 = repo.create(make_discussion(title="One"))
    d2 = repo.create(make_discussion(title="Two"))

    repo.add_bookmark(user_id=1, discussion_id=d1.id)
    repo.add_bookmark(user_id=1, discussion_id=d2.id)

    bookmarks = repo.get_user_bookmarks(user_id=1)
    assert set(bookmarks) == {d1.id, d2.id}


def test_list_and_count_bookmarked_only(repo):
    d1 = repo.create(make_discussion(title="Bookmarked"))
    repo.create(make_discussion(title="Not Bookmarked"))
    repo.add_bookmark(user_id=1, discussion_id=d1.id)

    rows = repo.list_all(bookmarked_user_id=1)
    assert len(rows) == 1
    assert rows[0].id == d1.id
    assert repo.count(bookmarked_user_id=1) == 1
