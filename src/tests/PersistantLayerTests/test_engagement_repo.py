import sqlite3
import pytest

from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.DiscussionRepo import DiscussionRepo
from Backend.PersistantLayer.ReplyRepo import ReplyRepo
from Backend.PersistantLayer.EngagementRepo import EngagementRepo
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
    engagement_repo = EngagementRepo(conn)

    # Create test users
    alice = User(id=0, username="alice", role=UserRole.SOLVER, xp=0)
    user_repo.create(alice, password="pw")
    bob = User(id=0, username="bob", role=UserRole.SOLVER, xp=0)
    user_repo.create(bob, password="pw")

    # Create a test discussion
    discussion = Discussion(
        id=0, title="Test", body="Test body", author_id=1,
        category=ThreadCategory.GENERAL,
    )
    discussion = discussion_repo.create(discussion)

    # Create a test reply
    reply = Reply(id=0, discussion_id=discussion.id, author_id=2, body="Reply body")
    reply = reply_repo.create(reply)

    return engagement_repo, discussion, reply


# ---- Discussion Votes ----

def test_set_discussion_vote_upvote(setup):
    repo, discussion, _ = setup
    result = repo.set_discussion_vote(discussion.id, 1, 1)
    assert result == 1
    assert repo.get_discussion_vote(discussion.id, 1) == 1


def test_set_discussion_vote_toggle_off(setup):
    repo, discussion, _ = setup
    repo.set_discussion_vote(discussion.id, 1, 1)
    result = repo.set_discussion_vote(discussion.id, 1, 1)  # same vote again
    assert result is None
    assert repo.get_discussion_vote(discussion.id, 1) is None


def test_set_discussion_vote_change(setup):
    repo, discussion, _ = setup
    repo.set_discussion_vote(discussion.id, 1, 1)
    result = repo.set_discussion_vote(discussion.id, 1, -1)
    assert result == -1
    assert repo.get_discussion_vote(discussion.id, 1) == -1


def test_count_discussion_votes(setup):
    repo, discussion, _ = setup
    repo.set_discussion_vote(discussion.id, 1, 1)  # alice upvotes
    repo.set_discussion_vote(discussion.id, 2, -1)  # bob downvotes
    counts = repo.count_discussion_votes(discussion.id)
    assert counts == {"upvotes": 1, "downvotes": 1}


# ---- Reply Votes ----

def test_set_reply_vote(setup):
    repo, _, reply = setup
    result = repo.set_reply_vote(reply.id, 1, 1)
    assert result == 1
    counts = repo.count_reply_votes(reply.id)
    assert counts["upvotes"] == 1


def test_reply_vote_toggle(setup):
    repo, _, reply = setup
    repo.set_reply_vote(reply.id, 1, 1)
    repo.set_reply_vote(reply.id, 1, 1)  # toggle off
    counts = repo.count_reply_votes(reply.id)
    assert counts["upvotes"] == 0


# ---- Discussion Reactions ----

def test_toggle_discussion_reaction_on(setup):
    repo, discussion, _ = setup
    result = repo.toggle_discussion_reaction(discussion.id, 1, "insightful")
    assert result is True
    reactions = repo.get_discussion_reactions(discussion.id)
    assert len(reactions) == 1
    assert reactions[0]["type"] == "insightful"
    assert reactions[0]["count"] == 1


def test_toggle_discussion_reaction_off(setup):
    repo, discussion, _ = setup
    repo.toggle_discussion_reaction(discussion.id, 1, "insightful")
    result = repo.toggle_discussion_reaction(discussion.id, 1, "insightful")
    assert result is False
    reactions = repo.get_discussion_reactions(discussion.id)
    assert len(reactions) == 0


def test_get_user_discussion_reactions(setup):
    repo, discussion, _ = setup
    repo.toggle_discussion_reaction(discussion.id, 1, "insightful")
    repo.toggle_discussion_reaction(discussion.id, 1, "helpful")
    user_reactions = repo.get_user_discussion_reactions(discussion.id, 1)
    assert set(user_reactions) == {"insightful", "helpful"}


# ---- Reply Reactions ----

def test_toggle_reply_reaction(setup):
    repo, _, reply = setup
    result = repo.toggle_reply_reaction(reply.id, 1, "genius")
    assert result is True
    reactions = repo.get_reply_reactions(reply.id)
    assert len(reactions) == 1
    assert reactions[0]["type"] == "genius"


def test_get_user_reply_reactions(setup):
    repo, _, reply = setup
    repo.toggle_reply_reaction(reply.id, 1, "genius")
    user_reactions = repo.get_user_reply_reactions(reply.id, 1)
    assert user_reactions == ["genius"]


# ---- Follows ----

def test_toggle_follow_on(setup):
    repo, discussion, _ = setup
    result = repo.toggle_follow(discussion.id, 1)
    assert result is True
    assert repo.is_following(discussion.id, 1) is True


def test_toggle_follow_off(setup):
    repo, discussion, _ = setup
    repo.toggle_follow(discussion.id, 1)
    result = repo.toggle_follow(discussion.id, 1)
    assert result is False
    assert repo.is_following(discussion.id, 1) is False


def test_get_follower_ids(setup):
    repo, discussion, _ = setup
    repo.toggle_follow(discussion.id, 1)
    repo.toggle_follow(discussion.id, 2)
    followers = repo.get_follower_ids(discussion.id)
    assert set(followers) == {1, 2}


# ---- Bookmarks ----

def test_toggle_bookmark_on(setup):
    repo, discussion, _ = setup
    result = repo.toggle_bookmark(discussion.id, 1)
    assert result is True
    assert repo.is_bookmarked(discussion.id, 1) is True


def test_toggle_bookmark_off(setup):
    repo, discussion, _ = setup
    repo.toggle_bookmark(discussion.id, 1)
    result = repo.toggle_bookmark(discussion.id, 1)
    assert result is False
    assert repo.is_bookmarked(discussion.id, 1) is False


def test_get_user_bookmarked_ids(setup):
    repo, discussion, _ = setup
    repo.toggle_bookmark(discussion.id, 1)
    bookmarked = repo.get_user_bookmarked_ids(1)
    assert bookmarked == [discussion.id]


# ---- Bulk engagement data ----

def test_get_discussion_engagement(setup):
    repo, discussion, _ = setup
    repo.set_discussion_vote(discussion.id, 1, 1)
    repo.toggle_discussion_reaction(discussion.id, 1, "helpful")
    repo.toggle_follow(discussion.id, 1)
    repo.toggle_bookmark(discussion.id, 1)

    engagement = repo.get_discussion_engagement(discussion.id, 1)
    assert engagement["upvotes"] == 1
    assert engagement["downvotes"] == 0
    assert engagement["user_vote"] == 1
    assert len(engagement["reactions"]) == 1
    assert engagement["user_reactions"] == ["helpful"]
    assert engagement["is_following"] is True
    assert engagement["is_bookmarked"] is True


def test_get_reply_engagement(setup):
    repo, _, reply = setup
    repo.set_reply_vote(reply.id, 1, -1)
    repo.toggle_reply_reaction(reply.id, 1, "thinking")

    engagement = repo.get_reply_engagement(reply.id, 1)
    assert engagement["upvotes"] == 0
    assert engagement["downvotes"] == 1
    assert engagement["user_vote"] == -1
    assert len(engagement["reactions"]) == 1
    assert engagement["user_reactions"] == ["thinking"]
