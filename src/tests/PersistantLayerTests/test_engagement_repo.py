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


class TestEngagementXPAward:
    """Tests for engagement XP deduplication"""
    
    def test_try_award_engagement_xp_first_time(self, setup):
        repo, discussion, _ = setup
        result = repo.try_award_engagement_xp("discussion", discussion.id, actor_user_id=1, xp_type="upvote")
        assert result is True

    def test_try_award_engagement_xp_duplicate(self, setup):
        repo, discussion, _ = setup
        repo.try_award_engagement_xp("discussion", discussion.id, actor_user_id=1, xp_type="upvote")
        result = repo.try_award_engagement_xp("discussion", discussion.id, actor_user_id=1, xp_type="upvote")
        assert result is False

    def test_try_award_engagement_xp_different_xp_type(self, setup):
        repo, discussion, _ = setup
        repo.try_award_engagement_xp("discussion", discussion.id, actor_user_id=1, xp_type="upvote")
        result = repo.try_award_engagement_xp("discussion", discussion.id, actor_user_id=1, xp_type="downvote")
        assert result is True

    def test_try_award_engagement_xp_different_actor(self, setup):
        repo, discussion, _ = setup
        repo.try_award_engagement_xp("discussion", discussion.id, actor_user_id=1, xp_type="upvote")
        result = repo.try_award_engagement_xp("discussion", discussion.id, actor_user_id=2, xp_type="upvote")
        assert result is True

    def test_try_award_engagement_xp_different_target(self, setup):
        repo, discussion, reply = setup
        repo.try_award_engagement_xp("discussion", discussion.id, actor_user_id=1, xp_type="upvote")
        result = repo.try_award_engagement_xp("reply", reply.id, actor_user_id=1, xp_type="upvote")
        assert result is True


class TestVotingEdgeCases:
    """Tests for voting special scenarios"""
    
    def test_get_discussion_vote_none_when_no_vote(self, setup):
        repo, discussion, _ = setup
        vote = repo.get_discussion_vote(discussion.id, 1)
        assert vote is None

    def test_get_discussion_vote_returns_correct_value(self, setup):
        repo, discussion, _ = setup
        repo.set_discussion_vote(discussion.id, 1, 1)
        vote = repo.get_discussion_vote(discussion.id, 1)
        assert vote == 1

    def test_count_discussion_votes_empty(self, setup):
        repo, discussion, _ = setup
        counts = repo.count_discussion_votes(discussion.id)
        assert counts == {"upvotes": 0, "downvotes": 0}

    def test_count_discussion_votes_only_upvotes(self, setup):
        repo, discussion, _ = setup
        repo.set_discussion_vote(discussion.id, 1, 1)
        repo.set_discussion_vote(discussion.id, 2, 1)
        counts = repo.count_discussion_votes(discussion.id)
        assert counts == {"upvotes": 2, "downvotes": 0}

    def test_count_discussion_votes_only_downvotes(self, setup):
        repo, discussion, _ = setup
        repo.set_discussion_vote(discussion.id, 1, -1)
        repo.set_discussion_vote(discussion.id, 2, -1)
        counts = repo.count_discussion_votes(discussion.id)
        assert counts == {"upvotes": 0, "downvotes": 2}

    def test_get_reply_vote_none(self, setup):
        repo, _, reply = setup
        vote = repo.get_reply_vote(reply.id, 1)
        assert vote is None

    def test_count_reply_votes_empty(self, setup):
        repo, _, reply = setup
        counts = repo.count_reply_votes(reply.id)
        assert counts == {"upvotes": 0, "downvotes": 0}


