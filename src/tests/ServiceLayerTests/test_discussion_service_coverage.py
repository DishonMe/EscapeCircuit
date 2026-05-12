"""Coverage tests for DiscussionService — focuses on under-tested moderation,
engagement, reporting, and nested-reply branches."""

import sqlite3
import pytest
from unittest.mock import Mock, patch

from Backend.ServiceLayer.DiscussionService import DiscussionService
from Backend.DomainLayer.Discussion import Discussion
from Backend.DomainLayer.Reply import Reply
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole, ThreadCategory, ReactionType
from Backend.DomainLayer.Exceptions import ValidationError


def make_service(with_engagement=True, with_report=True, with_notif=True):
    discussion_repo = Mock()
    discussion_repo.conn = Mock()
    reply_repo = Mock()
    user_repo = Mock()
    auth_service = Mock()
    xp_service = Mock()
    engagement_repo = Mock() if with_engagement else None
    report_repo = Mock() if with_report else None
    notification_repo = Mock() if with_notif else None
    return DiscussionService(
        discussion_repo=discussion_repo,
        reply_repo=reply_repo,
        user_repo=user_repo,
        auth_service=auth_service,
        xp_service=xp_service,
        engagement_repo=engagement_repo,
        report_repo=report_repo,
        notification_repo=notification_repo,
    )


def make_user(uid=1, role=UserRole.SOLVER):
    return User(id=uid, username=f"u{uid}", role=role)


def make_discussion(did=1, author_id=1):
    return Discussion(id=did, title="T", body="B", author_id=author_id, category=ThreadCategory.GENERAL)


def make_reply(rid, author_id=1, parent=None, did=1):
    return Reply(id=rid, discussion_id=did, body="r", author_id=author_id, parent_reply_id=parent)


# ---------------------------------------------------------------------------
# get_discussion — nested reply tree & engagement
# ---------------------------------------------------------------------------

