from typing import List, Optional

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

        previous_role = target.role.value
        draft_count = 0

        # Wrap the entire read-draft-IDs + delete + role-demote in one
        # IMMEDIATE transaction to prevent TOCTOU (C6).
        with transaction(self.user_repo.conn) as txn:
            if target.role == UserRole.CREATOR:
                draft_puzzles = self.puzzle_repo.get_by_creator_and_status(
                    target_user_id, PuzzleStatus.DRAFT
                )
                draft_ids = [p.id for p in draft_puzzles]
                draft_count = len(draft_ids)
                if draft_ids:
                    self.solve_repo.delete_by_puzzle_ids(draft_ids)
                    for pid in draft_ids:
                        self.rating_repo.delete_by_puzzle(pid)
                    txn.execute(
                        "CREATE TABLE IF NOT EXISTS deleted_puzzle_names (name TEXT PRIMARY KEY)"
                    )
                    for p in draft_puzzles:
                        txn.execute(
                            "INSERT OR IGNORE INTO deleted_puzzle_names(name) VALUES(?)",
                            (p.name,),
                        )
                    self.puzzle_repo.delete_by_ids(draft_ids)

            changed = self.user_repo.update_role_if(target_user_id, UserRole.SOLVER, target.role)
            if not changed:
                raise ValidationError("user role was changed by another admin")
            # COMMIT at context-manager exit

        # Notify user
        self.notification_repo.create(
            user_id=target_user_id,
            notif_type="role_change",
            message="Your Creator role has been removed by an admin. You have been set back to Solver.",
        )

        # Audit log (req 7.5)
        self.audit_log.create(
            admin_user_id=admin_id,
            action_type=AuditActionType.REMOVE_CREATOR.value,
            target_user_id=target_user_id,
            details={
                "previous_role": previous_role,
                "draft_puzzles_deleted": draft_count,
            },
        )

        return {"ok": True, "new_role": UserRole.SOLVER.value}

    # ------------------------------------------------------------------ #
    #  REQ 7.4  —  Delete Any Puzzle
    # ------------------------------------------------------------------ #
    def delete_puzzle(self, session_token: str, puzzle_id: int) -> dict:
        admin_id = self._require_admin(session_token)

        puzzle = self.puzzle_repo.get_by_id(puzzle_id)
        if not puzzle:
            raise ValidationError("puzzle not found")

        puzzle_name = puzzle.name
        creator_id = puzzle.creator_user_id
        status = puzzle.status.value

        # Wrap cleanup + delete in one IMMEDIATE transaction so no
        # concurrent solve/rating can be inserted mid-delete (H5).
        with transaction(self.puzzle_repo.conn) as txn:
            self.solve_repo.delete_by_puzzle(puzzle_id)
            self.rating_repo.delete_by_puzzle(puzzle_id)
            self.puzzle_repo.delete(puzzle_id)
            txn.execute(
                "CREATE TABLE IF NOT EXISTS deleted_puzzle_names (name TEXT PRIMARY KEY)"
            )
            txn.execute(
                "INSERT OR IGNORE INTO deleted_puzzle_names(name) VALUES(?)",
                (puzzle_name,),
            )
            # COMMIT at context-manager exit

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
            creator = self.user_repo.get_by_id(p.creator_user_id)
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
