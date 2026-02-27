import sqlite3
from typing import Optional, List

from Backend.DomainLayer.Discussion import Discussion
from Backend.DomainLayer.Enums import ReactionType, ThreadCategory, UserRole
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Utils import utcnow
from Backend.PersistantLayer.DiscussionRepo import DiscussionRepo
from Backend.PersistantLayer.EngagementRepo import EngagementRepo
from Backend.PersistantLayer.ReplyRepo import ReplyRepo
from Backend.PersistantLayer.NotificationRepo import NotificationRepo
from Backend.PersistantLayer.ReportRepo import ReportRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService

VALID_REPORT_REASONS = {"spam", "harassment", "off_topic", "inappropriate", "other"}


# XP constants for forum actions
DISCUSSION_CREATE_XP = 5
UPVOTE_XP = 3
REACTION_XP = 1


class DiscussionService:
    def __init__(
        self,
        discussion_repo: DiscussionRepo,
        reply_repo: ReplyRepo,
        user_repo: UserRepo,
        auth_service: AuthService,
        xp_service: XPService,
        engagement_repo: Optional[EngagementRepo] = None,
        report_repo: Optional[ReportRepo] = None,
        notification_repo: Optional[NotificationRepo] = None,
    ):
        self.discussion_repo = discussion_repo
        self.reply_repo = reply_repo
        self.user_repo = user_repo
        self.auth = auth_service
        self.xp = xp_service
        self.engagement = engagement_repo
        self.report_repo = report_repo
        self.notification_repo = notification_repo

    def create_discussion(self, token: str, payload: dict) -> dict:
        user_id = self.auth.require_user_id(token)
        user = self.user_repo.get_by_id(user_id)
        if user and user.is_discussion_banned:
            raise ValidationError("you are banned from creating discussions")
        title = (payload.get("title") or "").strip()
        body = (payload.get("body") or "").strip()
        category_str = payload.get("category", "general")
        puzzle_id = payload.get("puzzle_id")

        if not title:
            raise ValidationError("title is required")
        if not body:
            raise ValidationError("body is required")

        try:
            category = ThreadCategory(category_str)
        except ValueError:
            raise ValidationError(f"invalid category: {category_str}")

        discussion = Discussion(
            id=0,
            title=title,
            body=body,
            author_id=user_id,
            puzzle_id=int(puzzle_id) if puzzle_id is not None else None,
            category=category,
        )
        created = self.discussion_repo.create(discussion)

        # Award XP for creating a discussion
        self.xp._apply_xp(user_id, DISCUSSION_CREATE_XP)

        result = created.to_dict()
        author = self.user_repo.get_by_id(user_id)
        if author:
            result["author"] = author.to_dict()
        return result

    def _enrich_reply(self, reply, user_id: int) -> dict:
        """Convert reply to dict with author and engagement data."""
        reply_dict = reply.to_dict()
        reply_author = self.user_repo.get_by_id(reply.author_id)
        if reply_author:
            reply_dict["author"] = reply_author.to_dict()
        if self.engagement:
            reply_dict["engagement"] = self.engagement.get_reply_engagement(reply.id, user_id)
        return reply_dict

    def get_discussion(self, token: str, discussion_id: int) -> dict:
        user_id = self.auth.require_user_id(token)
        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        # Increment view count
        self.discussion_repo.increment_view_count(discussion_id)
        discussion.view_count += 1

        result = discussion.to_dict()

        # Attach author info
        author = self.user_repo.get_by_id(discussion.author_id)
        if author:
            result["author"] = author.to_dict()

        # Attach engagement data for the current user
        if self.engagement:
            result["engagement"] = self.engagement.get_discussion_engagement(discussion_id, user_id)

        # Attach replies (nested)
        top_replies = self.reply_repo.list_top_level(discussion_id, limit=100)
        replies_list = []
        for reply in top_replies:
            reply_dict = self._enrich_reply(reply, user_id)
            children = self.reply_repo.list_children(reply.id)
            children_list = []
            for child in children:
                child_dict = self._enrich_reply(child, user_id)
                grandchildren = self.reply_repo.list_children(child.id)
                gc_list = []
                for gc in grandchildren:
                    gc_dict = self._enrich_reply(gc, user_id)
                    gc_dict["children"] = []
                    gc_list.append(gc_dict)
                child_dict["children"] = gc_list
                children_list.append(child_dict)
            reply_dict["children"] = children_list
            replies_list.append(reply_dict)

        result["replies"] = replies_list
        return result

    def list_discussions(
        self,
        token: str,
        limit: int = 20,
        offset: int = 0,
        category: Optional[str] = None,
        puzzle_id: Optional[int] = None,
        author_id: Optional[int] = None,
        sort_by: str = "newest",
        search: Optional[str] = None,
    ) -> dict:
        self.auth.require_user_id(token)

        discussions = self.discussion_repo.list_all(
            limit=limit,
            offset=offset,
            category=category,
            puzzle_id=puzzle_id,
            author_id=author_id,
            sort_by=sort_by,
            search=search,
        )
        total = self.discussion_repo.count(
            category=category,
            puzzle_id=puzzle_id,
            author_id=author_id,
            search=search,
        )

        items = []
        for d in discussions:
            item = d.to_dict()
            author = self.user_repo.get_by_id(d.author_id)
            if author:
                item["author"] = author.to_dict()
            items.append(item)

        return {
            "discussions": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def update_discussion(self, token: str, discussion_id: int, payload: dict) -> dict:
        user_id = self.auth.require_user_id(token)
        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        user = self.user_repo.get_by_id(user_id)
        is_admin = user and user.role == UserRole.ADMIN
        is_owner = discussion.author_id == user_id

        if not is_admin and not is_owner:
            raise ValidationError("not allowed to update this discussion")

        fields = {}
        if "title" in payload:
            title = (payload["title"] or "").strip()
            if not title:
                raise ValidationError("title is required")
            fields["title"] = title
        if "body" in payload:
            body = (payload["body"] or "").strip()
            if not body:
                raise ValidationError("body is required")
            fields["body"] = body
        if "category" in payload:
            try:
                ThreadCategory(payload["category"])
            except ValueError:
                raise ValidationError(f"invalid category: {payload['category']}")
            fields["category"] = payload["category"]

        if not fields:
            raise ValidationError("nothing to update")

        updated = self.discussion_repo.update(discussion_id, fields)
        if not updated:
            raise ValidationError("discussion not found")

        result = updated.to_dict()
        author = self.user_repo.get_by_id(updated.author_id)
        if author:
            result["author"] = author.to_dict()
        return result

    def delete_discussion(self, token: str, discussion_id: int) -> dict:
        user_id = self.auth.require_user_id(token)
        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        user = self.user_repo.get_by_id(user_id)
        is_admin = user and user.role == UserRole.ADMIN
        is_owner = discussion.author_id == user_id

        if not is_admin and not is_owner:
            raise ValidationError("not allowed to delete this discussion")

        self.discussion_repo.delete(discussion_id)
        return {"deleted": True, "id": discussion_id}

    def pin_discussion(self, token: str, discussion_id: int) -> dict:
        user_id = self.auth.require_user_id(token)
        user = self.user_repo.get_by_id(user_id)
        if not user or user.role != UserRole.ADMIN:
            raise ValidationError("admin only")

        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        new_pinned = not discussion.is_pinned
        updated = self.discussion_repo.update(discussion_id, {"is_pinned": new_pinned})
        result = updated.to_dict()
        author = self.user_repo.get_by_id(updated.author_id)
        if author:
            result["author"] = author.to_dict()
        return result

    def lock_discussion(self, token: str, discussion_id: int) -> dict:
        user_id = self.auth.require_user_id(token)
        user = self.user_repo.get_by_id(user_id)
        if not user or user.role != UserRole.ADMIN:
            raise ValidationError("admin only")

        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        new_locked = not discussion.is_locked
        updated = self.discussion_repo.update(discussion_id, {"is_locked": new_locked})
        result = updated.to_dict()
        author = self.user_repo.get_by_id(updated.author_id)
        if author:
            result["author"] = author.to_dict()
        return result

    # ---- Engagement methods ----

    def vote_discussion(self, token: str, discussion_id: int, value: int) -> dict:
        user_id = self.auth.require_user_id(token)
        if not self.engagement:
            raise ValidationError("engagement not available")
        if value not in (1, -1):
            raise ValidationError("value must be 1 or -1")

        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        old_vote = self.engagement.get_discussion_vote(discussion_id, user_id)
        new_vote = self.engagement.set_discussion_vote(discussion_id, user_id, value)

        # Award XP on upvote (only when newly upvoting, not when toggling off)
        if value == 1 and old_vote != 1 and discussion.author_id != user_id:
            self.xp._apply_xp(discussion.author_id, UPVOTE_XP)

        votes = self.engagement.count_discussion_votes(discussion_id)
        # Update the cached upvotes on the discussion
        self.discussion_repo.update(discussion_id, {"upvotes": votes["upvotes"]})

        return {
            "discussion_id": discussion_id,
            "user_vote": new_vote,
            "upvotes": votes["upvotes"],
            "downvotes": votes["downvotes"],
        }

    def react_to_discussion(self, token: str, discussion_id: int, reaction_type: str) -> dict:
        user_id = self.auth.require_user_id(token)
        if not self.engagement:
            raise ValidationError("engagement not available")

        try:
            ReactionType(reaction_type)
        except ValueError:
            raise ValidationError(f"invalid reaction type: {reaction_type}")

        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        is_active = self.engagement.toggle_discussion_reaction(discussion_id, user_id, reaction_type)

        # Award XP when reaction added (not removed)
        if is_active and discussion.author_id != user_id:
            self.xp._apply_xp(discussion.author_id, REACTION_XP)

        reactions = self.engagement.get_discussion_reactions(discussion_id)
        user_reactions = self.engagement.get_user_discussion_reactions(discussion_id, user_id)

        return {
            "discussion_id": discussion_id,
            "is_active": is_active,
            "reactions": reactions,
            "user_reactions": user_reactions,
        }

    def follow_discussion(self, token: str, discussion_id: int) -> dict:
        user_id = self.auth.require_user_id(token)
        if not self.engagement:
            raise ValidationError("engagement not available")

        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        is_following = self.engagement.toggle_follow(discussion_id, user_id)
        return {
            "discussion_id": discussion_id,
            "is_following": is_following,
        }

    def bookmark_discussion(self, token: str, discussion_id: int) -> dict:
        user_id = self.auth.require_user_id(token)
        if not self.engagement:
            raise ValidationError("engagement not available")

        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        is_bookmarked = self.engagement.toggle_bookmark(discussion_id, user_id)
        return {
            "discussion_id": discussion_id,
            "is_bookmarked": is_bookmarked,
        }

    # ---- Report methods ----

    def report_discussion(self, token: str, discussion_id: int, reason: str, details: str = "") -> dict:
        user_id = self.auth.require_user_id(token)
        if not self.report_repo:
            raise ValidationError("reporting not available")
        if reason not in VALID_REPORT_REASONS:
            raise ValidationError(f"invalid reason: {reason}")

        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        if self.report_repo.has_reported(user_id, "discussion", discussion_id):
            raise ValidationError("you have already reported this discussion")

        try:
            return self.report_repo.create(user_id, "discussion", discussion_id, reason, details)
        except sqlite3.IntegrityError:
            raise ValidationError("you have already reported this discussion")

    def report_reply(self, token: str, reply_id: int, reason: str, details: str = "") -> dict:
        user_id = self.auth.require_user_id(token)
        if not self.report_repo:
            raise ValidationError("reporting not available")
        if reason not in VALID_REPORT_REASONS:
            raise ValidationError(f"invalid reason: {reason}")

        reply = self.reply_repo.get_by_id(reply_id)
        if not reply:
            raise ValidationError("reply not found")

        if self.report_repo.has_reported(user_id, "reply", reply_id):
            raise ValidationError("you have already reported this reply")

        try:
            return self.report_repo.create(user_id, "reply", reply_id, reason, details)
        except sqlite3.IntegrityError:
            raise ValidationError("you have already reported this reply")

    def list_reports(self, token: str, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> dict:
        user_id = self.auth.require_user_id(token)
        if not self.report_repo:
            raise ValidationError("reporting not available")

        user = self.user_repo.get_by_id(user_id)
        if not user or user.role != UserRole.ADMIN:
            raise ValidationError("admin only")

        reports = self.report_repo.list_all(status=status, limit=limit, offset=offset)
        total = self.report_repo.count(status=status)

        # Enrich with usernames
        for report in reports:
            reporter = self.user_repo.get_by_id(report["reporter_id"])
            report["reporter_username"] = reporter.username if reporter else "Unknown"
            # Get target author
            if report["target_type"] == "discussion":
                disc = self.discussion_repo.get_by_id(report["target_id"])
                if disc:
                    author = self.user_repo.get_by_id(disc.author_id)
                    report["target_author_id"] = disc.author_id
                    report["target_author_username"] = author.username if author else "Unknown"
            elif report["target_type"] == "reply":
                reply = self.reply_repo.get_by_id(report["target_id"])
                if reply:
                    author = self.user_repo.get_by_id(reply.author_id)
                    report["target_author_id"] = reply.author_id
                    report["target_author_username"] = author.username if author else "Unknown"
                    report["discussion_id"] = reply.discussion_id

        return {"reports": reports, "total": total, "limit": limit, "offset": offset}

    def update_report_status(self, token: str, report_id: int, status: str) -> dict:
        user_id = self.auth.require_user_id(token)
        if not self.report_repo:
            raise ValidationError("reporting not available")

        user = self.user_repo.get_by_id(user_id)
        if not user or user.role != UserRole.ADMIN:
            raise ValidationError("admin only")

        if status not in ("pending", "reviewed", "dismissed"):
            raise ValidationError(f"invalid status: {status}")

        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise ValidationError("report not found")

        return self.report_repo.update_status(report_id, status)

    def _require_admin(self, token: str) -> int:
        user_id = self.auth.require_user_id(token)
        user = self.user_repo.get_by_id(user_id)
        if not user or user.role != UserRole.ADMIN:
            raise ValidationError("admin only")
        return user_id

    def _get_report_target_author_id(self, report: dict) -> int:
        if report["target_type"] == "discussion":
            disc = self.discussion_repo.get_by_id(report["target_id"])
            if not disc:
                raise ValidationError("reported discussion not found")
            return disc.author_id
        elif report["target_type"] == "reply":
            reply = self.reply_repo.get_by_id(report["target_id"])
            if not reply:
                raise ValidationError("reported reply not found")
            return reply.author_id
        raise ValidationError("unknown target type")

    def warn_user_for_report(self, token: str, report_id: int) -> dict:
        self._require_admin(token)
        if not self.report_repo:
            raise ValidationError("reporting not available")

        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise ValidationError("report not found")

        target_author_id = self._get_report_target_author_id(report)

        # Send warning notification
        if self.notification_repo:
            msg = f"You have received a warning for your {report['target_type']} (reason: {report['reason']}). Please follow the community guidelines."
            self.notification_repo.create(
                user_id=target_author_id,
                notif_type="warning",
                message=msg,
            )

        # Mark report as reviewed
        self.report_repo.update_status(report_id, "reviewed")
        return {"action": "warned", "report_id": report_id, "warned_user_id": target_author_id}

    def ban_user_for_report(self, token: str, report_id: int) -> dict:
        self._require_admin(token)
        if not self.report_repo:
            raise ValidationError("reporting not available")

        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise ValidationError("report not found")

        target_author_id = self._get_report_target_author_id(report)

        # Ban the user from discussions
        self.user_repo.ban_from_discussions(target_author_id)

        # Send ban notification
        if self.notification_repo:
            msg = f"You have been banned from the discussions forum due to a violation (reason: {report['reason']}). You can no longer create discussions or replies."
            self.notification_repo.create(
                user_id=target_author_id,
                notif_type="ban",
                message=msg,
            )

        # Mark report as reviewed
        self.report_repo.update_status(report_id, "reviewed")
        return {"action": "banned", "report_id": report_id, "banned_user_id": target_author_id}

    def delete_reported_content(self, token: str, report_id: int) -> dict:
        self._require_admin(token)
        if not self.report_repo:
            raise ValidationError("reporting not available")

        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise ValidationError("report not found")

        if report["target_type"] == "discussion":
            disc = self.discussion_repo.get_by_id(report["target_id"])
            if not disc:
                raise ValidationError("reported discussion has already been deleted")
            self.discussion_repo.delete(report["target_id"])
        elif report["target_type"] == "reply":
            reply = self.reply_repo.get_by_id(report["target_id"])
            if not reply:
                raise ValidationError("reported reply has already been deleted")
            self.reply_repo.delete(report["target_id"])
            self.discussion_repo.increment_reply_count(reply.discussion_id, -1)

        # Mark report as reviewed
        self.report_repo.update_status(report_id, "reviewed")
        return {"action": "deleted", "report_id": report_id, "target_type": report["target_type"], "target_id": report["target_id"]}

    def lock_reported_discussion(self, token: str, report_id: int) -> dict:
        self._require_admin(token)
        if not self.report_repo:
            raise ValidationError("reporting not available")

        report = self.report_repo.get_by_id(report_id)
        if not report:
            raise ValidationError("report not found")

        if report["target_type"] != "discussion":
            raise ValidationError("can only lock discussions, not replies")

        discussion = self.discussion_repo.get_by_id(report["target_id"])
        if not discussion:
            raise ValidationError("discussion not found")

        self.discussion_repo.update(report["target_id"], {"is_locked": True})

        # Mark report as reviewed
        self.report_repo.update_status(report_id, "reviewed")
        return {"action": "locked", "report_id": report_id, "discussion_id": report["target_id"]}
