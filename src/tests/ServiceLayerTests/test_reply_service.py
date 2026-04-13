import pytest
from unittest.mock import Mock

from Backend.ServiceLayer.ReplyService import ReplyService, REPLY_CREATE_XP, REPLY_ACCEPTED_XP, ACCEPT_SOLUTION_XP, REPLY_UPVOTE_XP, REPLY_REACTION_XP
from Backend.DomainLayer.Discussion import Discussion
from Backend.DomainLayer.Reply import Reply
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole, ThreadCategory, ReactionType
from Backend.DomainLayer.Exceptions import ValidationError


def make_service():
    reply_repo = Mock()
    discussion_repo = Mock()
    user_repo = Mock()
    auth_service = Mock()
    xp_service = Mock()
    return ReplyService(
        reply_repo=reply_repo,
        discussion_repo=discussion_repo,
        user_repo=user_repo,
        auth_service=auth_service,
        xp_service=xp_service,
    )


def make_user(user_id=1, role=UserRole.SOLVER):
    return User(id=user_id, username=f"user{user_id}", role=role, xp=100)


def make_discussion(discussion_id=1, author_id=1, is_locked=False):
    d = Discussion(id=discussion_id, title="Test", body="Body", author_id=author_id, category=ThreadCategory.GENERAL)
    d.is_locked = is_locked
    return d


def make_reply(reply_id=1, discussion_id=1, author_id=1, is_accepted=False, parent_reply_id=None):
    r = Reply(id=reply_id, discussion_id=discussion_id, author_id=author_id, body="Reply body", parent_reply_id=parent_reply_id)
    r.is_accepted = is_accepted
    return r