class TestGetDiscussionExtended:
    def test_get_discussion_with_three_level_nested_replies(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        disc = make_discussion(did=10, author_id=5)
        svc.discussion_repo.get_by_id.return_value = disc
        svc.discussion_repo.is_bookmarked.return_value = True

        # Build a 3-level tree
        top = make_reply(rid=1, author_id=2, parent=None, did=10)
        child = make_reply(rid=2, author_id=3, parent=1, did=10)
        grand = make_reply(rid=3, author_id=4, parent=2, did=10)
        # Reply with unknown parent (no parent) goes in top_level too
        orphan = make_reply(rid=4, author_id=5, parent=None, did=10)
        svc.reply_repo.list_by_discussion.return_value = [top, child, grand, orphan]

        users_map = {
            2: make_user(2), 3: make_user(3), 4: make_user(4), 5: make_user(5),
        }
        svc.user_repo.get_by_ids.return_value = users_map

        svc.engagement.get_discussion_engagement.return_value = {"upvotes": 5}
        svc.engagement.get_bulk_reply_engagement.return_value = {
            1: {"upvotes": 1, "downvotes": 0, "user_vote": None, "reactions": [], "user_reactions": []},
            # 2 missing → uses default
        }

        result = svc.get_discussion("token", 10)
        assert result["is_bookmarked"] is True
        # 2 top-level
        assert len(result["replies"]) == 2
        # First top has one child → which has one grandchild
        first = result["replies"][0]
        assert len(first["children"]) == 1
        assert len(first["children"][0]["children"]) == 1
        # Reply 2 used default engagement
        assert first["children"][0]["engagement"]["upvotes"] == 0

    def test_get_discussion_without_engagement(self):
        svc = make_service(with_engagement=False)
        svc.auth.require_user_id.return_value = 1
        disc = make_discussion(did=10, author_id=5)
        svc.discussion_repo.get_by_id.return_value = disc
        svc.discussion_repo.is_bookmarked.return_value = False
        svc.reply_repo.list_by_discussion.return_value = [
            make_reply(rid=1, author_id=2, parent=None, did=10)
        ]
        svc.user_repo.get_by_ids.return_value = {2: make_user(2), 5: make_user(5)}
        result = svc.get_discussion("token", 10)
        assert "engagement" not in result
        assert "engagement" not in result["replies"][0]

    def test_get_discussion_no_replies(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        disc = make_discussion(did=10, author_id=5)
        svc.discussion_repo.get_by_id.return_value = disc
        svc.discussion_repo.is_bookmarked.return_value = False
        svc.reply_repo.list_by_discussion.return_value = []
        svc.user_repo.get_by_ids.return_value = {5: make_user(5)}
        svc.engagement.get_discussion_engagement.return_value = {"upvotes": 0}
        result = svc.get_discussion("token", 10)
        # No reply engagement query when no replies
        svc.engagement.get_bulk_reply_engagement.assert_not_called()
        assert result["replies"] == []


# ---------------------------------------------------------------------------
# update_discussion — field-by-field branches
# ---------------------------------------------------------------------------

class TestUpdateDiscussionBranches:
    def setup_method(self):
        self.svc = make_service()
        self.svc.auth.require_user_id.return_value = 1
        self.disc = make_discussion(did=10, author_id=1)
        self.svc.discussion_repo.get_by_id.return_value = self.disc
        self.svc.user_repo.get_by_id.return_value = make_user(1)
        updated = make_discussion(did=10, author_id=1)
        self.svc.discussion_repo.update.return_value = updated

    def test_update_title_only(self):
        result = self.svc.update_discussion("tok", 10, {"title": "New"})
        assert result["id"] == "10"

    def test_update_title_empty_rejected(self):
        with pytest.raises(ValidationError, match="title is required"):
            self.svc.update_discussion("tok", 10, {"title": "   "})

    def test_update_body_empty_rejected(self):
        with pytest.raises(ValidationError, match="body is required"):
            self.svc.update_discussion("tok", 10, {"body": ""})

    def test_update_invalid_category(self):
        with pytest.raises(ValidationError, match="invalid category"):
            self.svc.update_discussion("tok", 10, {"category": "bogus"})

    def test_update_valid_category(self):
        self.svc.update_discussion("tok", 10, {"category": ThreadCategory.GENERAL.value})

    def test_update_nothing_to_update(self):
        with pytest.raises(ValidationError, match="nothing to update"):
            self.svc.update_discussion("tok", 10, {})

    def test_update_repo_returns_none(self):
        self.svc.discussion_repo.update.return_value = None
        with pytest.raises(ValidationError, match="discussion not found"):
            self.svc.update_discussion("tok", 10, {"title": "X"})

    def test_update_not_found(self):
        self.svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="discussion not found"):
            self.svc.update_discussion("tok", 10, {"title": "X"})


# ---------------------------------------------------------------------------
# delete_discussion / pin / lock — admin/owner paths
# ---------------------------------------------------------------------------

class TestDeletePinLock:
    def test_delete_admin(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 99
        svc.discussion_repo.get_by_id.return_value = make_discussion(did=10, author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(99, UserRole.ADMIN)
        result = svc.delete_discussion("tok", 10)
        assert result["deleted"] is True

    def test_delete_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.delete_discussion("tok", 10)

    def test_pin_not_admin(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1, UserRole.SOLVER)
        with pytest.raises(ValidationError, match="admin"):
            svc.pin_discussion("tok", 10)

    def test_pin_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1, UserRole.ADMIN)
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.pin_discussion("tok", 10)

    def test_lock_not_admin(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1, UserRole.SOLVER)
        with pytest.raises(ValidationError, match="admin"):
            svc.lock_discussion("tok", 10)

    def test_lock_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1, UserRole.ADMIN)
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.lock_discussion("tok", 10)


# ---------------------------------------------------------------------------
# vote / react / follow — error / engagement-absent paths
# ---------------------------------------------------------------------------

class TestEngagementErrorPaths:
    def test_vote_engagement_unavailable(self):
        svc = make_service(with_engagement=False)
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="engagement not available"):
            svc.vote_discussion("tok", 1, 1)

    def test_vote_invalid_value(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="1 or -1"):
            svc.vote_discussion("tok", 1, 5)

    def test_vote_discussion_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.vote_discussion("tok", 1, 1)

    def test_vote_no_xp_when_already_voted(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = make_discussion(did=1, author_id=2)
        svc.engagement.get_discussion_vote.return_value = 1  # already upvoted
        svc.engagement.set_discussion_vote.return_value = 1
        svc.discussion_repo.sync_upvotes_from_votes.return_value = {"upvotes": 1, "downvotes": 0}
        svc.vote_discussion("tok", 1, 1)
        # XP not awarded a second time
        svc.engagement.try_award_engagement_xp.assert_not_called()

    def test_vote_no_xp_when_self_vote(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        # Self-vote: author == voter
        svc.discussion_repo.get_by_id.return_value = make_discussion(did=1, author_id=1)
        svc.engagement.get_discussion_vote.return_value = None
        svc.engagement.set_discussion_vote.return_value = 1
        svc.discussion_repo.sync_upvotes_from_votes.return_value = {"upvotes": 1, "downvotes": 0}
        svc.vote_discussion("tok", 1, 1)
        svc.engagement.try_award_engagement_xp.assert_not_called()

    def test_react_invalid_type(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="invalid reaction"):
            svc.react_to_discussion("tok", 1, "not-a-reaction")

    def test_react_engagement_unavailable(self):
        svc = make_service(with_engagement=False)
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="engagement not available"):
            svc.react_to_discussion("tok", 1, ReactionType.INSIGHTFUL.value)

    def test_react_discussion_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.react_to_discussion("tok", 1, ReactionType.INSIGHTFUL.value)

    def test_react_self_no_xp(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = make_discussion(did=1, author_id=1)
        svc.engagement.toggle_discussion_reaction.return_value = True
        svc.engagement.get_discussion_reactions.return_value = []
        svc.engagement.get_user_discussion_reactions.return_value = []
        svc.react_to_discussion("tok", 1, ReactionType.INSIGHTFUL.value)
        svc.engagement.try_award_engagement_xp.assert_not_called()

    def test_follow_engagement_unavailable(self):
        svc = make_service(with_engagement=False)
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="engagement not available"):
            svc.follow_discussion("tok", 1)

    def test_follow_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.follow_discussion("tok", 1)

    def test_bookmark_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.bookmark_discussion("tok", 1)


# ---------------------------------------------------------------------------
# Reports — full path: missing, duplicate, invalid reason, integrity error
# ---------------------------------------------------------------------------

class TestReports:
    def test_report_discussion_no_repo(self):
        svc = make_service(with_report=False)
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="reporting not available"):
            svc.report_discussion("tok", 1, "spam")

    def test_report_discussion_invalid_reason(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="invalid reason"):
            svc.report_discussion("tok", 1, "not_valid")

    def test_report_discussion_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.report_discussion("tok", 1, "spam")

    def test_report_discussion_duplicate(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = make_discussion()
        svc.report_repo.has_reported.return_value = True
        with pytest.raises(ValidationError, match="already reported"):
            svc.report_discussion("tok", 1, "spam")

    def test_report_discussion_integrity_error_translated(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = make_discussion()
        svc.report_repo.has_reported.return_value = False
        svc.report_repo.create.side_effect = sqlite3.IntegrityError("dup")
        with pytest.raises(ValidationError, match="already reported"):
            svc.report_discussion("tok", 1, "spam")

    def test_report_reply_no_repo(self):
        svc = make_service(with_report=False)
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="reporting not available"):
            svc.report_reply("tok", 1, "spam")

    def test_report_reply_invalid_reason(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="invalid reason"):
            svc.report_reply("tok", 1, "bogus")

    def test_report_reply_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.report_reply("tok", 1, "spam")

    def test_report_reply_duplicate(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = make_reply(rid=1)
        svc.report_repo.has_reported.return_value = True
        with pytest.raises(ValidationError, match="already reported"):
            svc.report_reply("tok", 1, "spam")

    def test_report_reply_integrity_error(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = make_reply(rid=1)
        svc.report_repo.has_reported.return_value = False
        svc.report_repo.create.side_effect = sqlite3.IntegrityError("x")
        with pytest.raises(ValidationError, match="already reported"):
            svc.report_reply("tok", 1, "spam")

    def test_list_reports_no_repo(self):
        svc = make_service(with_report=False)
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="reporting not available"):
            svc.list_reports("tok")

    def test_list_reports_non_admin(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1, UserRole.SOLVER)
        with pytest.raises(ValidationError, match="admin only"):
            svc.list_reports("tok")

    def test_list_reports_admin_with_mixed_targets(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1, UserRole.ADMIN)
        svc.report_repo.list_all.return_value = [
            {"id": 1, "reporter_id": 1, "target_type": "discussion", "target_id": 10, "reason": "spam"},
            {"id": 2, "reporter_id": 2, "target_type": "reply", "target_id": 20, "reason": "spam"},
        ]
        svc.report_repo.count.return_value = 2
        svc.discussion_repo.get_by_ids.return_value = {10: make_discussion(did=10, author_id=5)}
        svc.reply_repo.get_by_ids.return_value = {20: make_reply(rid=20, author_id=6, did=30)}
        svc.user_repo.get_by_ids.return_value = {1: make_user(1), 2: make_user(2), 5: make_user(5), 6: make_user(6)}
        result = svc.list_reports("tok")
        assert result["total"] == 2
        # First report is discussion → has target_author info
        assert result["reports"][0]["target_author_id"] == 5
        # Second is reply → has discussion_id
        assert result["reports"][1]["discussion_id"] == 30

    def test_update_report_status_no_repo(self):
        svc = make_service(with_report=False)
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="reporting not available"):
            svc.update_report_status("tok", 1, "reviewed")

    def test_update_report_status_invalid(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1, UserRole.ADMIN)
        with pytest.raises(ValidationError, match="invalid status"):
            svc.update_report_status("tok", 1, "garbage")

    def test_update_report_status_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1, UserRole.ADMIN)
        svc.report_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="report not found"):
            svc.update_report_status("tok", 1, "reviewed")

    def test_update_report_status_non_admin(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1, UserRole.SOLVER)
        with pytest.raises(ValidationError, match="admin only"):
            svc.update_report_status("tok", 1, "reviewed")