class TestReactionEdgeCases:
    """Tests for reaction special scenarios"""
    
    def test_toggle_discussion_reaction_multiple_types_same_user(self, setup):
        repo, discussion, _ = setup
        repo.toggle_discussion_reaction(discussion.id, 1, "insightful")
        repo.toggle_discussion_reaction(discussion.id, 1, "helpful")
        repo.toggle_discussion_reaction(discussion.id, 1, "thinking")
        
        reactions = repo.get_discussion_reactions(discussion.id)
        assert len(reactions) == 3
        types = {r["type"] for r in reactions}
        assert types == {"insightful", "helpful", "thinking"}

    def test_toggle_discussion_reaction_same_type_multiple_users(self, setup):
        repo, discussion, _ = setup
        repo.toggle_discussion_reaction(discussion.id, 1, "helpful")
        repo.toggle_discussion_reaction(discussion.id, 2, "helpful")
        
        reactions = repo.get_discussion_reactions(discussion.id)
        assert len(reactions) == 1
        assert reactions[0]["count"] == 2

    def test_get_discussion_reactions_empty(self, setup):
        repo, discussion, _ = setup
        reactions = repo.get_discussion_reactions(discussion.id)
        assert reactions == []

    def test_get_user_discussion_reactions_empty(self, setup):
        repo, discussion, _ = setup
        user_reactions = repo.get_user_discussion_reactions(discussion.id, 1)
        assert user_reactions == []

    def test_toggle_reply_reaction_multiple_times(self, setup):
        repo, _, reply = setup
        repo.toggle_reply_reaction(reply.id, 1, "genius")
        repo.toggle_reply_reaction(reply.id, 1, "genius")  # toggle off
        repo.toggle_reply_reaction(reply.id, 1, "genius")  # toggle on again
        
        reactions = repo.get_reply_reactions(reply.id)
        assert len(reactions) == 1
        assert reactions[0]["count"] == 1

    def test_get_reply_reactions_empty(self, setup):
        repo, _, reply = setup
        reactions = repo.get_reply_reactions(reply.id)
        assert reactions == []


class TestFollowBookmarkEdgeCases:
    """Tests for follow and bookmark special scenarios"""
    
    def test_get_follower_ids_empty(self, setup):
        repo, discussion, _ = setup
        followers = repo.get_follower_ids(discussion.id)
        assert followers == []

    def test_get_follower_ids_multiple(self, setup):
        repo, discussion, _ = setup
        repo.toggle_follow(discussion.id, 1)
        repo.toggle_follow(discussion.id, 2)
        
        followers = repo.get_follower_ids(discussion.id)
        assert set(followers) == {1, 2}

    def test_is_following_returns_correct_state(self, setup):
        repo, discussion, _ = setup
        assert repo.is_following(discussion.id, 1) is False
        repo.toggle_follow(discussion.id, 1)
        assert repo.is_following(discussion.id, 1) is True
        repo.toggle_follow(discussion.id, 1)
        assert repo.is_following(discussion.id, 1) is False

    def test_get_user_bookmarked_ids_empty(self, setup):
        repo, _, _ = setup
        bookmarked = repo.get_user_bookmarked_ids(1)
        assert bookmarked == []

    def test_get_user_bookmarked_ids_multiple(self, setup):
        repo, discussion, _ = setup
        # Create more discussions for bookmarking
        from Backend.PersistantLayer.DiscussionRepo import DiscussionRepo
        from Backend.DomainLayer.Enums import ThreadCategory
        discussion_repo = DiscussionRepo(repo.conn)
        
        d2 = Discussion(id=0, title="D2", body="Body", author_id=1, category=ThreadCategory.GENERAL)
        d2 = discussion_repo.create(d2)
        
        repo.toggle_bookmark(discussion.id, 1)
        repo.toggle_bookmark(d2.id, 1)
        
        bookmarked = repo.get_user_bookmarked_ids(1)
        assert len(bookmarked) == 2
        assert set(bookmarked) == {discussion.id, d2.id}

    def test_is_bookmarked_returns_correct_state(self, setup):
        repo, discussion, _ = setup
        assert repo.is_bookmarked(discussion.id, 1) is False
        repo.toggle_bookmark(discussion.id, 1)
        assert repo.is_bookmarked(discussion.id, 1) is True


