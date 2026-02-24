import sqlite3
import pytest

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
def setup(conn):
    user_repo = UserRepo(conn)
    PuzzleRepo(conn)  # needed for FK
    discussion_repo = DiscussionRepo(conn)

    # Create a test user
    user = User(id=0, username="alice", role=UserRole.SOLVER, xp=0)
    user_repo.create(user, password="pw")

    # Create several discussions with varied titles and bodies
    discussions = []
    data = [
        ("How to solve XOR puzzles", "I need help with XOR gate logic"),
        ("Tips for beginners", "Start with simple AND gates before moving on"),
        ("XOR gate tricks", "Advanced XOR techniques for competitive solving"),
        ("Feature request: dark mode", "Please add dark mode to the UI"),
        ("Bug in puzzle editor", "The editor crashes when saving large circuits"),
    ]
    for title, body in data:
        d = Discussion(
            id=0, title=title, body=body, author_id=1,
            category=ThreadCategory.GENERAL,
        )
        discussions.append(discussion_repo.create(d))

    return discussion_repo, discussions


# ---- Search by title substring ----

def test_search_by_title(setup):
    repo, _ = setup
    results = repo.list_all(search="XOR")
    # "How to solve XOR puzzles" and "XOR gate tricks" match by title;
    # "I need help with XOR gate logic" also matches via body on the first one.
    # The third discussion body also has "XOR".
    titles = [d.title for d in results]
    assert "How to solve XOR puzzles" in titles
    assert "XOR gate tricks" in titles


def test_search_by_title_case_insensitive_like(setup):
    repo, _ = setup
    # SQLite LIKE is case-insensitive for ASCII by default
    results = repo.list_all(search="xor")
    assert len(results) >= 2


# ---- Search by body substring ----

def test_search_by_body(setup):
    repo, _ = setup
    results = repo.list_all(search="dark mode")
    assert len(results) == 1
    assert results[0].title == "Feature request: dark mode"


def test_search_by_body_partial(setup):
    repo, _ = setup
    results = repo.list_all(search="circuits")
    assert len(results) == 1
    assert results[0].title == "Bug in puzzle editor"


# ---- Search with no results ----

def test_search_no_results(setup):
    repo, _ = setup
    results = repo.list_all(search="nonexistent_term_xyz")
    assert results == []


def test_search_empty_string_returns_all(setup):
    repo, discussions = setup
    # An empty search string should not filter anything
    results = repo.list_all(search="")
    assert len(results) == len(discussions)


# ---- Trending sort (basic sanity check) ----

def test_trending_sort_returns_discussions(setup):
    repo, discussions = setup
    # Give one discussion some engagement signals
    repo.increment_view_count(discussions[0].id)
    repo.increment_view_count(discussions[0].id)
    repo.increment_reply_count(discussions[0].id, 3)

    results = repo.list_all(sort_by="trending")
    assert len(results) == len(discussions)
    # All discussions should be returned
    returned_ids = {d.id for d in results}
    expected_ids = {d.id for d in discussions}
    assert returned_ids == expected_ids


def test_trending_sort_with_search(setup):
    repo, _ = setup
    results = repo.list_all(sort_by="trending", search="XOR")
    assert len(results) >= 2
    for d in results:
        assert "XOR" in d.title or "XOR" in d.body


def test_count_with_search(setup):
    repo, _ = setup
    assert repo.count(search="XOR") >= 2
    assert repo.count(search="dark mode") == 1
    assert repo.count(search="nonexistent_term_xyz") == 0
