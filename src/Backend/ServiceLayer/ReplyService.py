from typing import Optional

from Backend.DomainLayer.Reply import Reply
from Backend.DomainLayer.Enums import ReactionType, UserRole
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.DiscussionRepo import DiscussionRepo
from Backend.PersistantLayer.EngagementRepo import EngagementRepo
from Backend.PersistantLayer.ReplyRepo import ReplyRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService


# XP constants for forum actions
REPLY_CREATE_XP = 2
REPLY_ACCEPTED_XP = 25
ACCEPT_SOLUTION_XP = 5
REPLY_UPVOTE_XP = 3
REPLY_REACTION_XP = 1


class ReplyService:
    def __init__(
        self,
        reply_repo: ReplyRepo,
        discussion_repo: DiscussionRepo,
        user_repo: UserRepo,
        auth_service: AuthService,
        xp_service: XPService,
        engagement_repo: Optional[EngagementRepo] = None,
    ):
        self.reply_repo = reply_repo
        self.discussion_repo = discussion_repo
        self.user_repo = user_repo
        self.auth = auth_service
        self.xp = xp_service
        self.engagement = engagement_repo

    def create_reply(self, token: str, discussion_id: int, payload: dict) -> dict:
        user_id = self.auth.require_user_id(token)
        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")
        if discussion.is_locked:
            raise ValidationError("discussion is locked")

        body = (payload.get("body") or "").strip()
        if not body:
            raise ValidationError("body is required")

        parent_reply_id = payload.get("parent_reply_id")
        if parent_reply_id is not None:
            parent_reply_id = int(parent_reply_id)
            parent = self.reply_repo.get_by_id(parent_reply_id)
            if not parent or parent.discussion_id != discussion_id:
                raise ValidationError("invalid parent reply")

        reply = Reply(
            id=0,
            discussion_id=discussion_id,
            author_id=user_id,
            body=body,
            parent_reply_id=parent_reply_id,
        )
        created = self.reply_repo.create(reply)

        # Update reply count on discussion
        self.discussion_repo.increment_reply_count(discussion_id, 1)

        # Award XP for creating a reply
        self.xp._apply_xp(user_id, REPLY_CREATE_XP)

        result = created.to_dict()
        author = self.user_repo.get_by_id(user_id)
        if author:
            result["author"] = author.to_dict()
        return result

    def get_replies(self, token: str, discussion_id: int, limit: int = 100, offset: int = 0) -> dict:
        self.auth.require_user_id(token)
        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        replies = self.reply_repo.list_by_discussion(discussion_id, limit=limit, offset=offset)
        total = self.reply_repo.count_by_discussion(discussion_id)

        items = []
        for r in replies:
            item = r.to_dict()
            author = self.user_repo.get_by_id(r.author_id)
            if author:
                item["author"] = author.to_dict()
            items.append(item)

        return {
            "replies": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def update_reply(self, token: str, reply_id: int, payload: dict) -> dict:
        user_id = self.auth.require_user_id(token)
        reply = self.reply_repo.get_by_id(reply_id)
        if not reply:
            raise ValidationError("reply not found")

        user = self.user_repo.get_by_id(user_id)
        is_admin = user and user.role == UserRole.ADMIN
        is_owner = reply.author_id == user_id

        if not is_admin and not is_owner:
            raise ValidationError("not allowed to update this reply")

        body = (payload.get("body") or "").strip()
        if not body:
            raise ValidationError("body is required")

        updated = self.reply_repo.update(reply_id, {"body": body})
        if not updated:
            raise ValidationError("reply not found")

        result = updated.to_dict()
        author = self.user_repo.get_by_id(updated.author_id)
        if author:
            result["author"] = author.to_dict()
        return result

    def delete_reply(self, token: str, reply_id: int) -> dict:
        user_id = self.auth.require_user_id(token)
        reply = self.reply_repo.get_by_id(reply_id)
        if not reply:
            raise ValidationError("reply not found")

        user = self.user_repo.get_by_id(user_id)
        is_admin = user and user.role == UserRole.ADMIN
        is_owner = reply.author_id == user_id

        if not is_admin and not is_owner:
            raise ValidationError("not allowed to delete this reply")

        discussion_id = reply.discussion_id
        self.reply_repo.delete(reply_id)

        # Decrement reply count on discussion
        self.discussion_repo.increment_reply_count(discussion_id, -1)

        return {"deleted": True, "id": reply_id}

    def accept_reply(self, token: str, reply_id: int) -> dict:
        user_id = self.auth.require_user_id(token)
        reply = self.reply_repo.get_by_id(reply_id)
        if not reply:
            raise ValidationError("reply not found")

        discussion = self.discussion_repo.get_by_id(reply.discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        user = self.user_repo.get_by_id(user_id)
        is_admin = user and user.role == UserRole.ADMIN
        is_owner = discussion.author_id == user_id

        if not is_admin and not is_owner:
            raise ValidationError("only the thread author or admin can accept a solution")

        # If this reply is already accepted, unaccept it
        if reply.is_accepted:
            self.reply_repo.update(reply_id, {"is_accepted": False})
            self.discussion_repo.set_accepted_reply(discussion.id, None)
            updated = self.reply_repo.get_by_id(reply_id)
            result = updated.to_dict()
            author = self.user_repo.get_by_id(updated.author_id)
            if author:
                result["author"] = author.to_dict()
            return result

        # Clear any previously accepted reply
        self.reply_repo.clear_accepted_for_discussion(discussion.id)

        # Accept this reply
        self.reply_repo.update(reply_id, {"is_accepted": True})
        self.discussion_repo.set_accepted_reply(discussion.id, reply_id)

        # Award XP: +25 to reply author, +5 to thread author for accepting
        if reply.author_id != user_id:
            self.xp._apply_xp(reply.author_id, REPLY_ACCEPTED_XP)
        self.xp._apply_xp(user_id, ACCEPT_SOLUTION_XP)

        updated = self.reply_repo.get_by_id(reply_id)
        result = updated.to_dict()
        author = self.user_repo.get_by_id(updated.author_id)
        if author:
            result["author"] = author.to_dict()
        return result

    # ---- Engagement methods ----

    def vote_reply(self, token: str, reply_id: int, value: int) -> dict:
        user_id = self.auth.require_user_id(token)
        if not self.engagement:
            raise ValidationError("engagement not available")
        if value not in (1, -1):
            raise ValidationError("value must be 1 or -1")

        reply = self.reply_repo.get_by_id(reply_id)
        if not reply:
            raise ValidationError("reply not found")

        old_vote = self.engagement.get_reply_vote(reply_id, user_id)
        new_vote = self.engagement.set_reply_vote(reply_id, user_id, value)

        # Award XP on upvote (only when newly upvoting)
        if value == 1 and old_vote != 1 and reply.author_id != user_id:
            self.xp._apply_xp(reply.author_id, REPLY_UPVOTE_XP)

        votes = self.engagement.count_reply_votes(reply_id)
        # Update cached vote counts on the reply
        self.reply_repo.update_votes(reply_id, votes["upvotes"], votes["downvotes"])

        return {
            "reply_id": reply_id,
            "user_vote": new_vote,
            "upvotes": votes["upvotes"],
            "downvotes": votes["downvotes"],
        }

    def react_to_reply(self, token: str, reply_id: int, reaction_type: str) -> dict:
        user_id = self.auth.require_user_id(token)
        if not self.engagement:
            raise ValidationError("engagement not available")

        try:
            ReactionType(reaction_type)
        except ValueError:
            raise ValidationError(f"invalid reaction type: {reaction_type}")

        reply = self.reply_repo.get_by_id(reply_id)
        if not reply:
            raise ValidationError("reply not found")

        is_active = self.engagement.toggle_reply_reaction(reply_id, user_id, reaction_type)

        # Award XP when reaction added (not removed)
        if is_active and reply.author_id != user_id:
            self.xp._apply_xp(reply.author_id, REPLY_REACTION_XP)

        reactions = self.engagement.get_reply_reactions(reply_id)
        user_reactions = self.engagement.get_user_reply_reactions(reply_id, user_id)

        return {
            "reply_id": reply_id,
            "is_active": is_active,
            "reactions": reactions,
            "user_reactions": user_reactions,
        }
