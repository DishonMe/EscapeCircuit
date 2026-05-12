"""Coverage tests for ReplyService — focused on get_replies path, update/delete
permission branches, accept_reply edge cases, vote/react error paths."""

import sqlite3
import pytest
from unittest.mock import Mock, patch

from Backend.ServiceLayer.ReplyService import ReplyService
from Backend.DomainLayer.Reply import Reply
from Backend.DomainLayer.Discussion import Discussion
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole, ThreadCategory, ReactionType
from Backend.DomainLayer.Exceptions import ValidationError


def _make_service(with_engagement=True):
    reply_repo = Mock()
    reply_repo.conn = Mock()
    discussion_repo = Mock()
    user_repo = Mock()
    auth = Mock()
    xp = Mock()
    engagement = Mock() if with_engagement else None
    svc = ReplyService(reply_repo, discussion_repo, user_repo, auth, xp, engagement_repo=engagement)
    return svc


def _user(uid=1, role=UserRole.SOLVER):
    return User(id=uid, username=f"u{uid}", role=role)


def _disc(did=1, author_id=1, locked=False):
    d = Discussion(id=did, title="T", body="B", author_id=author_id, category=ThreadCategory.GENERAL)
    d.is_locked = locked
    return d


def _reply(rid=1, did=1, author_id=1, parent=None):
    return Reply(id=rid, discussion_id=did, body="x", author_id=author_id, parent_reply_id=parent)


# ---------------------------------------------------------------------------
# create_reply — integrity error during transaction
# ---------------------------------------------------------------------------