# ---------------------------------------------------------------------------
# Moderation actions — warn / ban / delete / lock from report
# ---------------------------------------------------------------------------

class TestModerationActions:
    def setup_method(self):
        self.svc = make_service()
        self.svc.auth.require_user_id.return_value = 99
        self.svc.user_repo.get_by_id.return_value = make_user(99, UserRole.ADMIN)

    def test_warn_no_report_repo(self):
        svc = make_service(with_report=False)
        svc.auth.require_user_id.return_value = 99
        svc.user_repo.get_by_id.return_value = make_user(99, UserRole.ADMIN)
        with pytest.raises(ValidationError, match="reporting not available"):
            svc.warn_user_for_report("tok", 1)

    def test_warn_report_not_found(self):
        self.svc.report_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="report not found"):
            self.svc.warn_user_for_report("tok", 1)

    def test_warn_reply_path(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "reply", "target_id": 5, "reason": "spam",
        }
        self.svc.reply_repo.get_by_id.return_value = make_reply(rid=5, author_id=42)
        result = self.svc.warn_user_for_report("tok", 1)
        assert result["warned_user_id"] == 42
        self.svc.notification_repo.create.assert_called_once()

    def test_warn_unknown_target_type(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "unknown", "target_id": 5, "reason": "spam",
        }
        with pytest.raises(ValidationError, match="unknown target"):
            self.svc.warn_user_for_report("tok", 1)

    def test_warn_target_missing(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "discussion", "target_id": 5, "reason": "spam",
        }
        self.svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="reported discussion not found"):
            self.svc.warn_user_for_report("tok", 1)

    def test_warn_reply_target_missing(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "reply", "target_id": 5, "reason": "spam",
        }
        self.svc.reply_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="reported reply not found"):
            self.svc.warn_user_for_report("tok", 1)

    def test_ban_report_not_found(self):
        self.svc.report_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="report not found"):
            self.svc.ban_user_for_report("tok", 1)

    def test_ban_no_report_repo(self):
        svc = make_service(with_report=False)
        svc.auth.require_user_id.return_value = 99
        svc.user_repo.get_by_id.return_value = make_user(99, UserRole.ADMIN)
        with pytest.raises(ValidationError, match="reporting not available"):
            svc.ban_user_for_report("tok", 1)

    def test_delete_content_discussion(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "discussion", "target_id": 5,
        }
        self.svc.discussion_repo.get_by_id.return_value = make_discussion(did=5, author_id=42)
        result = self.svc.delete_reported_content("tok", 1)
        assert result["target_type"] == "discussion"
        self.svc.discussion_repo.delete.assert_called_once_with(5)

    def test_delete_content_discussion_already_gone(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "discussion", "target_id": 5,
        }
        self.svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="already been deleted"):
            self.svc.delete_reported_content("tok", 1)

    def test_delete_content_reply(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "reply", "target_id": 5,
        }
        reply = make_reply(rid=5, did=99)
        self.svc.reply_repo.get_by_id.return_value = reply
        self.svc.reply_repo.delete.return_value = True
        self.svc.delete_reported_content("tok", 1)
        self.svc.discussion_repo.increment_reply_count.assert_called_once_with(99, -1)

    def test_delete_content_reply_already_gone(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "reply", "target_id": 5,
        }
        self.svc.reply_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="already been deleted"):
            self.svc.delete_reported_content("tok", 1)

    def test_delete_content_reply_delete_returns_false(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "reply", "target_id": 5,
        }
        self.svc.reply_repo.get_by_id.return_value = make_reply(rid=5, did=99)
        self.svc.reply_repo.delete.return_value = False
        self.svc.delete_reported_content("tok", 1)
        # Did NOT decrement
        self.svc.discussion_repo.increment_reply_count.assert_not_called()

    def test_delete_content_no_report_repo(self):
        svc = make_service(with_report=False)
        svc.auth.require_user_id.return_value = 99
        svc.user_repo.get_by_id.return_value = make_user(99, UserRole.ADMIN)
        with pytest.raises(ValidationError, match="reporting not available"):
            svc.delete_reported_content("tok", 1)

    def test_lock_reported_discussion_not_discussion(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "reply", "target_id": 5,
        }
        with pytest.raises(ValidationError, match="can only lock discussions"):
            self.svc.lock_reported_discussion("tok", 1)

    def test_lock_reported_discussion_missing(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "discussion", "target_id": 5,
        }
        self.svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="discussion not found"):
            self.svc.lock_reported_discussion("tok", 1)

    def test_lock_reported_discussion_success(self):
        self.svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "discussion", "target_id": 5,
        }
        self.svc.discussion_repo.get_by_id.return_value = make_discussion(did=5)
        result = self.svc.lock_reported_discussion("tok", 1)
        assert result["action"] == "locked"
        self.svc.discussion_repo.update.assert_called_once_with(5, {"is_locked": True})

    def test_lock_reported_no_report_repo(self):
        svc = make_service(with_report=False)
        svc.auth.require_user_id.return_value = 99
        svc.user_repo.get_by_id.return_value = make_user(99, UserRole.ADMIN)
        with pytest.raises(ValidationError, match="reporting not available"):
            svc.lock_reported_discussion("tok", 1)

    def test_lock_reported_report_not_found(self):
        self.svc.report_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="report not found"):
            self.svc.lock_reported_discussion("tok", 1)


