from typing import List

from Backend.PersistantLayer.NotificationRepo import NotificationRepo
from Backend.ServiceLayer.AuthService import AuthService


class NotificationService:
    """Manages creator notifications (XP earned from other users)."""

    def __init__(self, notification_repo: NotificationRepo, auth_service: AuthService):
        self.repo = notification_repo
        self.auth = auth_service

    # --- Called by other services when creator earns XP ---

    def notify_creator_solve(self, creator_user_id: int, solver_username: str,
                             puzzle_name: str, xp_amount: int) -> None:
        """Create a notification: someone solved your puzzle."""
        msg = f"🎉 {solver_username} solved your puzzle \"{puzzle_name}\"! You earned {xp_amount} XP."
        self.repo.create(
            user_id=creator_user_id,
            notif_type="solve",
            message=msg,
            xp_amount=xp_amount,
            puzzle_name=puzzle_name,
            actor_username=solver_username,
        )

    def notify_creator_rating(self, creator_user_id: int, rater_username: str,
                              puzzle_name: str, xp_amount: int) -> None:
        """Create a notification: someone rated your puzzle."""
        msg = f"⭐ {rater_username} rated your puzzle \"{puzzle_name}\"! You earned {xp_amount} XP."
        self.repo.create(
            user_id=creator_user_id,
            notif_type="rating",
            message=msg,
            xp_amount=xp_amount,
            puzzle_name=puzzle_name,
            actor_username=rater_username,
        )

    # --- Called by API layer ---

    def get_unread(self, token: str) -> List[dict]:
        """Get all unread notifications for the authenticated user."""
        user_id = self.auth.require_user_id(token)
        return self.repo.get_unread(user_id)

    def get_all(self, token: str) -> List[dict]:
        """Get all notifications (both read and unread) for the authenticated user."""
        user_id = self.auth.require_user_id(token)
        return self.repo.get_all(user_id)

    def mark_all_read(self, token: str) -> dict:
        """Mark all notifications as read for the authenticated user."""
        user_id = self.auth.require_user_id(token)
        count = self.repo.mark_all_read(user_id)
        return {"marked_read": count}
