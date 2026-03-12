from typing import List, Optional
import pathlib
import os
import shutil
import re

from Backend import settings
from Backend.DomainLayer.Enums import UserRole, PuzzleStatus, AuditActionType
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer._db import transaction

from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.PersistantLayer.RatingRepo import RatingRepo
from Backend.PersistantLayer.AuditLogRepo import AuditLogRepo
from Backend.PersistantLayer.NotificationRepo import NotificationRepo

from Backend.ServiceLayer.AuthService import AuthService


class AdminService:
    """
    Orchestrates all admin-only actions: role management, puzzle moderation, audit logging.
    """

    def __init__(
        self,
        user_repo: UserRepo,
        puzzle_repo: PuzzleRepo,
        solve_repo: SolveRepo,
        rating_repo: RatingRepo,
        audit_log_repo: AuditLogRepo,
        notification_repo: NotificationRepo,
        auth_service: AuthService,
    ):
        self.user_repo = user_repo
        self.puzzle_repo = puzzle_repo
        self.solve_repo = solve_repo
        self.rating_repo = rating_repo
        self.audit_log = audit_log_repo
        self.notification_repo = notification_repo
        self.auth = auth_service

    def _require_admin(self, session_token: str) -> int:
        """Validate session and ensure user is admin. Returns admin user_id."""
        admin_id = self.auth.require_user_id(session_token)
        admin = self.user_repo.get_by_id(admin_id)
        if not admin or admin.role != UserRole.ADMIN:
            raise ValidationError("admin required")
        return admin_id

    @staticmethod
    def _slugify_puzzle_name(name: str) -> str:
        sanitized = re.sub(r'[^\w\s-]', '', name or '')
        sanitized = re.sub(r'[\s-]+', '_', sanitized)
        return sanitized.lower().strip('_')

    def _delete_riddle_files(self, puzzle_name: str) -> None:
        """Delete riddle files from the riddles directory matching the puzzle name."""
        try:
            # Get riddles directory path
            current_file = pathlib.Path(__file__).resolve()
            root_dir = current_file.parent.parent.parent.parent
            riddles_dir = root_dir / 'riddles'
            
            if not riddles_dir.exists():
                return
            
            puzzle_slug = self._slugify_puzzle_name(puzzle_name)

            def matches_riddle_item(item_name: str, is_dir: bool) -> bool:
                item_lower = item_name.lower()
                if puzzle_slug:
                    if is_dir and re.fullmatch(rf'riddle_\d+_{re.escape(puzzle_slug)}', item_lower):
                        return True
                    if (not is_dir) and re.match(rf'riddle_\d+_{re.escape(puzzle_slug)}_', item_lower):
                        return True
                # Legacy fallback for older naming variants
                return ("_" + puzzle_name.lower() + "_") in item_lower

            deleted_count = 0
            for item in riddles_dir.iterdir():
                if matches_riddle_item(item.name, item.is_dir()):
                    try:
                        if item.is_file():
                            item.unlink()
                            print(f"[DELETE] Removed riddle file: {item.name}")
                        elif item.is_dir():
                            shutil.rmtree(item)
                            print(f"[DELETE] Removed riddle folder: {item.name}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"[WARNING] Failed to delete {item.name}: {e}")
            
            if deleted_count > 0:
                print(f"[DELETE] Removed {deleted_count} riddle item(s) for puzzle: {puzzle_name}")
        except Exception as e:
            print(f"[WARNING] Error during riddle cleanup: {e}")

    def _require_admin_or_creator(self, session_token: str) -> int:
        """Validate session and ensure user is admin or creator. Returns user_id."""
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user or user.role not in (UserRole.ADMIN, UserRole.CREATOR, UserRole.PENDING_CREATOR):
            raise ValidationError("admin or creator required")
        return user_id

    # ------------------------------------------------------------------ #
    #  REQ 7.2 + 1.2  —  Assign Creator Role (pending invitation)
    # ------------------------------------------------------------------ #
    def assign_creator(self, session_token: str, target_user_id: int) -> dict:
        admin_id = self._require_admin(session_token)

        target = self.user_repo.get_by_id(target_user_id)
        if not target:
            raise ValidationError("target user not found")
        if target.role == UserRole.ADMIN:
            raise ValidationError("cannot change admin role")
        if target.role == UserRole.CREATOR:
            raise ValidationError("user is already a creator")
        if target.role == UserRole.PENDING_CREATOR:
            raise ValidationError("user already has a pending creator invitation")

        # Atomically set to pending_creator only if still SOLVER (prevents duplicate notifications)
        changed = self.user_repo.update_role_if(target_user_id, UserRole.PENDING_CREATOR, target.role)
        if not changed:
            raise ValidationError("user role was changed by another admin")
        self.user_repo.conn.commit()

        # Notify the target user
        admin_user = self.user_repo.get_by_id(admin_id)
        self.notification_repo.create(
            user_id=target_user_id,
            notif_type="creator_invite",
            message=f"You have been invited to become a Creator by {admin_user.username}. Accept or decline in your profile.",
            actor_username=admin_user.username,
        )

        # Audit log (req 7.5)
        self.audit_log.create(
            admin_user_id=admin_id,
            action_type=AuditActionType.ASSIGN_CREATOR.value,
            target_user_id=target_user_id,
            details={"previous_role": target.role.value},
        )

        return {"ok": True, "new_role": UserRole.PENDING_CREATOR.value}

    # ------------------------------------------------------------------ #
    #  REQ 7.3 + 1.2.1  —  Remove Creator Role
    # ------------------------------------------------------------------ #
    def remove_creator(self, session_token: str, target_user_id: int) -> dict:
        admin_id = self._require_admin(session_token)

        target = self.user_repo.get_by_id(target_user_id)
        if not target:
            raise ValidationError("target user not found")
        if target.role not in (UserRole.CREATOR, UserRole.PENDING_CREATOR):
            raise ValidationError("user is not a creator or pending creator")

        # If pending creator, just cancel without asking about puzzles
        if target.role == UserRole.PENDING_CREATOR:
            changed = self.user_repo.update_role_if(target_user_id, UserRole.SOLVER, target.role)
            if not changed:
                raise ValidationError("user role was changed by another admin")
            
            self.notification_repo.create(
                user_id=target_user_id,
                notif_type="role_change",
                message="Your pending Creator role has been cancelled by an admin.",
            )
            
            self.audit_log.create(
                admin_user_id=admin_id,
                action_type=AuditActionType.REMOVE_CREATOR.value,
                target_user_id=target_user_id,
                details={
                    "previous_role": target.role.value,
                    "was_pending": True,
                },
            )
            
            return {"ok": True, "new_role": UserRole.SOLVER.value, "was_pending": True}

        # For actual creators, return info about their puzzles
        published_puzzles = self.puzzle_repo.get_by_creator_and_status(
            target_user_id, PuzzleStatus.PUBLISHED
        )
        draft_puzzles = self.puzzle_repo.get_by_creator_and_status(
            target_user_id, PuzzleStatus.DRAFT
        )
        
        return {
            "ok": True,
            "user_id": target_user_id,
            "username": target.username,
            "published_count": len(published_puzzles),
            "draft_count": len(draft_puzzles),
            "published_puzzles": [{"id": p.id, "name": p.name} for p in published_puzzles],
            "admin_action_required": len(published_puzzles) > 0,
        }

    def confirm_remove_creator(
        self, 
        session_token: str, 
        target_user_id: int, 
        action: str
    ) -> dict:
        """
        Confirm creator removal with specified action for published puzzles.
        action: "unpublish", "delete", or "leave"
        """
        admin_id = self._require_admin(session_token)

        target = self.user_repo.get_by_id(target_user_id)
        if not target:
            raise ValidationError("target user not found")
        if target.role != UserRole.CREATOR:
            raise ValidationError("user is not a creator")

        if action not in ("unpublish", "delete", "leave"):
            raise ValidationError("invalid action")

        previous_role = target.role.value
        draft_count = 0
        published_count = 0
        action_taken = action

        with transaction(self.user_repo.conn) as txn:
            # Handle draft puzzles — always delete
            draft_puzzles = self.puzzle_repo.get_by_creator_and_status(
                target_user_id, PuzzleStatus.DRAFT
            )
            draft_ids = [p.id for p in draft_puzzles]
            draft_count = len(draft_ids)
            if draft_ids:
                self.solve_repo.delete_by_puzzle_ids(draft_ids)
                for pid in draft_ids:
                    self.rating_repo.delete_by_puzzle(pid)
                for p in draft_puzzles:
                    self.puzzle_repo.track_user_deletion(p.name)
                self.puzzle_repo.delete_by_ids(draft_ids)

            # Handle published puzzles based on admin's choice
            published_puzzles = self.puzzle_repo.get_by_creator_and_status(
                target_user_id, PuzzleStatus.PUBLISHED
            )
            published_ids = [p.id for p in published_puzzles]
            published_count = len(published_ids)

            if action == "delete" and published_ids:
                self.solve_repo.delete_by_puzzle_ids(published_ids)
                for pid in published_ids:
                    self.rating_repo.delete_by_puzzle(pid)
                for p in published_puzzles:
                    self.puzzle_repo.track_admin_deletion(p.name)
                self.puzzle_repo.delete_by_ids(published_ids)
            elif action == "unpublish" and published_ids:
                # Unpublish published puzzles
                for p in published_puzzles:
                    p.status = PuzzleStatus.UNPUBLISHED
                    self.puzzle_repo.update(p)

            # Demote user to solver
            changed = self.user_repo.update_role_if(target_user_id, UserRole.SOLVER, target.role)
            if not changed:
                raise ValidationError("user role was changed by another admin")
            # COMMIT at context-manager exit

        # Notify user
        if action == "delete":
            message = f"Your Creator role has been removed by an admin. {published_count} published puzzle(s) and {draft_count} draft puzzle(s) have been deleted. You have been set back to Solver."
        elif action == "unpublish":
            message = f"Your Creator role has been removed by an admin. {published_count} published puzzle(s) have been unpublished and {draft_count} draft puzzle(s) have been deleted. You have been set back to Solver."
        else:  # leave
            message = f"Your Creator role has been removed by an admin. Your {published_count} published puzzle(s) remain published. {draft_count} draft puzzle(s) have been deleted. You have been set back to Solver."

        self.notification_repo.create(
            user_id=target_user_id,
            notif_type="role_change",
            message=message,
        )

        # Audit log (req 7.5)
        self.audit_log.create(
            admin_user_id=admin_id,
            action_type=AuditActionType.REMOVE_CREATOR.value,
            target_user_id=target_user_id,
            details={
                "previous_role": previous_role,
                "draft_puzzles_deleted": draft_count,
                "published_puzzles_action": action_taken,
                "published_count": published_count,
            },
        )

        return {
            "ok": True,
            "new_role": UserRole.SOLVER.value,
            "action": action,
            "draft_deleted": draft_count,
            "published_affected": published_count,
        }

    # ------------------------------------------------------------------ #
    #  REQ 7.4  —  Delete Any Puzzle
    # ------------------------------------------------------------------ #
    def delete_puzzle(self, session_token: str, puzzle_id: int) -> dict:
        admin_id = self._require_admin(session_token)

        puzzle = self.puzzle_repo.get_by_id(puzzle_id)
        if not puzzle:
            raise ValidationError("puzzle not found")

        # Admins may not directly delete a published puzzle; they must unpublish first
        if puzzle.status == PuzzleStatus.PUBLISHED:
            raise ValidationError(
                "Cannot delete a published puzzle. Unpublish it first, then delete."
            )

        puzzle_name = puzzle.name
        creator_id = puzzle.creator_user_id
        status = puzzle.status.value

        # Wrap cleanup + delete in one IMMEDIATE transaction so no
        # concurrent solve/rating can be inserted mid-delete (H5).
        with transaction(self.puzzle_repo.conn) as txn:
            self.solve_repo.delete_by_puzzle(puzzle_id)
            self.rating_repo.delete_by_puzzle(puzzle_id)
            self.puzzle_repo.delete(puzzle_id)
            # Track admin deletion to prevent re-import by insert_riddles
            self.puzzle_repo.track_admin_deletion(puzzle_name)
            # COMMIT at context-manager exit

        # Delete riddle files from riddles directory
        self._delete_riddle_files(puzzle_name)

        # Audit log (req 7.5)
        self.audit_log.create(
            admin_user_id=admin_id,
            action_type=AuditActionType.DELETE_PUZZLE.value,
            target_puzzle_id=puzzle_id,
            target_user_id=creator_id,
            details={
                "puzzle_name": puzzle_name,
                "previous_status": status,
            },
        )

        return {"ok": True}

    # ------------------------------------------------------------------ #
    #  Admin Unpublish Puzzle (moderation — bypasses unpublished-limit)
    # ------------------------------------------------------------------ #
    def admin_unpublish_puzzle(self, session_token: str, puzzle_id: int) -> dict:
        """Unpublish a published puzzle as an admin.

        Unlike a creator unpublishing their own puzzle, this bypasses the
        creator's unpublished-capacity limit — the puzzle is always unpublished,
        but the creator may become blocked from editing/creating until they
        remove enough puzzles.
        """
        admin_id = self._require_admin(session_token)

        puzzle = self.puzzle_repo.get_by_id(puzzle_id)
        if not puzzle:
            raise ValidationError("puzzle not found")

        if puzzle.status != PuzzleStatus.PUBLISHED:
            raise ValidationError("puzzle is not published")

        puzzle_name = puzzle.name
        creator_id = puzzle.creator_user_id

        self.puzzle_repo.conn.execute(
            "UPDATE puzzles SET status = 'unpublished' WHERE id = ? AND status = 'published'",
            (int(puzzle_id),),
        )
        self.puzzle_repo.conn.commit()

        # Notify the creator
        creator = self.user_repo.get_by_id(creator_id)
        if creator:
            self.notification_repo.create(
                user_id=creator_id,
                notif_type="puzzle_unpublished",
                message=f"Your puzzle \"{puzzle_name}\" has been unpublished by an admin.",
            )

        # Audit log
        self.audit_log.create(
            admin_user_id=admin_id,
            action_type=AuditActionType.UNPUBLISH_PUZZLE.value,
            target_puzzle_id=puzzle_id,
            target_user_id=creator_id,
            details={"puzzle_name": puzzle_name},
        )

        return {"ok": True}

    # ------------------------------------------------------------------ #
    #  Admin: edit creator's puzzle capacity overrides
    # ------------------------------------------------------------------ #
    def update_creator_puzzle_limits(
        self,
        session_token: str,
        target_user_id: int,
        max_published: Optional[int],
        max_unpublished: Optional[int],
    ) -> dict:
        """Set per-creator published/unpublished puzzle capacity overrides.

        Pass None for either value to revert to the level-based default.
        """
        self._require_admin(session_token)

        target = self.user_repo.get_by_id(target_user_id)
        if not target:
            raise ValidationError("target user not found")
        if target.role not in (UserRole.CREATOR, UserRole.PENDING_CREATOR):
            raise ValidationError("target user is not a creator")

        if max_published is not None and max_published < 0:
            raise ValidationError("max_published cannot be negative")
        if max_unpublished is not None and max_unpublished < 0:
            raise ValidationError("max_unpublished cannot be negative")

        self.user_repo.update_puzzle_limits(target_user_id, max_published, max_unpublished)

        # Re-fetch to return current effective values
        updated = self.user_repo.get_by_id(target_user_id)
        eff_published, eff_unpublished = updated.get_puzzle_capacity()

        return {
            "ok": True,
            "user_id": target_user_id,
            "max_published_override": max_published,
            "max_unpublished_override": max_unpublished,
            "effective_max_published": eff_published,
            "effective_max_unpublished": eff_unpublished,
        }

    # ------------------------------------------------------------------ #
    #  Admin Puzzle Listing (moderation view)
    # ------------------------------------------------------------------ #
    def list_puzzles(
        self,
        session_token: str,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        status: Optional[str] = None,
        creator_id: Optional[int] = None,
        creator_username: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
    ) -> dict:
        self._require_admin(session_token)

        puzzles = self.puzzle_repo.list_all_for_admin(
            limit=limit,
            offset=offset,
            search=search,
            status=status,
            creator_id=creator_id,
            creator_username=creator_username,
            date_from=date_from,
            date_to=date_to,
            order_by=order_by,
            order_direction=order_direction,
        )
        total = self.puzzle_repo.count_all_for_admin(
            search=search,
            status=status,
            creator_id=creator_id,
            creator_username=creator_username,
            date_from=date_from,
            date_to=date_to,
        )
        limit = max(1, limit)
        total_pages = (total + limit - 1) // limit

        # Batch-fetch all creators in one query instead of N individual queries
        creator_ids = list(set(p.creator_user_id for p in puzzles))
        creators_map = self.user_repo.get_by_ids(creator_ids)

        enriched = []
        for p in puzzles:
            d = p.to_dict()
            # Add moderation flags
            d["flags"] = []
            if p.status == PuzzleStatus.PUBLISHED:
                if p.avg_fun > 0 and p.avg_fun < settings.MODERATION_LOW_FUN_THRESHOLD:
                    d["flags"].append("low_fun")
                if p.avg_clearness > 0 and p.avg_clearness < settings.MODERATION_LOW_CLEARNESS_THRESHOLD:
                    d["flags"].append("low_clearness")
                if p.rating_count == 0:
                    d["flags"].append("unrated")
            # Attach creator info
            creator = creators_map.get(p.creator_user_id)
            if creator:
                d["creator"] = creator.to_dict()
            enriched.append(d)

        return {
            "data": enriched,
            "meta": {
                "page": (offset // limit) + 1,
                "total": total,
                "totalPages": total_pages,
            },
        }

    # ------------------------------------------------------------------ #
    #  REQ 7.5  —  Audit Log Listing
    # ------------------------------------------------------------------ #
    def list_audit_log(
        self,
        session_token: str,
        limit: int = 100,
        offset: int = 0,
        action_type: Optional[str] = None,
    ) -> List[dict]:
        self._require_admin(session_token)
        return self.audit_log.list_all(
            limit=limit,
            offset=offset,
            action_type=action_type,
        )