class TestCreateReply:
    def test_success(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = make_discussion()
        created = make_reply()
        svc.reply_repo.create.return_value = created
        svc.user_repo.get_by_id.return_value = make_user()
        svc.xp._apply_xp.return_value = REPLY_CREATE_XP

        result = svc.create_reply("token", 1, {"body": "My reply"})
        assert result["body"] == "Reply body"
        svc.reply_repo.create.assert_called_once()
        svc.discussion_repo.increment_reply_count.assert_called_once_with(1, 1, commit=False)
        svc.xp._apply_xp.assert_called_once_with(1, REPLY_CREATE_XP)

    def test_locked_discussion(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user()
        svc.discussion_repo.get_by_id.return_value = make_discussion(is_locked=True)

        with pytest.raises(ValidationError, match="locked"):
            svc.create_reply("token", 1, {"body": "Nope"})

    def test_missing_body(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user()
        svc.discussion_repo.get_by_id.return_value = make_discussion()

        with pytest.raises(ValidationError, match="body"):
            svc.create_reply("token", 1, {"body": ""})

    def test_discussion_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user()
        svc.discussion_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="not found"):
            svc.create_reply("token", 1, {"body": "Reply"})

    def test_with_parent_reply(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = make_discussion()
        parent = make_reply(reply_id=5, discussion_id=1)
        svc.reply_repo.get_by_id.return_value = parent
        created = make_reply(parent_reply_id=5)
        svc.reply_repo.create.return_value = created
        svc.user_repo.get_by_id.return_value = make_user()
        svc.xp._apply_xp.return_value = REPLY_CREATE_XP

        result = svc.create_reply("token", 1, {"body": "Nested reply", "parent_reply_id": 5})
        svc.reply_repo.create.assert_called_once()

    def test_invalid_parent_reply(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user()
        svc.discussion_repo.get_by_id.return_value = make_discussion()
        svc.reply_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="invalid parent"):
            svc.create_reply("token", 1, {"body": "Reply", "parent_reply_id": 999})


class TestUpdateReply:
    def test_owner_can_update(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = make_reply(author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(1)
        updated = make_reply()
        svc.reply_repo.update.return_value = updated

        result = svc.update_reply("token", 1, {"body": "Updated"})
        assert result["body"] == "Reply body"

    def test_non_owner_cannot_update(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 2
        svc.reply_repo.get_by_id.return_value = make_reply(author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(2)

        with pytest.raises(ValidationError, match="not allowed"):
            svc.update_reply("token", 1, {"body": "Nope"})


class TestDeleteReply:
    def test_owner_can_delete(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = make_reply(author_id=1, discussion_id=1)
        svc.user_repo.get_by_id.return_value = make_user(1)

        result = svc.delete_reply("token", 1)
        assert result["deleted"] is True
        svc.discussion_repo.increment_reply_count.assert_called_once_with(1, -1, commit=False)


class TestAcceptReply:
    def test_thread_author_can_accept(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1  # Thread author
        reply = make_reply(reply_id=5, author_id=2)  # Reply by someone else
        svc.reply_repo.get_by_id.return_value = reply
        svc.discussion_repo.get_by_id.return_value = make_discussion(author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(1)

        # After accept, return updated reply
        accepted = make_reply(reply_id=5, author_id=2, is_accepted=True)
        svc.reply_repo.update.return_value = None
        # get_by_id called after update returns accepted version
        svc.reply_repo.get_by_id.side_effect = [reply, accepted]
        user2 = make_user(2)
        svc.user_repo.get_by_id.side_effect = [make_user(1), user2]
        svc.xp._apply_xp.return_value = 0

        # Mock conn.execute to return cursor with rowcount=1 and subscriptable fetchone
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {"is_accepted": 0}  # not yet accepted
        svc.reply_repo.conn = Mock()
        svc.reply_repo.conn.execute.return_value = mock_cursor

        result = svc.accept_reply("token", 5)
        assert result["is_accepted"] is True
        # XP awarded: +25 to reply author (2), +5 to acceptor (1)
        svc.xp._apply_xp.assert_any_call(2, REPLY_ACCEPTED_XP)
        svc.xp._apply_xp.assert_any_call(1, ACCEPT_SOLUTION_XP)

    def test_non_author_cannot_accept(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 3  # Not thread author
        svc.reply_repo.get_by_id.return_value = make_reply(reply_id=5, author_id=2)
        svc.discussion_repo.get_by_id.return_value = make_discussion(author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(3)

        with pytest.raises(ValidationError, match="only"):
            svc.accept_reply("token", 5)

    def test_admin_can_accept(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 3  # Admin, not thread author
        reply = make_reply(reply_id=5, author_id=2)
        svc.reply_repo.get_by_id.return_value = reply
        svc.discussion_repo.get_by_id.return_value = make_discussion(author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(3, role=UserRole.ADMIN)

        accepted = make_reply(reply_id=5, author_id=2, is_accepted=True)
        svc.reply_repo.get_by_id.side_effect = [reply, accepted]
        svc.user_repo.get_by_id.side_effect = [make_user(3, role=UserRole.ADMIN), make_user(2)]
        svc.xp._apply_xp.return_value = 0

        # Mock conn.execute to return cursor with rowcount=1 and subscriptable fetchone
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {"is_accepted": 0}  # not yet accepted
        svc.reply_repo.conn = Mock()
        svc.reply_repo.conn.execute.return_value = mock_cursor

        result = svc.accept_reply("token", 5)
        assert result["is_accepted"] is True

    def test_unaccept_already_accepted(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        reply = make_reply(reply_id=5, author_id=2, is_accepted=True)
        svc.reply_repo.get_by_id.return_value = reply
        svc.discussion_repo.get_by_id.return_value = make_discussion(author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(1)

        unaccepted = make_reply(reply_id=5, author_id=2, is_accepted=False)
        svc.reply_repo.get_by_id.side_effect = [reply, unaccepted]
        svc.user_repo.get_by_id.side_effect = [make_user(1), make_user(2)]

        # Mock conn with fetchone returning is_accepted=1 (already accepted)
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {"is_accepted": 1}
        svc.reply_repo.conn = Mock()
        svc.reply_repo.conn.execute.return_value = mock_cursor

        result = svc.accept_reply("token", 5)
        assert result["is_accepted"] is False
        # No XP should be awarded for unaccepting
        svc.xp._apply_xp.assert_not_called()


def make_service_with_engagement():
    """Service with engagement repo for vote/react tests."""
    reply_repo = Mock()
    discussion_repo = Mock()
    user_repo = Mock()
    auth_service = Mock()
    xp_service = Mock()
    engagement_repo = Mock()
    return ReplyService(
        reply_repo=reply_repo,
        discussion_repo=discussion_repo,
        user_repo=user_repo,
        auth_service=auth_service,
        xp_service=xp_service,
        engagement_repo=engagement_repo,
    )


class TestVoteReply:
    def test_upvote_success(self):
        svc = make_service_with_engagement()
        svc.auth.require_user_id.return_value = 2
        svc.reply_repo.get_by_id.return_value = make_reply(reply_id=1, author_id=1)
        svc.engagement.get_reply_vote.return_value = None
        svc.engagement.set_reply_vote.return_value = 1
        svc.reply_repo.sync_votes_from_votes.return_value = {"upvotes": 1, "downvotes": 0}

        result = svc.vote_reply("token", 1, 1)

        assert result["upvotes"] == 1
        svc.xp._apply_xp.assert_called_once_with(1, REPLY_UPVOTE_XP)
        svc.reply_repo.sync_votes_from_votes.assert_called_once_with(1)

    def test_downvote_success(self):
        svc = make_service_with_engagement()
        svc.auth.require_user_id.return_value = 2
        svc.reply_repo.get_by_id.return_value = make_reply(reply_id=1, author_id=1)
        svc.engagement.get_reply_vote.return_value = None
        svc.engagement.set_reply_vote.return_value = -1
        svc.reply_repo.sync_votes_from_votes.return_value = {"upvotes": 0, "downvotes": 1}

        result = svc.vote_reply("token", 1, -1)

        assert result["downvotes"] == 1
        svc.xp._apply_xp.assert_not_called()
        svc.reply_repo.sync_votes_from_votes.assert_called_once_with(1)

    def test_toggle_removes_vote(self):
        svc = make_service_with_engagement()
        svc.auth.require_user_id.return_value = 2
        svc.reply_repo.get_by_id.return_value = make_reply(reply_id=1, author_id=1)
        svc.engagement.get_reply_vote.return_value = 1  # already upvoted
        svc.engagement.set_reply_vote.return_value = None
        svc.reply_repo.sync_votes_from_votes.return_value = {"upvotes": 0, "downvotes": 0}

        result = svc.vote_reply("token", 1, 1)

        assert result["user_vote"] is None
        svc.reply_repo.sync_votes_from_votes.assert_called_once_with(1)


class TestReactToReply:
    def test_add_reaction(self):
        svc = make_service_with_engagement()
        svc.auth.require_user_id.return_value = 2
        svc.reply_repo.get_by_id.return_value = make_reply(reply_id=1, author_id=1)
        svc.engagement.toggle_reply_reaction.return_value = True
        svc.engagement.get_reply_reactions.return_value = [{"type": "helpful", "count": 1}]
        svc.engagement.get_user_reply_reactions.return_value = ["helpful"]

        result = svc.react_to_reply("token", 1, "helpful")

        assert result["is_active"] is True
        svc.xp._apply_xp.assert_called_once_with(1, REPLY_REACTION_XP)

    def test_remove_reaction(self):
        svc = make_service_with_engagement()
        svc.auth.require_user_id.return_value = 2
        svc.reply_repo.get_by_id.return_value = make_reply(reply_id=1, author_id=1)
        svc.engagement.toggle_reply_reaction.return_value = False
        svc.engagement.get_reply_reactions.return_value = []
        svc.engagement.get_user_reply_reactions.return_value = []

        result = svc.react_to_reply("token", 1, "helpful")

        assert result["is_active"] is False
        svc.xp._apply_xp.assert_not_called()


class TestBanEnforcementReply:
    def test_banned_user_cannot_create_reply(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        user = make_user(user_id=1)
        user.is_discussion_banned = True
        svc.user_repo.get_by_id.return_value = user
        svc.discussion_repo.get_by_id.return_value = make_discussion(is_locked=False)

        with pytest.raises(ValidationError, match="banned"):
            svc.create_reply("token", 1, {"body": "I am banned"})
