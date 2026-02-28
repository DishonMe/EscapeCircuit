import sqlite3
from typing import Optional, List

from Backend import settings
from Backend.DomainLayer.Discussion import Discussion
from Backend.DomainLayer.Enums import ReactionType, ThreadCategory, UserRole
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Utils import utcnow
from Backend.PersistantLayer._db import transaction
from Backend.PersistantLayer.DiscussionRepo import DiscussionRepo
from Backend.PersistantLayer.EngagementRepo import EngagementRepo
from Backend.PersistantLayer.ReplyRepo import ReplyRepo
from Backend.PersistantLayer.NotificationRepo import NotificationRepo
from Backend.PersistantLayer.ReportRepo import ReportRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService

# Aliases so the rest of the module is unchanged
VALID_REPORT_REASONS = settings.MODERATION_VALID_REPORT_REASONS

# XP constants for forum actions
DISCUSSION_CREATE_XP = settings.XP_DISCUSSION_CREATE
UPVOTE_XP = settings.XP_DISCUSSION_UPVOTE
REACTION_XP = settings.XP_DISCUSSION_REACTION


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

    def view_discussion(self, token: str, discussion_id: int) -> dict:
        """Increment view count once per visit. Called separately from get_discussion."""
        self.auth.require_user_id(token)
        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")
        self.discussion_repo.increment_view_count(discussion_id)
        return {"view_count": discussion.view_count + 1}

    def get_discussion(self, token: str, discussion_id: int) -> dict:
        user_id = self.auth.require_user_id(token)
        discussion = self.discussion_repo.get_by_id(discussion_id)
        if not discussion:
            raise ValidationError("discussion not found")

        result = discussion.to_dict()

        # Fetch ALL replies in one query (created_at ASC ordering preserved)
        all_replies = self.reply_repo.list_by_discussion(discussion_id, limit=10000)

        # Batch-fetch all authors (discussion + replies) in one query
        author_ids = list(set(
            [discussion.author_id] + [r.author_id for r in all_replies]
        ))
        authors_map = self.user_repo.get_by_ids(author_ids)

        # Attach discussion author
        author = authors_map.get(discussion.author_id)
        if author:
            result["author"] = author.to_dict()

        # Attach discussion engagement (single discussion — still 6 sub-queries)
        if self.engagement:
            result["engagement"] = self.engagement.get_discussion_engagement(discussion_id, user_id)

        # Bulk-fetch reply engagement (4 queries instead of 4*N)
        reply_ids = [r.id for r in all_replies]
        engagement_map = {}
        if self.engagement and reply_ids:
            engagement_map = self.engagement.get_bulk_reply_engagement(reply_ids, user_id)

        # Build enriched reply dicts
        reply_dicts: dict = {}
        for r in all_replies:
            rd = r.to_dict()
            a = authors_map.get(r.author_id)
            if a:
                rd["author"] = a.to_dict()
            if self.engagement:
                rd["engagement"] = engagement_map.get(r.id, {
                    "upvotes": 0, "downvotes": 0, "user_vote": None,
                    "reactions": [], "user_reactions": [],
                })
            reply_dicts[r.id] = rd

        # Build children map: parent_reply_id -> [reply_ids in creation order]
        children_map: dict = {}
        for r in all_replies:
            pid = r.parent_reply_id
            if pid not in children_map:
                children_map[pid] = []
            children_map[pid].append(r.id)

        # Assemble 3-level nested tree (top-level capped at 100, matching original)
        top_ids = children_map.get(None, [])[:100]
        replies_list = []
        for rid in top_ids:
            rd = reply_dicts[rid]
            children_list = []
            for cid in children_map.get(rid, []):
                cd = reply_dicts[cid]
                gc_list = []
                for gid in children_map.get(cid, []):
                    gd = reply_dicts[gid]
                    gd["children"] = []
                    gc_list.append(gd)
                cd["children"] = gc_list
                children_list.append(cd)
            rd["children"] = children_list
            replies_list.append(rd)

        result["replies"] = replies_list
        return result

    def list_discussions(
        self,
        token: str,
        limit: int = settings.LIST_DISCUSSIONS_DEFAULT_LIMIT,
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

        # Batch-fetch all authors in one query instead of N individual queries
        author_ids = list(set(d.author_id for d in discussions))
        authors_map = self.user_repo.get_by_ids(author_ids)

        items = []
        for d in discussions:
            item = d.to_dict()
            author = authors_map.get(d.author_id)
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

        # Atomic SQL-level toggle inside an IMMEDIATE transaction
        with transaction(self.discussion_repo.conn):
            self.discussion_repo.conn.execute(
                "UPDATE discussions SET is_pinned = 1 - is_pinned WHERE id = ?",
                (int(discussion_id),),
            )

        updated = self.discussion_repo.get_by_id(discussion_id)
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

        # Atomic SQL-level toggle inside an IMMEDIATE transaction
        with transaction(self.discussion_repo.conn):
            self.discussion_repo.conn.execute(
                "UPDATE discussions SET is_locked = 1 - is_locked WHERE id = ?",
                (int(discussion_id),),
            )

        updated = self.discussion_repo.get_by_id(discussion_id)
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

        # Award XP on upvote (only once per user per discussion, prevents toggle farming)
        if value == 1 and old_vote != 1 and discussion.author_id != user_id:
            if self.engagement.try_award_engagement_xp("discussion", discussion_id, user_id, "upvote"):
                self.xp._apply_xp(discussion.author_id, UPVOTE_XP)

        # Sync cache and get authoritative counts in one step (no redundant re-count)
        votes = self.discussion_repo.sync_upvotes_from_votes(discussion_id)

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

        # Award XP when reaction added (only once per user per discussion per reaction type)
        if is_active and discussion.author_id != user_id:
            if self.engagement.try_award_engagement_xp("discussion", discussion_id, user_id, f"reaction_{reaction_type}"):
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

        # Batch-fetch all referenced entities instead of N+1 individual queries
        disc_target_ids = [r["target_id"] for r in reports if r["target_type"] == "discussion"]
        reply_target_ids = [r["target_id"] for r in reports if r["target_type"] == "reply"]
        disc_map = self.discussion_repo.get_by_ids(disc_target_ids) if disc_target_ids else {}
        reply_map = self.reply_repo.get_by_ids(reply_target_ids) if reply_target_ids else {}

        # Collect all user IDs needed (reporters + target authors)
        all_user_ids = set(r["reporter_id"] for r in reports)
        for d in disc_map.values():
            all_user_ids.add(d.author_id)
        for rp in reply_map.values():
            all_user_ids.add(rp.author_id)
        users_map = self.user_repo.get_by_ids(list(all_user_ids))

        # Enrich with usernames using lookup dicts
        for report in reports:
            reporter = users_map.get(report["reporter_id"])
            report["reporter_username"] = reporter.username if reporter else "Unknown"
            if report["target_type"] == "discussion":
                disc = disc_map.get(report["target_id"])
                if disc:
                    author = users_map.get(disc.author_id)
                    report["target_author_id"] = disc.author_id
                    report["target_author_username"] = author.username if author else "Unknown"
            elif report["target_type"] == "reply":
                reply = reply_map.get(report["target_id"])
                if reply:
                    author = users_map.get(reply.author_id)
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
            deleted = self.reply_repo.delete(report["target_id"])
            # Only decrement if the delete actually removed a row (prevents double-decrement race)
            if deleted:
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