class TestCreateReplyEdge:
    def test_integrity_error_translates_to_deleted_discussion(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = _user(1)
        svc.discussion_repo.get_by_id.return_value = _disc()
        # transaction tries BEGIN then `create`; raise IntegrityError on create
        svc.reply_repo.create.side_effect = sqlite3.IntegrityError("fk")
        with pytest.raises(ValidationError, match="was deleted"):
            svc.create_reply("tok", 1, {"body": "hi"})

    def test_create_reply_locked_discussion(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = _user(1)
        svc.discussion_repo.get_by_id.return_value = _disc(locked=True)
        with pytest.raises(ValidationError, match="locked"):
            svc.create_reply("tok", 1, {"body": "hi"})

    def test_create_reply_invalid_parent(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = _user(1)
        svc.discussion_repo.get_by_id.return_value = _disc(did=1)
        # parent reply belongs to a different discussion
        svc.reply_repo.get_by_id.return_value = _reply(rid=5, did=999)
        with pytest.raises(ValidationError, match="invalid parent"):
            svc.create_reply("tok", 1, {"body": "hi", "parent_reply_id": 5})

    def test_create_reply_parent_not_found(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = _user(1)
        svc.discussion_repo.get_by_id.return_value = _disc(did=1)
        svc.reply_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="invalid parent"):
            svc.create_reply("tok", 1, {"body": "hi", "parent_reply_id": 5})


# ---------------------------------------------------------------------------
# get_replies
# ---------------------------------------------------------------------------

class TestGetReplies:
    def test_get_replies_not_found(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="discussion not found"):
            svc.get_replies("tok", 1)

    def test_get_replies_with_authors(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = _disc()
        svc.reply_repo.list_by_discussion.return_value = [
            _reply(rid=1, did=1, author_id=2),
            _reply(rid=2, did=1, author_id=99),  # no author found
        ]
        svc.reply_repo.count_by_discussion.return_value = 2
        svc.user_repo.get_by_ids.return_value = {2: _user(2)}
        result = svc.get_replies("tok", 1)
        assert result["total"] == 2
        assert "author" in result["replies"][0]
        assert "author" not in result["replies"][1]


# ---------------------------------------------------------------------------
# update_reply — permission & validation branches
# ---------------------------------------------------------------------------

class TestUpdateReply:
    def test_not_found(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="reply not found"):
            svc.update_reply("tok", 1, {"body": "x"})

    def test_not_allowed(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(author_id=999)
        svc.user_repo.get_by_id.return_value = _user(1)
        with pytest.raises(ValidationError, match="not allowed"):
            svc.update_reply("tok", 1, {"body": "x"})

    def test_empty_body(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(author_id=1)
        svc.user_repo.get_by_id.return_value = _user(1)
        with pytest.raises(ValidationError, match="body is required"):
            svc.update_reply("tok", 1, {"body": "  "})

    def test_repo_update_returns_none(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(author_id=1)
        svc.user_repo.get_by_id.return_value = _user(1)
        svc.reply_repo.update.return_value = None
        with pytest.raises(ValidationError, match="reply not found"):
            svc.update_reply("tok", 1, {"body": "x"})

    def test_admin_can_update(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 99
        svc.reply_repo.get_by_id.return_value = _reply(author_id=1)
        svc.user_repo.get_by_id.return_value = _user(99, UserRole.ADMIN)
        updated = _reply(author_id=1)
        svc.reply_repo.update.return_value = updated
        # No author on second get
        result = svc.update_reply("tok", 1, {"body": "new"})
        assert result["id"] == "1"


# ---------------------------------------------------------------------------
# delete_reply
# ---------------------------------------------------------------------------

class TestDeleteReply:
    def test_not_found(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="reply not found"):
            svc.delete_reply("tok", 1)

    def test_not_allowed(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(author_id=999)
        svc.user_repo.get_by_id.return_value = _user(1)
        with pytest.raises(ValidationError, match="not allowed"):
            svc.delete_reply("tok", 1)

    def test_owner_can_delete(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(author_id=1)
        svc.user_repo.get_by_id.return_value = _user(1)
        svc.reply_repo.delete.return_value = True
        result = svc.delete_reply("tok", 1)
        assert result["deleted"] is True

    def test_delete_returns_false_no_decrement(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(author_id=1)
        svc.user_repo.get_by_id.return_value = _user(1)
        svc.reply_repo.delete.return_value = False
        result = svc.delete_reply("tok", 1)
        assert result["deleted"] is True
        svc.discussion_repo.increment_reply_count.assert_not_called()


# ---------------------------------------------------------------------------
# accept_reply
# ---------------------------------------------------------------------------

class TestAcceptReply:
    def test_not_found(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="reply not found"):
            svc.accept_reply("tok", 1)

    def test_discussion_not_found(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply()
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="discussion not found"):
            svc.accept_reply("tok", 1)

    def test_not_thread_author(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(author_id=2)
        svc.discussion_repo.get_by_id.return_value = _disc(author_id=999)
        svc.user_repo.get_by_id.return_value = _user(1)
        with pytest.raises(ValidationError, match="only the thread author"):
            svc.accept_reply("tok", 1)

    def test_accept_path(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(rid=10, did=5, author_id=2)
        svc.discussion_repo.get_by_id.return_value = _disc(did=5, author_id=1)
        svc.user_repo.get_by_id.return_value = _user(1)
        # Mock transaction context: txn.execute(...).fetchone() = {is_accepted: 0}
        fresh_cursor = Mock()
        fresh_cursor.fetchone.return_value = {"is_accepted": 0}
        # UPDATE replies returns rowcount=1
        update_cursor = Mock()
        update_cursor.rowcount = 1
        svc.reply_repo.conn.execute.side_effect = [
            Mock(),                # BEGIN IMMEDIATE
            fresh_cursor,          # SELECT is_accepted
            update_cursor,         # UPDATE replies SET is_accepted=1
            Mock(),                # UPDATE discussions SET accepted_reply_id
            Mock(),                # UPDATE replies SET is_accepted=0 for others
            Mock(),                # COMMIT
        ]
        # For final re-read
        svc.reply_repo.get_by_id.side_effect = [
            _reply(rid=10, did=5, author_id=2),  # used in service initial get
        ]
        # Provide it after transaction
        # Actually accept_reply calls get_by_id once at start, then again at end
        # Configure side_effect to return reply both times
        svc.reply_repo.get_by_id.side_effect = [
            _reply(rid=10, did=5, author_id=2),
            _reply(rid=10, did=5, author_id=2),
        ]
        result = svc.accept_reply("tok", 10)
        assert result["id"] == "10"
        # XP awarded — author != accepter, so REPLY_ACCEPTED_XP + ACCEPT_SOLUTION_XP
        assert svc.xp._apply_xp.call_count == 2

    def test_unaccept_path(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(rid=10, did=5, author_id=2)
        svc.discussion_repo.get_by_id.return_value = _disc(did=5, author_id=1)
        svc.user_repo.get_by_id.return_value = _user(1)
        # is_accepted = 1 → unaccept path
        fresh = Mock()
        fresh.fetchone.return_value = {"is_accepted": 1}
        svc.reply_repo.conn.execute.side_effect = [
            Mock(),  # BEGIN
            fresh,   # SELECT
            Mock(),  # UPDATE discussion SET accepted_reply_id = NULL
            Mock(),  # UPDATE replies SET is_accepted = 0
            Mock(),  # COMMIT
        ]
        # The "updated" lookup inside the unaccept branch
        svc.reply_repo.get_by_id.side_effect = [
            _reply(rid=10, did=5, author_id=2),  # initial
            _reply(rid=10, did=5, author_id=2),  # after unaccept
        ]
        result = svc.accept_reply("tok", 10)
        assert result["id"] == "10"
        # XP not awarded on unaccept
        svc.xp._apply_xp.assert_not_called()

    def test_fresh_not_found_in_transaction(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(rid=10, did=5, author_id=2)
        svc.discussion_repo.get_by_id.return_value = _disc(did=5, author_id=1)
        svc.user_repo.get_by_id.return_value = _user(1)
        fresh = Mock()
        fresh.fetchone.return_value = None
        svc.reply_repo.conn.execute.side_effect = [Mock(), fresh, Mock()]
        with pytest.raises(ValidationError, match="reply not found"):
            svc.accept_reply("tok", 10)


# ---------------------------------------------------------------------------
# vote_reply / react_to_reply error paths
# ---------------------------------------------------------------------------

class TestVoteReactBranches:
    def test_vote_engagement_unavailable(self):
        svc = _make_service(with_engagement=False)
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="engagement not available"):
            svc.vote_reply("tok", 1, 1)

    def test_vote_invalid_value(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="1 or -1"):
            svc.vote_reply("tok", 1, 2)

    def test_vote_reply_not_found(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="reply not found"):
            svc.vote_reply("tok", 1, 1)

    def test_vote_self_no_xp(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(author_id=1)
        svc.engagement.get_reply_vote.return_value = None
        svc.engagement.set_reply_vote.return_value = 1
        svc.reply_repo.sync_votes_from_votes.return_value = {"upvotes": 0, "downvotes": 0}
        svc.vote_reply("tok", 1, 1)
        svc.engagement.try_award_engagement_xp.assert_not_called()

    def test_vote_xp_awarded(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(author_id=99)
        svc.engagement.get_reply_vote.return_value = None
        svc.engagement.set_reply_vote.return_value = 1
        svc.engagement.try_award_engagement_xp.return_value = True
        svc.reply_repo.sync_votes_from_votes.return_value = {"upvotes": 1, "downvotes": 0}
        svc.vote_reply("tok", 1, 1)
        svc.xp._apply_xp.assert_called_once()

    def test_react_engagement_unavailable(self):
        svc = _make_service(with_engagement=False)
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="engagement not available"):
            svc.react_to_reply("tok", 1, ReactionType.INSIGHTFUL.value)

    def test_react_invalid_type(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="invalid reaction"):
            svc.react_to_reply("tok", 1, "garbage")

    def test_react_reply_not_found(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="reply not found"):
            svc.react_to_reply("tok", 1, ReactionType.INSIGHTFUL.value)

    def test_react_self_no_xp(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(author_id=1)
        svc.engagement.toggle_reply_reaction.return_value = True
        svc.engagement.get_reply_reactions.return_value = []
        svc.engagement.get_user_reply_reactions.return_value = []
        svc.react_to_reply("tok", 1, ReactionType.INSIGHTFUL.value)
        svc.engagement.try_award_engagement_xp.assert_not_called()

    def test_react_xp_awarded(self):
        svc = _make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = _reply(author_id=99)
        svc.engagement.toggle_reply_reaction.return_value = True
        svc.engagement.try_award_engagement_xp.return_value = True
        svc.engagement.get_reply_reactions.return_value = []
        svc.engagement.get_user_reply_reactions.return_value = []
        svc.react_to_reply("tok", 1, ReactionType.INSIGHTFUL.value)
        svc.xp._apply_xp.assert_called_once()
