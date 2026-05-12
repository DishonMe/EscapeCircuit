"""Tests for NotificationService"""
import sqlite3
import pytest
from unittest.mock import Mock
from Backend.ServiceLayer.NotificationService import NotificationService
from Backend.PersistantLayer.NotificationRepo import NotificationRepo
from Backend.PersistantLayer._db import transaction


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

    def test_notify_creator_solve_default_commits(self):
        self.service.notify_creator_solve(1, "u", "p", 5)
        assert self.mock_notification_repo.create.call_args[1]["commit"] is True

    def test_notify_creator_solve_commit_false_propagates(self):
        self.service.notify_creator_solve(1, "u", "p", 5, commit=False)
        assert self.mock_notification_repo.create.call_args[1]["commit"] is False


class TestNotifyCreatorSolveInsideTransaction:
    """Regression test for the production 500 on first-time solve of another
    user's puzzle. Reproduces the original bug: notify_creator_solve() called
    inside an active BEGIN IMMEDIATE used to issue its own commit, which left
    the outer `with transaction(...)` block's COMMIT with no active txn ->
    sqlite3.OperationalError -> 500. The fix routes commit=False through
    NotificationService so the outer transaction stays in charge.
    """

    def setup_method(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.isolation_level = None  # match production: manual BEGIN/COMMIT
        self.repo = NotificationRepo(self.conn)
        self.service = NotificationService(self.repo, Mock())

    def test_notify_inside_transaction_does_not_break_outer_commit(self):
        # This mirrors SolvingService.validate_solution's transaction:
        # the inner notify must NOT commit, so the outer COMMIT succeeds.
        with transaction(self.conn):
            self.service.notify_creator_solve(
                creator_user_id=1,
                solver_username="solver",
                puzzle_name="Binary Adder",
                xp_amount=50,
                commit=False,
            )
        # Outer commit succeeded; row is persisted.
        rows = self.conn.execute(
            "SELECT user_id, type, message FROM creator_notifications"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["user_id"] == 1
        assert rows[0]["type"] == "solve"

    def test_notify_inside_transaction_with_default_commit_raises(self):
        # Without the fix, this is what was happening in prod on first solve:
        # the inner commit short-circuits the outer BEGIN IMMEDIATE, and the
        # context manager's COMMIT then errors. Locked in as a regression
        # guard so we don't regress to commit=True by default from this site.
        with pytest.raises(sqlite3.OperationalError):
            with transaction(self.conn):
                self.service.notify_creator_solve(
                    creator_user_id=1,
                    solver_username="solver",
                    puzzle_name="Binary Adder",
                    xp_amount=50,
                    # commit defaults to True — reproduces the original bug
                )


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


