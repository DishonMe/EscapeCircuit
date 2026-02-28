import pytest
from unittest.mock import Mock

from Backend.ServiceLayer.DiscussionService import DiscussionService, DISCUSSION_CREATE_XP
from Backend.DomainLayer.Discussion import Discussion
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole, ThreadCategory
from Backend.DomainLayer.Exceptions import ValidationError


def make_service():
    discussion_repo = Mock()
    reply_repo = Mock()
    user_repo = Mock()
    auth_service = Mock()
    xp_service = Mock()
    service = DiscussionService(
        discussion_repo=discussion_repo,
        reply_repo=reply_repo,
        user_repo=user_repo,
        auth_service=auth_service,
        xp_service=xp_service,
    )
    return service


def make_user(user_id=1, role=UserRole.SOLVER):
    return User(id=user_id, username=f"user{user_id}", role=role, xp=100)


def make_discussion(discussion_id=1, author_id=1, title="Test", body="Body", category=ThreadCategory.GENERAL):
    return Discussion(
        id=discussion_id, title=title, body=body, author_id=author_id, category=category
    )


class TestCreateDiscussion:
    def test_success(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        created = make_discussion()
        svc.discussion_repo.create.return_value = created
        svc.user_repo.get_by_id.return_value = make_user()
        svc.xp._apply_xp.return_value = DISCUSSION_CREATE_XP

        result = svc.create_discussion("token", {"title": "Test", "body": "Body"})
        assert result["title"] == "Test"
        svc.discussion_repo.create.assert_called_once()
        svc.xp._apply_xp.assert_called_once_with(1, DISCUSSION_CREATE_XP)

    def test_missing_title(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user()
        with pytest.raises(ValidationError, match="title"):
            svc.create_discussion("token", {"title": "", "body": "Body"})

    def test_missing_body(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user()
        with pytest.raises(ValidationError, match="body"):
            svc.create_discussion("token", {"title": "Title", "body": ""})

    def test_invalid_category(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user()
        with pytest.raises(ValidationError, match="category"):
            svc.create_discussion("token", {"title": "T", "body": "B", "category": "invalid"})

    def test_with_category_and_puzzle_id(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        created = make_discussion(title="Help!", body="Stuck", category=ThreadCategory.PUZZLE_HELP)
        svc.discussion_repo.create.return_value = created
        svc.user_repo.get_by_id.return_value = make_user()
        svc.xp._apply_xp.return_value = DISCUSSION_CREATE_XP

        result = svc.create_discussion("token", {
            "title": "Help!", "body": "Stuck", "category": "puzzle_help", "puzzle_id": 5
        })
        assert result["title"] == "Help!"


class TestViewDiscussion:
    def test_increments_view_count(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = make_discussion()

        result = svc.view_discussion("token", 1)
        svc.discussion_repo.increment_view_count.assert_called_once_with(1)
        assert result["view_count"] == 1

    def test_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.view_discussion("token", 999)


class TestGetDiscussion:
    def test_success(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = make_discussion()
        svc.user_repo.get_by_ids.return_value = {1: make_user()}
        svc.reply_repo.list_by_discussion.return_value = []

        result = svc.get_discussion("token", 1)
        assert result["title"] == "Test"
        assert result["author"]["username"] == "user1"
        # get_discussion should NOT increment view count
        svc.discussion_repo.increment_view_count.assert_not_called()

    def test_not_found(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.get_discussion("token", 999)


class TestListDiscussions:
    def test_success(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.list_all.return_value = [make_discussion(), make_discussion(discussion_id=2, title="T2")]
        svc.discussion_repo.count.return_value = 2
        svc.user_repo.get_by_ids.return_value = {1: make_user()}

        result = svc.list_discussions("token")
        assert len(result["discussions"]) == 2
        assert result["total"] == 2
        # Verify authors are enriched via batch fetch
        assert result["discussions"][0]["author"]["username"] == "user1"


class TestUpdateDiscussion:
    def test_owner_can_update(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = make_discussion(author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(1)
        updated = make_discussion(title="Updated")
        svc.discussion_repo.update.return_value = updated

        result = svc.update_discussion("token", 1, {"title": "Updated"})
        assert result["title"] == "Updated"

    def test_admin_can_update(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(2, role=UserRole.ADMIN)
        updated = make_discussion(title="Admin Updated")
        svc.discussion_repo.update.return_value = updated

        result = svc.update_discussion("token", 1, {"title": "Admin Updated"})
        assert result["title"] == "Admin Updated"

    def test_non_owner_cannot_update(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(2)

        with pytest.raises(ValidationError, match="not allowed"):
            svc.update_discussion("token", 1, {"title": "Nope"})


class TestDeleteDiscussion:
    def test_owner_can_delete(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = make_discussion(author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(1)

        result = svc.delete_discussion("token", 1)
        assert result["deleted"] is True

    def test_non_owner_cannot_delete(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(author_id=1)
        svc.user_repo.get_by_id.return_value = make_user(2)

        with pytest.raises(ValidationError, match="not allowed"):
            svc.delete_discussion("token", 1)


class TestPinDiscussion:
    def test_admin_can_pin(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1, role=UserRole.ADMIN)
        disc = make_discussion()
        svc.discussion_repo.get_by_id.return_value = disc
        svc.discussion_repo.conn = Mock()
        # After SQL toggle, get_by_id is called again to return updated state
        pinned = make_discussion()
        pinned.is_pinned = True
        svc.discussion_repo.get_by_id.side_effect = [disc, pinned]

        result = svc.pin_discussion("token", 1)
        assert result["is_pinned"] is True

    def test_non_admin_cannot_pin(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1)

        with pytest.raises(ValidationError, match="admin"):
            svc.pin_discussion("token", 1)


class TestLockDiscussion:
    def test_admin_can_lock(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1, role=UserRole.ADMIN)
        disc = make_discussion()
        svc.discussion_repo.get_by_id.return_value = disc
        svc.discussion_repo.conn = Mock()
        # After SQL toggle, get_by_id is called again to return updated state
        locked = make_discussion()
        locked.is_locked = True
        svc.discussion_repo.get_by_id.side_effect = [disc, locked]

        result = svc.lock_discussion("token", 1)
        assert result["is_locked"] is True

    def test_non_admin_cannot_lock(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1)

        with pytest.raises(ValidationError, match="admin"):
            svc.lock_discussion("token", 1)


# ---------------------------------------------------------------------------
# Full-service factory (includes engagement, report, notification repos)
# ---------------------------------------------------------------------------

def make_full_service():
    """Service with engagement, report, and notification repos."""
    discussion_repo = Mock()
    reply_repo = Mock()
    user_repo = Mock()
    auth_service = Mock()
    xp_service = Mock()
    engagement_repo = Mock()
    report_repo = Mock()
    notification_repo = Mock()
    service = DiscussionService(
        discussion_repo=discussion_repo,
        reply_repo=reply_repo,
        user_repo=user_repo,
        auth_service=auth_service,
        xp_service=xp_service,
        engagement_repo=engagement_repo,
        report_repo=report_repo,
        notification_repo=notification_repo,
    )
    return service


# ---------------------------------------------------------------------------
# Engagement tests
# ---------------------------------------------------------------------------

class TestVoteDiscussion:
    def test_upvote_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)
        svc.engagement.get_discussion_vote.return_value = None
        svc.engagement.set_discussion_vote.return_value = 1
        svc.discussion_repo.sync_upvotes_from_votes.return_value = {"upvotes": 1, "downvotes": 0}

        result = svc.vote_discussion("token", 1, 1)

        assert result["upvotes"] == 1
        assert result["user_vote"] == 1
        svc.xp._apply_xp.assert_called_once_with(1, 3)

    def test_downvote_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)
        svc.engagement.get_discussion_vote.return_value = None
        svc.engagement.set_discussion_vote.return_value = -1
        svc.discussion_repo.sync_upvotes_from_votes.return_value = {"upvotes": 0, "downvotes": 1}

        result = svc.vote_discussion("token", 1, -1)

        assert result["downvotes"] == 1
        svc.xp._apply_xp.assert_not_called()

    def test_toggle_removes_vote(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)
        svc.engagement.get_discussion_vote.return_value = 1
        svc.engagement.set_discussion_vote.return_value = None
        svc.discussion_repo.sync_upvotes_from_votes.return_value = {"upvotes": 0, "downvotes": 0}

        result = svc.vote_discussion("token", 1, 1)

        assert result["user_vote"] is None
        svc.xp._apply_xp.assert_not_called()


class TestReactToDiscussion:
    def test_add_reaction_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)
        svc.engagement.toggle_discussion_reaction.return_value = True
        svc.engagement.get_discussion_reactions.return_value = [{"type": "insightful", "count": 1}]
        svc.engagement.get_user_discussion_reactions.return_value = ["insightful"]

        result = svc.react_to_discussion("token", 1, "insightful")

        assert result["is_active"] is True
        svc.xp._apply_xp.assert_called_once_with(1, 1)

    def test_remove_reaction_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)
        svc.engagement.toggle_discussion_reaction.return_value = False
        svc.engagement.get_discussion_reactions.return_value = []
        svc.engagement.get_user_discussion_reactions.return_value = []

        result = svc.react_to_discussion("token", 1, "insightful")

        assert result["is_active"] is False
        svc.xp._apply_xp.assert_not_called()

    def test_invalid_reaction_type(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)

        with pytest.raises(ValidationError, match="invalid reaction"):
            svc.react_to_discussion("token", 1, "invalid_type")


class TestFollowDiscussion:
    def test_follow_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)
        svc.engagement.toggle_follow.return_value = True

        result = svc.follow_discussion("token", 1)

        assert result["is_following"] is True

    def test_unfollow_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)
        svc.engagement.toggle_follow.return_value = False

        result = svc.follow_discussion("token", 1)

        assert result["is_following"] is False


class TestBookmarkDiscussion:
    def test_bookmark_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)
        svc.engagement.toggle_bookmark.return_value = True

        result = svc.bookmark_discussion("token", 1)

        assert result["is_bookmarked"] is True

    def test_unbookmark_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)
        svc.engagement.toggle_bookmark.return_value = False

        result = svc.bookmark_discussion("token", 1)

        assert result["is_bookmarked"] is False


# ---------------------------------------------------------------------------
# Report tests
# ---------------------------------------------------------------------------

class TestReportDiscussion:
    def test_report_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)
        svc.report_repo.has_reported.return_value = False
        svc.report_repo.create.return_value = {"id": 1, "reporter_id": 2, "target_type": "discussion", "target_id": 1, "reason": "spam"}

        result = svc.report_discussion("token", 1, "spam")

        svc.report_repo.create.assert_called_once()

    def test_duplicate_report_rejected(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=1)
        svc.report_repo.has_reported.return_value = True

        with pytest.raises(ValidationError, match="already reported"):
            svc.report_discussion("token", 1, "spam")


# ---------------------------------------------------------------------------
# Admin moderation tests
# ---------------------------------------------------------------------------

class TestAdminModeration:
    def test_warn_author_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 10
        svc.user_repo.get_by_id.return_value = make_user(user_id=10, role=UserRole.ADMIN)
        svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "discussion", "target_id": 1, "reason": "spam",
        }
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=5)

        result = svc.warn_user_for_report("token", 1)

        svc.notification_repo.create.assert_called_once()
        call_kwargs = svc.notification_repo.create.call_args[1]
        assert call_kwargs["user_id"] == 5
        assert call_kwargs["notif_type"] == "warning"
        svc.report_repo.update_status.assert_called_once_with(1, "reviewed")

    def test_ban_author_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 10
        svc.user_repo.get_by_id.return_value = make_user(user_id=10, role=UserRole.ADMIN)
        svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "discussion", "target_id": 1, "reason": "spam",
        }
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=5)

        result = svc.ban_user_for_report("token", 1)

        svc.user_repo.ban_from_discussions.assert_called_once_with(5)
        svc.notification_repo.create.assert_called_once()
        call_kwargs = svc.notification_repo.create.call_args[1]
        assert call_kwargs["notif_type"] == "ban"
        svc.report_repo.update_status.assert_called_once_with(1, "reviewed")

    def test_delete_content_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 10
        svc.user_repo.get_by_id.return_value = make_user(user_id=10, role=UserRole.ADMIN)
        svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "discussion", "target_id": 1, "reason": "spam",
        }
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=5)

        result = svc.delete_reported_content("token", 1)

        svc.discussion_repo.delete.assert_called_once_with(1)
        svc.report_repo.update_status.assert_called_once_with(1, "reviewed")

    def test_lock_discussion_from_report_success(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 10
        svc.user_repo.get_by_id.return_value = make_user(user_id=10, role=UserRole.ADMIN)
        svc.report_repo.get_by_id.return_value = {
            "id": 1, "target_type": "discussion", "target_id": 1, "reason": "spam",
        }
        svc.discussion_repo.get_by_id.return_value = make_discussion(discussion_id=1, author_id=5)

        result = svc.lock_reported_discussion("token", 1)

        svc.discussion_repo.update.assert_called_once_with(1, {"is_locked": True})
        svc.report_repo.update_status.assert_called_once_with(1, "reviewed")

    def test_non_admin_cannot_moderate(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.user_repo.get_by_id.return_value = make_user(user_id=2, role=UserRole.SOLVER)

        with pytest.raises(ValidationError, match="admin"):
            svc.warn_user_for_report("token", 1)


# ---------------------------------------------------------------------------
# Ban enforcement tests
# ---------------------------------------------------------------------------

class TestBanEnforcement:
    def test_banned_user_cannot_create_discussion(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        user = make_user(user_id=1, role=UserRole.SOLVER)
        user.is_discussion_banned = True
        svc.user_repo.get_by_id.return_value = user

        with pytest.raises(ValidationError, match="banned"):
            svc.create_discussion("token", {"title": "Test", "body": "Body"})
