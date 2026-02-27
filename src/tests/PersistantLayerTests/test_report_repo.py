import sqlite3
import pytest

from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.DiscussionRepo import DiscussionRepo
from Backend.PersistantLayer.ReplyRepo import ReplyRepo
from Backend.PersistantLayer.ReportRepo import ReportRepo
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
def setup(conn):
    user_repo = UserRepo(conn)
    PuzzleRepo(conn)  # needed for FK
    discussion_repo = DiscussionRepo(conn)
    reply_repo = ReplyRepo(conn)
    report_repo = ReportRepo(conn)

    # Create test users
    alice = User(id=0, username="alice", role=UserRole.SOLVER, xp=0)
    user_repo.create(alice, password="pw")
    bob = User(id=0, username="bob", role=UserRole.SOLVER, xp=0)
    user_repo.create(bob, password="pw")

    # Create a test discussion
    discussion = Discussion(
        id=0, title="Test Discussion", body="Test body", author_id=1,
        category=ThreadCategory.GENERAL,
    )
    discussion = discussion_repo.create(discussion)

    # Create a test reply
    reply = Reply(id=0, discussion_id=discussion.id, author_id=2, body="Reply body")
    reply = reply_repo.create(reply)

    return report_repo, discussion, reply


# ---- Create ----

def test_create_report(setup):
    repo, discussion, _ = setup
    report = repo.create(
        reporter_id=1,
        target_type="discussion",
        target_id=discussion.id,
        reason="spam",
        details="This is spam content",
    )
    assert report["id"] > 0
    assert report["reporter_id"] == 1
    assert report["target_type"] == "discussion"
    assert report["target_id"] == discussion.id
    assert report["reason"] == "spam"
    assert report["details"] == "This is spam content"
    assert report["status"] == "pending"
    assert "created_at" in report


def test_create_report_default_details(setup):
    repo, discussion, _ = setup
    report = repo.create(
        reporter_id=1,
        target_type="discussion",
        target_id=discussion.id,
        reason="offensive",
    )
    assert report["details"] == ""


def test_create_report_on_reply(setup):
    repo, _, reply = setup
    report = repo.create(
        reporter_id=1,
        target_type="reply",
        target_id=reply.id,
        reason="harassment",
        details="Harassing content",
    )
    assert report["target_type"] == "reply"
    assert report["target_id"] == reply.id


# ---- Get by ID ----

def test_get_by_id(setup):
    repo, discussion, _ = setup
    created = repo.create(
        reporter_id=1,
        target_type="discussion",
        target_id=discussion.id,
        reason="spam",
    )
    fetched = repo.get_by_id(created["id"])
    assert fetched is not None
    assert fetched["id"] == created["id"]
    assert fetched["reporter_id"] == 1
    assert fetched["target_type"] == "discussion"
    assert fetched["target_id"] == discussion.id
    assert fetched["reason"] == "spam"
    assert fetched["status"] == "pending"


def test_get_by_id_nonexistent(setup):
    repo, _, _ = setup
    assert repo.get_by_id(999) is None


# ---- List all ----

def test_list_all_default(setup):
    repo, discussion, reply = setup
    repo.create(reporter_id=1, target_type="discussion", target_id=discussion.id, reason="spam")
    repo.create(reporter_id=2, target_type="reply", target_id=reply.id, reason="offensive")

    reports = repo.list_all()
    assert len(reports) == 2


def test_list_all_filtered_by_status(setup):
    repo, discussion, reply = setup
    r1 = repo.create(reporter_id=1, target_type="discussion", target_id=discussion.id, reason="spam")
    repo.create(reporter_id=2, target_type="reply", target_id=reply.id, reason="offensive")

    # Update one report to "resolved"
    repo.update_status(r1["id"], "resolved")

    pending = repo.list_all(status="pending")
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"

    resolved = repo.list_all(status="resolved")
    assert len(resolved) == 1
    assert resolved[0]["status"] == "resolved"


def test_list_all_with_limit_and_offset(setup):
    repo, discussion, reply = setup
    repo.create(reporter_id=1, target_type="discussion", target_id=discussion.id, reason="spam")
    repo.create(reporter_id=2, target_type="reply", target_id=reply.id, reason="offensive")

    page1 = repo.list_all(limit=1, offset=0)
    assert len(page1) == 1

    page2 = repo.list_all(limit=1, offset=1)
    assert len(page2) == 1

    # The two pages should have different reports
    assert page1[0]["id"] != page2[0]["id"]


