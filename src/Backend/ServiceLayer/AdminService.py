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
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
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
        circuit_repo: Optional[CircuitRepo] = None,
    ):
        self.user_repo = user_repo
        self.circuit_repo = circuit_repo
        self.puzzle_repo = puzzle_repo
        self.solve_repo = solve_repo
        self.rating_repo = rating_repo
        self.audit_log = audit_log_repo
        self.notification_repo = notification_repo
        self.auth = auth_service

    def _get_online_user_ids(self) -> set[int]:
        if not hasattr(self.auth, "_sessions") or not hasattr(self.auth, "_lock"):
            return set()
        try:
            with self.auth._lock:
                return {int(s.user_id) for s in self.auth._sessions.values()}
        except Exception:
            return set()

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

    @staticmethod
    def _sanitize_puzzle_name(name: str) -> str:
        """Sanitize puzzle name for use in directory/file names (matches creation logic).
        Convert spaces to underscores, convert to lowercase, and strip illegal characters."""
        sanitized = re.sub(r'[^\w\s-]', '', name or '')
        sanitized = re.sub(r'[\s-]+', '_', sanitized)
        return sanitized.lower()

    def _delete_riddle_files(self, puzzle_id: int, puzzle_name: str) -> None:
        """Delete riddle directory for a puzzle using puzzle_id and name.
        This uses the same naming convention as creation: riddle_{puzzle_id}_{sanitized_name}"""
        try:
            # Get riddles directory path
            current_file = pathlib.Path(__file__).resolve()
            root_dir = current_file.parent.parent.parent.parent
            riddles_dir = root_dir / 'riddles'
            
            if not riddles_dir.exists():
                print(f"[DELETE] Riddles directory not found: {riddles_dir}")
                return
            
            # Reconstruct directory name using the same logic as creation
            sanitized_name = self._sanitize_puzzle_name(puzzle_name)
            riddle_dir_name = f'riddle_{puzzle_id}_{sanitized_name}'
            riddle_dir_path = riddles_dir / riddle_dir_name
            
            # Delete the directory if it exists
            if riddle_dir_path.exists():
                try:
                    shutil.rmtree(riddle_dir_path)
                    print(f"✓ Successfully deleted puzzle directory: {riddle_dir_path}")
                except Exception as e:
                    print(f"⚠ Error deleting directory {riddle_dir_path}: {e}")
            else:
                print(f"[DELETE] Directory not found: {riddle_dir_path}")
                # Try legacy search as fallback
                puzzle_slug = self._slugify_puzzle_name(puzzle_name)
                for item in riddles_dir.iterdir():
                    if item.is_dir() and re.match(rf'riddle_\d+_{re.escape(puzzle_slug)}', item.name.lower()):
                        try:
                            shutil.rmtree(item)
                            print(f"[DELETE] Removed legacy puzzle directory: {item.name}")
                            return
                        except Exception as e:
                            print(f"[WARNING] Failed to delete legacy directory {item.name}: {e}")
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

        # Delete riddle directory from riddles directory (using puzzle_id for accurate path reconstruction)
        self._delete_riddle_files(puzzle_id, puzzle_name)

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
        admin_id = self._require_admin(session_token)

        target = self.user_repo.get_by_id(target_user_id)
        if not target:
            raise ValidationError("target user not found")
        if target.role not in (UserRole.CREATOR, UserRole.PENDING_CREATOR):
            raise ValidationError("target user is not a creator")

        previous_max_published_override = getattr(target, "max_published_puzzles", None)
        previous_max_unpublished_override = getattr(target, "max_unpublished_puzzles", None)
        previous_effective_max_published = None
        previous_effective_max_unpublished = None
        if hasattr(target, "get_puzzle_capacity"):
            previous_effective_max_published, previous_effective_max_unpublished = target.get_puzzle_capacity()

        if max_published is not None and max_published < 0:
            raise ValidationError("max_published cannot be negative")
        if max_unpublished is not None and max_unpublished < 0:
            raise ValidationError("max_unpublished cannot be negative")

        self.user_repo.update_puzzle_limits(target_user_id, max_published, max_unpublished)

        # Re-fetch to return current effective values
        updated = self.user_repo.get_by_id(target_user_id)
        eff_published, eff_unpublished = updated.get_puzzle_capacity()

        self.audit_log.create(
            admin_user_id=admin_id,
            action_type=AuditActionType.UPDATE_PUZZLE_LIMITS.value,
            target_user_id=target_user_id,
            details={
                "previous_max_published_override": previous_max_published_override,
                "previous_max_unpublished_override": previous_max_unpublished_override,
                "new_max_published_override": max_published,
                "new_max_unpublished_override": max_unpublished,
                "previous_effective_max_published": previous_effective_max_published,
                "previous_effective_max_unpublished": previous_effective_max_unpublished,
                "new_effective_max_published": eff_published,
                "new_effective_max_unpublished": eff_unpublished,
            },
        )

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

    def get_user_profile(self, session_token: str, user_id: int) -> dict:
        self._require_admin(session_token)

        target = self.user_repo.get_by_id(user_id)
        if not target:
            raise ValidationError("target user not found")

        d = target.to_dict()
        conn = self.user_repo.conn

        medal_rows = conn.execute(
            """
            SELECT best_medal, COUNT(*) AS count
            FROM puzzle_progress
            WHERE user_id = ?
            GROUP BY best_medal
            """,
            (int(user_id),),
        ).fetchall()
        medal_counts = {"bronze": 0, "silver": 0, "gold": 0}
        for row in medal_rows:
            best_medal = int(row["best_medal"])
            count = int(row["count"])
            if best_medal == 1:
                medal_counts["bronze"] += count
            elif best_medal == 2:
                medal_counts["silver"] += count
            elif best_medal == 3:
                medal_counts["gold"] += count
        d["medals"] = {
            **medal_counts,
            "total": medal_counts["bronze"] + medal_counts["silver"] + medal_counts["gold"],
        }

        saved_rows = conn.execute(
            """
            SELECT p.id, p.name, p.status, sp.created_at
            FROM saved_puzzles sp
            JOIN puzzles p ON p.id = sp.puzzle_id
            WHERE sp.user_id = ?
            ORDER BY sp.created_at DESC
            """,
            (int(user_id),),
        ).fetchall()
        d["saved_puzzles"] = [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "status": row["status"],
                "saved_at": row["created_at"],
            }
            for row in saved_rows
        ]

        created_rows = conn.execute(
            """
            SELECT id, name, status, created_at
            FROM puzzles
            WHERE creator_user_id = ?
            ORDER BY created_at DESC
            """,
            (int(user_id),),
        ).fetchall()
        d["created_puzzles"] = [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in created_rows
        ]

        d["is_online"] = int(user_id) in self._get_online_user_ids()

        d["arsenal"] = [
            {
                "id": str(piece.id),
                "name": piece.name,
                "cost": piece.cost,
                "is_arsenal": piece.is_arsenal,
                "num_inputs": piece.num_inputs,
                "num_outputs": piece.num_outputs,
                "basic_gates": piece.basic_gates,
                "truth_table": piece.truth_table,
                "structure_json": piece.structure_json,
                "description": piece.description,
            }
            for piece in (self.circuit_repo.list_arsenal_by_user(int(user_id)) if self.circuit_repo else [])
        ]

        return d

    def list_solving_attempts(
        self,
        session_token: str,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[int] = None,
        puzzle_id: Optional[int] = None,
        passed: Optional[bool] = None,
    ) -> dict:
        self._require_admin(session_token)
        data = self.solve_repo.list_attempts_for_admin(
            limit=limit,
            offset=offset,
            user_id=user_id,
            puzzle_id=puzzle_id,
            passed=passed,
        )
        total = self.solve_repo.count_attempts_for_admin(
            user_id=user_id,
            puzzle_id=puzzle_id,
            passed=passed,
        )
        return {
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def list_auth_attempts(
        self,
        session_token: str,
        limit: int = 100,
        offset: int = 0,
        action: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> List[dict]:
        self._require_admin(session_token)
        return self.user_repo.list_auth_attempts(
            limit=limit,
            offset=offset,
            action=action,
            success=success,
        )
