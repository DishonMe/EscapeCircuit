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
        with pytest.raises(ValidationError, match="title"):
            svc.create_discussion("token", {"title": "", "body": "Body"})

    def test_missing_body(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        with pytest.raises(ValidationError, match="body"):
            svc.create_discussion("token", {"title": "Title", "body": ""})

    def test_invalid_category(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
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


class TestGetDiscussion:
    def test_success(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.discussion_repo.get_by_id.return_value = make_discussion()
        svc.user_repo.get_by_id.return_value = make_user()
        svc.reply_repo.list_top_level.return_value = []

        result = svc.get_discussion("token", 1)
        assert result["title"] == "Test"
        svc.discussion_repo.increment_view_count.assert_called_once_with(1)

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
        svc.user_repo.get_by_id.return_value = make_user()

        result = svc.list_discussions("token")
        assert len(result["discussions"]) == 2
        assert result["total"] == 2


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
        svc.discussion_repo.get_by_id.return_value = make_discussion()
        pinned = make_discussion()
        pinned.is_pinned = True
        svc.discussion_repo.update.return_value = pinned

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
        svc.discussion_repo.get_by_id.return_value = make_discussion()
        locked = make_discussion()
        locked.is_locked = True
        svc.discussion_repo.update.return_value = locked

        result = svc.lock_discussion("token", 1)
        assert result["is_locked"] is True

    def test_non_admin_cannot_lock(self):
        svc = make_service()
        svc.auth.require_user_id.return_value = 1
        svc.user_repo.get_by_id.return_value = make_user(1)

        with pytest.raises(ValidationError, match="admin"):
            svc.lock_discussion("token", 1)