# ---------------------------------------------------------------------------
# Misc edge cases for _enrich_reply, list_discussions bookmarks default
# ---------------------------------------------------------------------------

class TestMiscBranches:
    def test_enrich_reply_with_engagement(self):
        svc = make_service()
        svc.user_repo.get_by_id.return_value = make_user(2)
        svc.engagement.get_reply_engagement.return_value = {"upvotes": 1}
        r = make_reply(rid=1, author_id=2)
        result = svc._enrich_reply(r, user_id=1)
        assert result["author"]["username"] == "u2"
        assert result["engagement"]["upvotes"] == 1

    def test_enrich_reply_no_author_no_engagement(self):
        svc = make_service(with_engagement=False)
        svc.user_repo.get_by_id.return_value = None
        result = svc._enrich_reply(make_reply(rid=1, author_id=2), user_id=1)
        assert "author" not in result
        assert "engagement" not in result

    def test_list_discussions_bookmarks_non_iterable(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.list_all.return_value = [make_discussion(did=1, author_id=5)]
        svc.discussion_repo.count.return_value = 1
        svc.user_repo.get_by_ids.return_value = {5: make_user(5)}
        # Non-iterable (e.g. None) → user_bookmarks = empty set
        svc.discussion_repo.get_user_bookmarks.return_value = None
        result = svc.list_discussions("tok")
        assert result["discussions"][0]["is_bookmarked"] is False
