"""Tests for NotificationService"""
import pytest
from unittest.mock import Mock
from Backend.ServiceLayer.NotificationService import NotificationService


class TestNotificationServiceInit:
    def setup_method(self):
        self.mock_notification_repo = Mock()
        self.mock_auth = Mock()
        
        self.service = NotificationService(
            self.mock_notification_repo,
            self.mock_auth,
        )

    def test_initialization(self):
        assert self.service.repo == self.mock_notification_repo
        assert self.service.auth == self.mock_auth


class TestNotificationServiceNotifyCreatorSolve:
    def setup_method(self):
        self.mock_notification_repo = Mock()
        self.mock_auth = Mock()
        
        self.service = NotificationService(
            self.mock_notification_repo,
            self.mock_auth,
        )

    def test_notify_creator_solve(self):
        creator_id = 1
        solver_username = "john_solver"
        puzzle_name = "Binary Adder"
        xp_amount = 50
        
        self.service.notify_creator_solve(
            creator_id,
            solver_username,
            puzzle_name,
            xp_amount
        )
        
        self.mock_notification_repo.create.assert_called_once()

    def test_notify_creator_solve_message_contains_info(self):
        creator_id = 1
        solver_username = "alice"
        puzzle_name = "Half Adder"
        xp_amount = 25
        
        self.service.notify_creator_solve(creator_id, solver_username, puzzle_name, xp_amount)
        
        call_args = self.mock_notification_repo.create.call_args[1]
        message = call_args["message"]
        
        assert solver_username in message
        assert puzzle_name in message
        assert str(xp_amount) in message


class TestNotificationServiceNotifyCreatorRating:
    def setup_method(self):
        self.mock_notification_repo = Mock()
        self.mock_auth = Mock()
        
        self.service = NotificationService(
            self.mock_notification_repo,
            self.mock_auth,
        )

    def test_notify_creator_rating(self):
        creator_id = 2
        rater_username = "bob_rater"
        puzzle_name = "Sequential Adder"
        xp_amount = 10
        
        self.service.notify_creator_rating(
            creator_id,
            rater_username,
            puzzle_name,
            xp_amount
        )
        
        self.mock_notification_repo.create.assert_called_once()

    def test_notify_creator_rating_message_contains_info(self):
        creator_id = 2
        rater_username = "charlie"
        puzzle_name = "Palindrome Checker"
        xp_amount = 5
        
        self.service.notify_creator_rating(creator_id, rater_username, puzzle_name, xp_amount)
        
        call_args = self.mock_notification_repo.create.call_args[1]
        message = call_args["message"]
        
        assert rater_username in message
        assert puzzle_name in message
        assert str(xp_amount) in message


class TestNotificationServiceGetUnread:
    def setup_method(self):
        self.mock_notification_repo = Mock()
        self.mock_auth = Mock()
        
        self.service = NotificationService(
            self.mock_notification_repo,
            self.mock_auth,
        )

    def test_get_unread_calls_repo(self):
        user_id = 1
        token = "valid_token"
        
        mock_notifications = [{"id": 1, "type": "solve"}, {"id": 2, "type": "rating"}]
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_notification_repo.get_unread.return_value = mock_notifications
        
        result = self.service.get_unread(token)
        
        assert result == mock_notifications
        self.mock_auth.require_user_id.assert_called_once_with(token)

    def test_get_unread_with_filters(self):
        user_id = 1
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_notification_repo.get_unread.return_value = []
        
        self.service.get_unread(token, notif_type="solve", puzzle_name="Binary")
        
        call_kwargs = self.mock_notification_repo.get_unread.call_args[1]
        assert call_kwargs["notif_type"] == "solve"
        assert call_kwargs["puzzle_name"] == "Binary"


class TestNotificationServiceGetAll:
    def setup_method(self):
        self.mock_notification_repo = Mock()
        self.mock_auth = Mock()
        
        self.service = NotificationService(
            self.mock_notification_repo,
            self.mock_auth,
        )

    def test_get_all_calls_repo(self):
        user_id = 1
        token = "valid_token"
        
        mock_notifications = [{"id": 1}, {"id": 2}]
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_notification_repo.get_all.return_value = mock_notifications
        
        result = self.service.get_all(token)
        
        assert result == mock_notifications


class TestNotificationServiceMarkAllRead:
    def setup_method(self):
        self.mock_notification_repo = Mock()
        self.mock_auth = Mock()
        
        self.service = NotificationService(
            self.mock_notification_repo,
            self.mock_auth,
        )

    def test_mark_all_read_success(self):
        user_id = 1
        token = "valid_token"
        count = 5
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_notification_repo.mark_all_read.return_value = count
        
        result = self.service.mark_all_read(token)
        
        assert result["marked_read"] == count
        self.mock_notification_repo.mark_all_read.assert_called_once_with(user_id)


