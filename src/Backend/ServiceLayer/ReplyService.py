import sqlite3
from typing import Optional

from Backend import settings
from Backend.DomainLayer.Reply import Reply
from Backend.DomainLayer.Enums import ReactionType, UserRole
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer._db import transaction
from Backend.PersistantLayer.DiscussionRepo import DiscussionRepo
from Backend.PersistantLayer.EngagementRepo import EngagementRepo
from Backend.PersistantLayer.ReplyRepo import ReplyRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService


# XP constants for forum actions (aliases into settings)
REPLY_CREATE_XP = settings.XP_REPLY_CREATE
REPLY_ACCEPTED_XP = settings.XP_REPLY_ACCEPTED
ACCEPT_SOLUTION_XP = settings.XP_ACCEPT_SOLUTION
REPLY_UPVOTE_XP = settings.XP_REPLY_UPVOTE
REPLY_REACTION_XP = settings.XP_REPLY_REACTION


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
        user = self.user_repo.get_by_id(user_id)
        if user and user.is_discussion_banned:
            raise ValidationError("you are banned from creating replies")
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
        # Wrap insert + reply_count increment + XP in one transaction
        # to prevent counter drift on concurrent create/delete (C4).
        try:
            with transaction(self.reply_repo.conn):
                created = self.reply_repo.create(reply, commit=False)
                self.discussion_repo.increment_reply_count(discussion_id, 1, commit=False)
                self.xp._apply_xp(user_id, REPLY_CREATE_XP)
        except sqlite3.IntegrityError:
            raise ValidationError("discussion was deleted")

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
        # Wrap delete + reply_count decrement in one transaction (C4).
        with transaction(self.reply_repo.conn):
            deleted = self.reply_repo.delete(reply_id, commit=False)
            if deleted:
                self.discussion_repo.increment_reply_count(discussion_id, -1, commit=False)

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

        conn = self.reply_repo.conn

        # Wrap the entire accept/unaccept + XP award in one IMMEDIATE
        # transaction to prevent TOCTOU on is_accepted state (C5).
        with transaction(conn) as txn:
            # Re-read is_accepted under the write lock to get fresh state
            fresh = txn.execute(
                "SELECT is_accepted FROM replies WHERE id = ?", (reply_id,)
            ).fetchone()
            if not fresh:
                raise ValidationError("reply not found")

            if fresh["is_accepted"]:
                # Unaccept
                txn.execute(
                    "UPDATE discussions SET accepted_reply_id = NULL WHERE id = ?",
                    (discussion.id,),
                )
                txn.execute(
                    "UPDATE replies SET is_accepted = 0 WHERE id = ?",
                    (reply_id,),
                )
                # COMMIT at context-manager exit

                updated = self.reply_repo.get_by_id(reply_id)
                result = updated.to_dict()
                author = self.user_repo.get_by_id(updated.author_id)
                if author:
                    result["author"] = author.to_dict()
                return result

            # Accept: atomically set is_accepted=1 only if still 0
            cur = txn.execute(
                "UPDATE replies SET is_accepted = 1 WHERE id = ? AND is_accepted = 0",
                (reply_id,),
            )
            newly_accepted = cur.rowcount > 0

            # Update discussion and clear other accepted replies
            txn.execute(
                "UPDATE discussions SET accepted_reply_id = ? WHERE id = ?",
                (reply_id, discussion.id),
            )
            txn.execute(
                "UPDATE replies SET is_accepted = 0 WHERE discussion_id = ? AND id != ?",
                (discussion.id, reply_id),
            )

            # Award XP inside the same transaction so dedup + award are atomic
            if newly_accepted:
                if reply.author_id != user_id:
                    self.xp._apply_xp(reply.author_id, REPLY_ACCEPTED_XP)
                self.xp._apply_xp(user_id, ACCEPT_SOLUTION_XP)
            # COMMIT at context-manager exit

        updated = self.reply_repo.get_by_id(reply_id)
        result = updated.to_dict() if updated else reply.to_dict()
        author = self.user_repo.get_by_id(reply.author_id)
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

        # Award XP on upvote (only once per user per reply, prevents toggle farming)
        if value == 1 and old_vote != 1 and reply.author_id != user_id:
            if self.engagement.try_award_engagement_xp("reply", reply_id, user_id, "upvote"):
                self.xp._apply_xp(reply.author_id, REPLY_UPVOTE_XP)

        # Atomically sync cached vote counts from authoritative vote table
        self.reply_repo.sync_votes_from_votes(reply_id)
        votes = self.engagement.count_reply_votes(reply_id)

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

        # Award XP when reaction added (only once per user per reply per reaction type)
        if is_active and reply.author_id != user_id:
            if self.engagement.try_award_engagement_xp("reply", reply_id, user_id, f"reaction_{reaction_type}"):
                self.xp._apply_xp(reply.author_id, REPLY_REACTION_XP)

        reactions = self.engagement.get_reply_reactions(reply_id)
        user_reactions = self.engagement.get_user_reply_reactions(reply_id, user_id)

        return {
            "reply_id": reply_id,
            "is_active": is_active,
            "reactions": reactions,
            "user_reactions": user_reactions,
        }
