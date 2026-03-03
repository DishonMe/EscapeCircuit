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


# ============ Additional branch coverage tests ============

class TestDiscussionServiceListVariations:
    """Test various list_discussions filters"""
    
    def test_list_discussions_by_category(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.list_all.return_value = [
            make_discussion(category=ThreadCategory.BUG_REPORT)
        ]
        svc.discussion_repo.count.return_value = 1
        svc.user_repo.get_by_ids.return_value = {1: make_user()}
        
        result = svc.list_discussions("token", category="bug_report")
        assert result["total"] == 1

    def test_list_discussions_by_puzzle(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.list_all.return_value = [
            make_discussion()
        ]
        svc.discussion_repo.count.return_value = 1
        svc.user_repo.get_by_ids.return_value = {1: make_user()}
        
        result = svc.list_discussions("token", puzzle_id=5)
        assert result["total"] == 1

    def test_list_discussions_sort_trending(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.list_all.return_value = []
        svc.discussion_repo.count.return_value = 0
        svc.user_repo.get_by_ids.return_value = {}
        
        result = svc.list_discussions("token", sort_by="trending")
        assert result["discussions"] == []

    def test_list_discussions_with_search(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.list_all.return_value = []
        svc.discussion_repo.count.return_value = 0
        svc.user_repo.get_by_ids.return_value = {}
        
        result = svc.list_discussions("token", search="circuit")
        assert "discussions" in result


class TestDiscussionServiceModerationAdminActions:
    """Test admin moderation functionality"""
    
    def test_admin_can_pin_discussion(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 10
        svc.user_repo.get_by_id.side_effect = [make_user(10, role=UserRole.ADMIN), make_user(1)]
        disc = make_discussion()
        svc.discussion_repo.get_by_id.side_effect = [disc, disc]
        
        result = svc.pin_discussion("token", 1)
        assert result["title"] == "Test"
        svc.discussion_repo.get_by_id.assert_called()

    def test_admin_can_lock_discussion(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 10
        svc.user_repo.get_by_id.side_effect = [make_user(10, role=UserRole.ADMIN), make_user(1)]
        disc = make_discussion()
        svc.discussion_repo.get_by_id.side_effect = [disc, disc]
        
        result = svc.lock_discussion("token", 1)
        assert result["title"] == "Test"

    def test_non_admin_cannot_pin(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.user_repo.get_by_id.return_value = make_user(2)
        
        with pytest.raises(ValidationError, match="admin"):
            svc.pin_discussion("token", 1)

    def test_non_admin_cannot_lock(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.user_repo.get_by_id.return_value = make_user(2)
        
        with pytest.raises(ValidationError, match="admin"):
            svc.lock_discussion("token", 1)


class TestDiscussionServiceEngagementVariations:
    """Test engagement operations"""
    
    def test_follow_then_unfollow(self):
        """Test toggling follow state"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion()
        svc.engagement.toggle_follow.side_effect = [True, False]
        
        follow_result = svc.follow_discussion("token", 1)
        assert follow_result["is_following"] is True
        
        unfollow_result = svc.follow_discussion("token", 1)
        assert unfollow_result["is_following"] is False

    def test_bookmark_toggle(self):
        """Test bookmark toggle"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion()
        svc.engagement.toggle_bookmark.return_value = True
        
        result = svc.bookmark_discussion("token", 1)
        assert result["is_bookmarked"] is True

    def test_react_multiple_types(self):
        """Test multiple reaction types"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(author_id=1)
        svc.engagement.toggle_discussion_reaction.return_value = True
        svc.engagement.get_discussion_reactions.return_value = [{"type": "insightful"}]
        svc.engagement.get_user_discussion_reactions.return_value = ["insightful"]
        
        result = svc.react_to_discussion("token", 1, "insightful")
        assert result["is_active"] is True


class TestDiscussionServiceReporting:
    """Test reporting functionality"""
    
    def test_report_discussion_new(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 2
        svc.discussion_repo.get_by_id.return_value = make_discussion(author_id=1)
        svc.report_repo.has_reported.return_value = False
        svc.report_repo.create.return_value = {"id": 1}
        
        result = svc.report_discussion("token", 1, "spam")
        assert result["id"] == 1

    def test_list_reports_pending(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 10
        svc.user_repo.get_by_id.return_value = make_user(10, role=UserRole.ADMIN)
        svc.report_repo.list_all.return_value = [
            {"id": 1, "status": "pending", "target_type": "discussion", "target_id": 1, "reporter_id": 5}
        ]
        svc.report_repo.count.return_value = 1
        svc.user_repo.get_by_ids.return_value = {5: make_user(5)}
        svc.discussion_repo.get_by_ids.return_value = {1: make_discussion()}
        
        result = svc.list_reports("token", status="pending")
        assert "reports" in result

    def test_update_report_status(self):
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 10
        svc.user_repo.get_by_id.return_value = make_user(10, role=UserRole.ADMIN)
        svc.report_repo.update_status.return_value = True
        
        result = svc.update_report_status("token", 1, "reviewed")
        assert result is not None


class TestDiscussionDeletion:
    """Test discussion deletion and permissions"""
    
    def test_delete_discussion_not_owner(self):
        """Test delete_discussion when user is not the owner"""
        service = make_full_service()
        service.auth.require_user_id.return_value = 2
        
        discussion = Mock()
        discussion.author_id = 1
        
        service.discussion_repo.get_by_id.return_value = discussion
        service.user_repo.get_by_id.return_value = Mock(role="user")
        
        with pytest.raises(ValidationError, match="not allowed"):
            service.delete_discussion("token", 1)
    
    def test_delete_discussion_owner_succeeds(self):
        """Test delete_discussion succeeds when user is owner"""
        service = make_full_service()
        service.auth.require_user_id.return_value = 1
        
        discussion = Mock()
        discussion.author_id = 1
        discussion.id = 1
        
        service.discussion_repo.get_by_id.return_value = discussion
        service.discussion_repo.delete.return_value = None
        service.user_repo.get_by_id.return_value = Mock(role="user")
        
        result = service.delete_discussion("token", 1)
        assert result["deleted"] == True
        service.discussion_repo.delete.assert_called_once()


class TestDiscussionUpdateCoveragePush:
    """Test discussion update"""
    
    def test_update_discussion_not_owner(self):
        """Test update_discussion when user is not the owner"""
        service = make_full_service()
        service.auth.require_user_id.return_value = 2
        
        discussion = Mock()
        discussion.author_id = 1
        
        service.discussion_repo.get_by_id.return_value = discussion
        service.user_repo.get_by_id.return_value = Mock(role="user")
        
        with pytest.raises(ValidationError, match="not allowed"):
            service.update_discussion("token", 1, {"content": "new"})


class TestAdminOnlyOperations:
    """Test admin-only operations"""
    
    def test_lock_discussion_admin_only(self):
        """Test lock_discussion requires admin"""
        service = make_full_service()
        service.auth.require_user_id.return_value = 1
        service.user_repo.get_by_id.return_value = Mock(role="user")
        
        with pytest.raises(ValidationError, match="admin"):
            service.lock_discussion("token", 1)
    
    def test_pin_discussion_admin_only(self):
        """Test pin_discussion requires admin"""
        service = make_full_service()
        service.auth.require_user_id.return_value = 1
        service.user_repo.get_by_id.return_value = Mock(role="user")
        
        with pytest.raises(ValidationError, match="admin"):
            service.pin_discussion("token", 1)


class TestDiscussionListingPagination:
    """Test discussion listing and filtering"""
    
    def test_get_discussions_pagination(self):
        """Test list_discussions with pagination parameters"""
        service = make_full_service()
        
        # Mock discussion_repo methods to return empty results
        service.discussion_repo.list_all.return_value = []
        service.discussion_repo.count.return_value = 0
        service.auth.require_user_id.return_value = 1
        
        result = service.list_discussions("token", puzzle_id=1, limit=10, offset=0)
        
        assert isinstance(result, dict)
        assert "discussions" in result
        assert result["total"] == 0
        assert result["discussions"] == []


class TestReplyListingPagination:
    """Test reply viewing"""
    
    def test_view_discussion_with_replies(self):
        """Test view_discussion returns discussion with replies"""
        service = make_full_service()
        discussion = Mock()
        discussion.id = 1
        discussion.view_count = 5
        
        service.discussion_repo.get_by_id.return_value = discussion
        service.reply_repo.list_for_discussion.return_value = []
        service.auth.require_user_id.return_value = 1
        service.user_repo.get_by_id.return_value = Mock(id=1)
        
        result = service.view_discussion("token", 1)
        
        assert isinstance(result, dict)


class TestCreateDiscussionBannedUserDeepPush:
    """Test banned user cannot create discussion"""

    def test_banned_user_cannot_create(self):
        """User banned from discussions cannot create"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        user = Mock()
        user.is_discussion_banned = True
        svc.user_repo.get_by_id.return_value = user

        with pytest.raises(ValidationError, match="banned"):
            svc.create_discussion("token", {"title": "T", "body": "B"})


class TestCreateDiscussionNoAuthorDeepPush:
    """Test create discussion when author lookup fails"""

    def test_author_not_found_enrichment(self):
        """Create discussion when author user lookup returns None"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = None  # Author not found
        created = Mock()
        created.id = "1"
        created.to_dict.return_value = {"id": "1"}
        svc.discussion_repo.create.return_value = created

        result = svc.create_discussion("token", {"title": "T", "body": "B"})
        assert result["id"] == "1"
        assert "author" not in result  # No author enrichment


class TestViewDiscussionNotFoundDeepPush:
    """Test view discussion error cases"""

    def test_view_discussion_not_found(self):
        """View non-existent discussion"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="not found"):
            svc.view_discussion("token", 999)


class TestVoteDiscussionXPAwardDeepPush:
    """Test vote XP award logic"""

    def test_upvote_awards_xp_once_per_user(self):
        """XP awarded only if user hasn't upvoted before"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.engagement.get_discussion_vote.return_value = None  # First vote
        svc.engagement.set_discussion_vote.return_value = 1
        svc.engagement.try_award_engagement_xp.return_value = True

        disc = Mock()
        disc.author_id = 99  # Different author
        svc.discussion_repo.get_by_id.return_value = disc
        svc.discussion_repo.sync_upvotes_from_votes.return_value = {"upvotes": 1, "downvotes": 0}

        result = svc.vote_discussion("token", 1, 1)
        assert result["user_vote"] == 1
        svc.xp._apply_xp.assert_called_once()

    def test_upvote_no_xp_if_author(self):
        """XP not awarded if user is discussion author"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.engagement.get_discussion_vote.return_value = None
        svc.engagement.set_discussion_vote.return_value = 1

        disc = Mock()
        disc.author_id = 1  # User is author
        svc.discussion_repo.get_by_id.return_value = disc
        svc.discussion_repo.sync_upvotes_from_votes.return_value = {"upvotes": 1, "downvotes": 0}

        result = svc.vote_discussion("token", 1, 1)
        assert result["user_vote"] == 1
        svc.xp._apply_xp.assert_not_called()  # No XP for author

    def test_downvote_no_xp(self):
        """XP not awarded for downvotes"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.engagement.get_discussion_vote.return_value = None
        svc.engagement.set_discussion_vote.return_value = -1

        disc = Mock()
        disc.author_id = 99
        svc.discussion_repo.get_by_id.return_value = disc
        svc.discussion_repo.sync_upvotes_from_votes.return_value = {"upvotes": 0, "downvotes": 1}

        result = svc.vote_discussion("token", 1, -1)
        svc.xp._apply_xp.assert_not_called()  # No XP for downvote

    def test_vote_invalid_value(self):
        """Invalid vote value raises error"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1

        with pytest.raises(ValidationError, match="value must be 1 or -1"):
            svc.vote_discussion("token", 1, 0)


class TestReactToDiscussionXPAwardDeepPush:
    """Test reaction XP award logic"""

    def test_reaction_awards_xp_once(self):
        """XP awarded for adding reaction"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.engagement.toggle_discussion_reaction.return_value = True
        svc.engagement.try_award_engagement_xp.return_value = True

        disc = Mock()
        disc.author_id = 99
        svc.discussion_repo.get_by_id.return_value = disc
        svc.engagement.get_discussion_reactions.return_value = [{"type": "insightful", "count": 1}]
        svc.engagement.get_user_discussion_reactions.return_value = ["insightful"]

        result = svc.react_to_discussion("token", 1, "insightful")
        assert result["is_active"] is True
        svc.xp._apply_xp.assert_called_once()

    def test_reaction_no_xp_if_author(self):
        """XP not awarded if reacting to own discussion"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.engagement.toggle_discussion_reaction.return_value = True

        disc = Mock()
        disc.author_id = 1  # User is author
        svc.discussion_repo.get_by_id.return_value = disc
        svc.engagement.get_discussion_reactions.return_value = []
        svc.engagement.get_user_discussion_reactions.return_value = []

        result = svc.react_to_discussion("token", 1, "insightful")
        svc.xp._apply_xp.assert_not_called()

    def test_reaction_remove_no_xp(self):
        """XP not awarded when removing reaction"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.engagement.toggle_discussion_reaction.return_value = False  # Removed

        disc = Mock()
        disc.author_id = 99
        svc.discussion_repo.get_by_id.return_value = disc
        svc.engagement.get_discussion_reactions.return_value = []
        svc.engagement.get_user_discussion_reactions.return_value = []

        result = svc.react_to_discussion("token", 1, "insightful")
        svc.xp._apply_xp.assert_not_called()


class TestReportDiscussionDuplicateDeepPush:
    """Test report validation"""

    def test_duplicate_report_raises_error(self):
        """Duplicate report detected at creation"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1

        disc = Mock()
        svc.discussion_repo.get_by_id.return_value = disc
        svc.report_repo.has_reported.return_value = True

        with pytest.raises(ValidationError, match="already reported"):
            svc.report_discussion("token", 1, "spam", "details")

    def test_duplicate_report_integrity_error(self):
        """Duplicate report detected at DB level"""
        import sqlite3
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1

        disc = Mock()
        svc.discussion_repo.get_by_id.return_value = disc
        svc.report_repo.has_reported.return_value = False
        svc.report_repo.create.side_effect = sqlite3.IntegrityError("UNIQUE constraint")

        with pytest.raises(ValidationError, match="already reported"):
            svc.report_discussion("token", 1, "spam", "details")


class TestReportReplyDeepPush:
    """Test reply reporting"""

    def test_report_reply_success(self):
        """Report reply successfully"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1

        reply = Mock()
        svc.reply_repo.get_by_id.return_value = reply
        svc.report_repo.has_reported.return_value = False
        svc.report_repo.create.return_value = {"id": 1, "target_id": 1, "target_type": "reply"}

        result = svc.report_reply("token", 1, "spam", "inappropriate")
        assert result["target_type"] == "reply"

    def test_report_reply_not_found(self):
        """Report non-existent reply"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        svc.reply_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="reply not found"):
            svc.report_reply("token", 999, "spam")


class TestListReportsDeepPush:
    """Test list reports functionality"""

    def test_list_reports_admin_only(self):
        """Only admins can list reports"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        user = Mock()
        user.role = UserRole.SOLVER
        svc.user_repo.get_by_id.return_value = user

        with pytest.raises(ValidationError, match="admin only"):
            svc.list_reports("token")

    def test_list_reports_with_batch_enrichment(self):
        """List reports with batch user/content enrichment"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        admin_user = Mock()
        admin_user.role = UserRole.ADMIN
        svc.user_repo.get_by_id.return_value = admin_user

        reports = [
            {
                "id": 1,
                "reporter_id": 2,
                "target_type": "discussion",
                "target_id": 10,
                "reason": "spam",
            },
            {"id": 2, "reporter_id": 3, "target_type": "reply", "target_id": 20, "reason": "spam"},
        ]
        svc.report_repo.list_all.return_value = reports
        svc.report_repo.count.return_value = 2

        disc = Mock()
        disc.author_id = 5
        reply = Mock()
        reply.discussion_id = 1
        reply.author_id = 6
        svc.discussion_repo.get_by_ids.return_value = {10: disc}
        svc.reply_repo.get_by_ids.return_value = {20: reply}

        users = {
            2: Mock(username="user2"),
            3: Mock(username="user3"),
            5: Mock(username="user5"),
            6: Mock(username="user6"),
        }
        svc.user_repo.get_by_ids.return_value = users

        result = svc.list_reports("token", status="pending")
        assert result["total"] == 2


class TestUpdateReportStatusDeepPush:
    """Test report status updates"""

    def test_update_report_status_non_admin(self):
        """Non-admin cannot update report status"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        user = Mock()
        user.role = UserRole.SOLVER
        svc.user_repo.get_by_id.return_value = user

        with pytest.raises(ValidationError, match="admin only"):
            svc.update_report_status("token", 1, "reviewed")

    def test_update_report_status_invalid(self):
        """Invalid status rejected"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        admin_user = Mock()
        admin_user.role = UserRole.ADMIN
        svc.user_repo.get_by_id.return_value = admin_user

        with pytest.raises(ValidationError, match="invalid status"):
            svc.update_report_status("token", 1, "invalid")


class TestWarnUserForReportDeepPush:
    """Test warning action from report"""

    def test_warn_user_success(self):
        """Warn user successfully with notification"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        admin_user = Mock()
        admin_user.role = UserRole.ADMIN
        svc.user_repo.get_by_id.return_value = admin_user

        report = {"id": 1, "target_type": "discussion", "target_id": 5, "reason": "spam"}
        svc.report_repo.get_by_id.return_value = report
        disc = Mock()
        disc.author_id = 10
        svc.discussion_repo.get_by_id.return_value = disc
        svc.report_repo.update_status.return_value = {"status": "reviewed"}

        result = svc.warn_user_for_report("token", 1)
        assert result["action"] == "warned"
        assert result["warned_user_id"] == 10
        svc.notification_repo.create.assert_called_once()

    def test_warn_user_no_notification_repo(self):
        """Warn user without notification repo"""
        svc = make_full_service()
        svc.notification_repo = None
        svc.auth.require_user_id.return_value = 1
        admin_user = Mock()
        admin_user.role = UserRole.ADMIN
        svc.user_repo.get_by_id.return_value = admin_user

        report = {"id": 1, "target_type": "discussion", "target_id": 5, "reason": "spam"}
        svc.report_repo.get_by_id.return_value = report
        disc = Mock()
        disc.author_id = 10
        svc.discussion_repo.get_by_id.return_value = disc
        svc.report_repo.update_status.return_value = {"status": "reviewed"}

        result = svc.warn_user_for_report("token", 1)
        assert result["action"] == "warned"


class TestBanUserForReportDeepPush:
    """Test banning user from report"""

    def test_ban_user_success(self):
        """Ban user successfully with notification"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        admin_user = Mock()
        admin_user.role = UserRole.ADMIN
        svc.user_repo.get_by_id.return_value = admin_user

        report = {"id": 1, "target_type": "reply", "target_id": 5, "reason": "harassment"}
        svc.report_repo.get_by_id.return_value = report
        reply = Mock()
        reply.author_id = 10
        svc.reply_repo.get_by_id.return_value = reply
        svc.report_repo.update_status.return_value = {"status": "reviewed"}

        result = svc.ban_user_for_report("token", 1)
        assert result["action"] == "banned"
        assert result["banned_user_id"] == 10
        svc.user_repo.ban_from_discussions.assert_called_once_with(10)
        svc.notification_repo.create.assert_called_once()


class TestDeleteReportedContentDeepPush:
    """Test deleting reported content"""

    def test_delete_discussion_from_report(self):
        """Delete reported discussion"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        admin_user = Mock()
        admin_user.role = UserRole.ADMIN
        svc.user_repo.get_by_id.return_value = admin_user

        report = {"id": 1, "target_type": "discussion", "target_id": 5}
        svc.report_repo.get_by_id.return_value = report
        disc = Mock()
        disc.author_id = 10
        svc.discussion_repo.get_by_id.return_value = disc
        svc.report_repo.update_status.return_value = {"status": "reviewed"}

        result = svc.delete_reported_content("token", 1)
        assert result["action"] == "deleted"
        assert result["target_type"] == "discussion"
        svc.discussion_repo.delete.assert_called_once_with(5)

    def test_delete_reply_from_report(self):
        """Delete reported reply with reply count decrement"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        admin_user = Mock()
        admin_user.role = UserRole.ADMIN
        svc.user_repo.get_by_id.return_value = admin_user

        report = {"id": 1, "target_type": "reply", "target_id": 20}
        svc.report_repo.get_by_id.return_value = report
        reply = Mock()
        reply.reply_id = 20
        reply.discussion_id = 5
        svc.reply_repo.get_by_id.return_value = reply
        svc.reply_repo.delete.return_value = True  # Delete succeeded
        svc.report_repo.update_status.return_value = {"status": "reviewed"}

        result = svc.delete_reported_content("token", 1)
        assert result["action"] == "deleted"
        svc.reply_repo.delete.assert_called_once_with(20)
        svc.discussion_repo.increment_reply_count.assert_called_once_with(5, -1)

    def test_delete_reply_no_decrement_if_failed(self):
        """Don't decrement reply count if delete fails"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        admin_user = Mock()
        admin_user.role = UserRole.ADMIN
        svc.user_repo.get_by_id.return_value = admin_user

        report = {"id": 1, "target_type": "reply", "target_id": 20}
        svc.report_repo.get_by_id.return_value = report
        reply = Mock()
        reply.reply_id = 20
        reply.discussion_id = 5
        svc.reply_repo.get_by_id.return_value = reply
        svc.reply_repo.delete.return_value = False  # Delete failed
        svc.report_repo.update_status.return_value = {"status": "reviewed"}

        result = svc.delete_reported_content("token", 1)
        svc.discussion_repo.increment_reply_count.assert_not_called()


class TestLockReportedDiscussionDeepPush:
    """Test locking discussion from report"""

    def test_lock_reports_non_admin(self):
        """Non-admin cannot lock from report"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        user = Mock()
        user.role = UserRole.SOLVER
        svc.user_repo.get_by_id.return_value = user

        with pytest.raises(ValidationError, match="admin only"):
            svc.lock_reported_discussion("token", 1)

    def test_lock_discussion_from_report_success(self):
        """Lock reported discussion"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        admin_user = Mock()
        admin_user.role = UserRole.ADMIN
        svc.user_repo.get_by_id.return_value = admin_user

        report = {"id": 1, "target_type": "discussion", "target_id": 5}
        svc.report_repo.get_by_id.return_value = report
        disc = Mock()
        disc.author_id = 10
        svc.discussion_repo.get_by_id.return_value = disc
        svc.discussion_repo.update.return_value = disc
        svc.report_repo.update_status.return_value = {"status": "reviewed"}

        result = svc.lock_reported_discussion("token", 1)
        assert result["action"] == "locked"
        svc.discussion_repo.update.assert_called_once_with(5, {"is_locked": True})

    def test_lock_from_report_reply_not_allowed(self):
        """Cannot lock reply from report (only discussions)"""
        svc = make_full_service()
        svc.auth.require_user_id.return_value = 1
        admin_user = Mock()
        admin_user.role = UserRole.ADMIN
        svc.user_repo.get_by_id.return_value = admin_user

        report = {"id": 1, "target_type": "reply", "target_id": 5}
        svc.report_repo.get_by_id.return_value = report

        with pytest.raises(ValidationError, match="can only lock discussions"):
            svc.lock_reported_discussion("token", 1)