def test_list_all_empty(setup):
    repo, _, _ = setup
    reports = repo.list_all()
    assert reports == []


# ---- Count ----

def test_count_all(setup):
    repo, discussion, reply = setup
    repo.create(reporter_id=1, target_type="discussion", target_id=discussion.id, reason="spam")
    repo.create(reporter_id=2, target_type="reply", target_id=reply.id, reason="offensive")

    assert repo.count() == 2


def test_count_filtered_by_status(setup):
    repo, discussion, reply = setup
    r1 = repo.create(reporter_id=1, target_type="discussion", target_id=discussion.id, reason="spam")
    repo.create(reporter_id=2, target_type="reply", target_id=reply.id, reason="offensive")

    repo.update_status(r1["id"], "resolved")

    assert repo.count(status="pending") == 1
    assert repo.count(status="resolved") == 1
    assert repo.count() == 2


def test_count_empty(setup):
    repo, _, _ = setup
    assert repo.count() == 0


# ---- Update status ----

def test_update_status(setup):
    repo, discussion, _ = setup
    created = repo.create(
        reporter_id=1,
        target_type="discussion",
        target_id=discussion.id,
        reason="spam",
    )
    assert created["status"] == "pending"

    updated = repo.update_status(created["id"], "resolved")
    assert updated is not None
    assert updated["status"] == "resolved"
    assert updated["id"] == created["id"]


def test_update_status_to_dismissed(setup):
    repo, discussion, _ = setup
    created = repo.create(
        reporter_id=1,
        target_type="discussion",
        target_id=discussion.id,
        reason="spam",
    )
    updated = repo.update_status(created["id"], "dismissed")
    assert updated["status"] == "dismissed"


def test_update_status_nonexistent(setup):
    repo, _, _ = setup
    result = repo.update_status(999, "resolved")
    assert result is None


# ---- has_reported ----

def test_has_reported_true(setup):
    repo, discussion, _ = setup
    repo.create(
        reporter_id=1,
        target_type="discussion",
        target_id=discussion.id,
        reason="spam",
    )
    assert repo.has_reported(1, "discussion", discussion.id) is True


def test_has_reported_false(setup):
    repo, discussion, _ = setup
    assert repo.has_reported(1, "discussion", discussion.id) is False


def test_has_reported_different_target_type(setup):
    repo, discussion, reply = setup
    repo.create(
        reporter_id=1,
        target_type="discussion",
        target_id=discussion.id,
        reason="spam",
    )
    # Same reporter, but target_type is "reply" -- should be False
    assert repo.has_reported(1, "reply", reply.id) is False


def test_has_reported_different_user(setup):
    repo, discussion, _ = setup
    repo.create(
        reporter_id=1,
        target_type="discussion",
        target_id=discussion.id,
        reason="spam",
    )
    # Different reporter -- should be False
    assert repo.has_reported(2, "discussion", discussion.id) is False


# ---- Duplicate report (UNIQUE constraint) ----

def test_duplicate_report_raises_integrity_error(setup):
    repo, discussion, _ = setup
    repo.create(
        reporter_id=1,
        target_type="discussion",
        target_id=discussion.id,
        reason="spam",
    )
    with pytest.raises(sqlite3.IntegrityError):
        repo.create(
            reporter_id=1,
            target_type="discussion",
            target_id=discussion.id,
            reason="offensive",
        )


def test_same_reporter_different_targets_allowed(setup):
    repo, discussion, reply = setup
    # Same reporter can report different targets
    r1 = repo.create(reporter_id=1, target_type="discussion", target_id=discussion.id, reason="spam")
    r2 = repo.create(reporter_id=1, target_type="reply", target_id=reply.id, reason="harassment")
    assert r1["id"] != r2["id"]


def test_different_reporters_same_target_allowed(setup):
    repo, discussion, _ = setup
    # Different reporters can report the same target
    r1 = repo.create(reporter_id=1, target_type="discussion", target_id=discussion.id, reason="spam")
    r2 = repo.create(reporter_id=2, target_type="discussion", target_id=discussion.id, reason="offensive")
    assert r1["id"] != r2["id"]