class TestDiscussionEngagementAdvanced:
    """Tests for complex get_discussion_engagement scenarios"""
    
    def test_get_discussion_engagement_no_votes_or_reactions(self, setup):
        repo, discussion, _ = setup
        engagement = repo.get_discussion_engagement(discussion.id, 1)
        assert engagement["upvotes"] == 0
        assert engagement["downvotes"] == 0
        assert engagement["user_vote"] is None
        assert engagement["reactions"] == []
        assert engagement["user_reactions"] == []
        assert engagement["is_following"] is False
        assert engagement["is_bookmarked"] is False

    def test_get_discussion_engagement_multiple_votes(self, setup):
        repo, discussion, _ = setup
        repo.set_discussion_vote(discussion.id, 1, 1)
        repo.set_discussion_vote(discussion.id, 2, 1)
        
        engagement = repo.get_discussion_engagement(discussion.id, 1)
        assert engagement["upvotes"] == 2
        assert engagement["downvotes"] == 0
        assert engagement["user_vote"] == 1

    def test_get_discussion_engagement_multiple_reactions(self, setup):
        repo, discussion, _ = setup
        repo.toggle_discussion_reaction(discussion.id, 1, "helpful")
        repo.toggle_discussion_reaction(discussion.id, 2, "helpful")
        repo.toggle_discussion_reaction(discussion.id, 1, "insightful")
        
        engagement = repo.get_discussion_engagement(discussion.id, 1)
        assert len(engagement["reactions"]) == 2
        reaction_types = {r["type"] for r in engagement["reactions"]}
        assert reaction_types == {"helpful", "insightful"}
        assert set(engagement["user_reactions"]) == {"helpful", "insightful"}

    def test_get_discussion_engagement_user_isolation(self, setup):
        repo, discussion, _ = setup
        repo.set_discussion_vote(discussion.id, 2, 1)  # user 2 upvotes
        engagement = repo.get_discussion_engagement(discussion.id, 1)
        
        # User 1 didn't vote
        assert engagement["user_vote"] is None
        # But we still see the total votes
        assert engagement["upvotes"] == 1


class TestReplyEngagementBulk:
    """Tests for bulk reply engagement operations"""
    
    def test_get_bulk_reply_engagement_empty_list(self, setup):
        repo, _, _ = setup
        result = repo.get_bulk_reply_engagement([], 1)
        assert result == {}

    def test_get_bulk_reply_engagement_single_reply(self, setup):
        repo, _, reply = setup
        repo.set_reply_vote(reply.id, 1, 1)
        
        result = repo.get_bulk_reply_engagement([reply.id], 1)
        assert reply.id in result
        assert result[reply.id]["upvotes"] == 1
        assert result[reply.id]["downvotes"] == 0
        assert result[reply.id]["user_vote"] == 1

    def test_get_bulk_reply_engagement_multiple_replies(self, setup):
        repo, _, reply = setup
        from Backend.PersistantLayer.ReplyRepo import ReplyRepo
        reply_repo = ReplyRepo(repo.conn)
        
        reply2 = Reply(id=0, discussion_id=reply.discussion_id, author_id=1, body="Reply 2")
        reply2 = reply_repo.create(reply2)
        
        repo.set_reply_vote(reply.id, 1, 1)
        repo.set_reply_vote(reply2.id, 1, -1)
        repo.toggle_reply_reaction(reply.id, 1, "good")
        
        result = repo.get_bulk_reply_engagement([reply.id, reply2.id], 1)
        
        assert len(result) == 2
        assert result[reply.id]["upvotes"] == 1
        assert result[reply2.id]["downvotes"] == 1
        assert result[reply.id]["user_reactions"] == ["good"]

    def test_get_bulk_reply_engagement_with_duplicate_ids(self, setup):
        repo, _, reply = setup
        repo.set_reply_vote(reply.id, 1, 1)
        
        # Pass same reply ID twice
        result = repo.get_bulk_reply_engagement([reply.id, reply.id, reply.id], 1)
        
        # Should still only have one entry
        assert len(result) == 1
        assert result[reply.id]["upvotes"] == 1

    def test_get_bulk_reply_engagement_no_votes(self, setup):
        repo, _, reply = setup
        result = repo.get_bulk_reply_engagement([reply.id], 1)
        
        assert result[reply.id]["upvotes"] == 0
        assert result[reply.id]["downvotes"] == 0
        assert result[reply.id]["user_vote"] is None
        assert result[reply.id]["reactions"] == []
        assert result[reply.id]["user_reactions"] == []
