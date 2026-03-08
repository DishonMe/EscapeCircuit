from typing import Dict, Any, List

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole

from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService


class UserService:
    """
    Controller talks only to UserService.
    UserService internally uses AuthService + UserRepo + XPService.
    """

    def __init__(self, user_repo: UserRepo, auth_service: AuthService, xp_service: XPService):
        self.user_repo = user_repo
        self.auth = auth_service
        self.xp = xp_service

    def register(self, payload: Dict[str, Any]) -> dict:
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        if not username or not password:
            raise ValidationError("username and password required")
        if self.user_repo.get_by_username(username):
            raise ValidationError("username already exists")

        # Domain objects require a truthy id; repo will replace it on insert.
        user = User(id="0", username=username, role=UserRole.SOLVER, xp=0)
        created = self.user_repo.create(user, password=password)
        
        # Auto login
        token = self.auth.login(username, password)

        d = created.to_dict()
        d["level"] = self.xp.calculate_level(created.xp)
        d["is_experienced"] = self.xp.is_experienced(created.xp)
        return {"token": token, "user": d}

    def login(self, payload: Dict[str, Any]) -> dict:
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        token = self.auth.login(username, password)
        user = self.user_repo.get_by_username(username)
        
        d = user.to_dict()
        d["level"] = self.xp.calculate_level(user.xp)
        d["is_experienced"] = self.xp.is_experienced(user.xp)
        
        return {"token": token, "user": d}

    def logout(self, session_token: str) -> dict:
        # auth called for every service action:
        _ = self.auth.require_user_id(session_token)
        self.auth.logout(session_token)
        return {"ok": True}

    def me(self, session_token: str) -> dict:
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")
        d = user.to_dict()
        d["level"] = self.xp.calculate_level(user.xp)
        d["is_experienced"] = self.xp.is_experienced(user.xp)
        d["effective_published_limit"] = self.xp.get_puzzle_published_limit(user.xp, user.puzzle_limit_published)
        d["effective_unpublished_limit"] = self.xp.get_puzzle_unpublished_limit(user.xp, user.puzzle_limit_unpublished)
        return d

    def list_users(self, session_token: str, limit: int = 200, offset: int = 0) -> List[dict]:
        _ = self.auth.require_user_id(session_token)
        users = self.user_repo.list_all(limit=limit, offset=offset)
        out = []
        for u in users:
            d = u.to_dict()
            d["level"] = self.xp.calculate_level(u.xp)
            d["is_experienced"] = self.xp.is_experienced(u.xp)
            d["effective_published_limit"] = self.xp.get_puzzle_published_limit(u.xp, u.puzzle_limit_published)
            d["effective_unpublished_limit"] = self.xp.get_puzzle_unpublished_limit(u.xp, u.puzzle_limit_unpublished)
            out.append(d)
        return out

    def set_role(self, session_token: str, payload: Dict[str, Any]) -> dict:
        admin_id = self.auth.require_user_id(session_token)
        admin = self.user_repo.get_by_id(admin_id)
        if not admin or admin.role != UserRole.ADMIN:
            raise ValidationError("admin required")

        target_user_id = int(payload.get("target_user_id", 0))
        role_raw = payload.get("role")
        if target_user_id <= 0:
            raise ValidationError("target_user_id required")
        if not role_raw:
            raise ValidationError("role required")

        role = UserRole(role_raw)
        self.user_repo.update_role(target_user_id, role)
        return {"ok": True}

    def update_puzzle_limits(self, session_token: str, target_user_id: int, payload: Dict[str, Any]) -> dict:
        """Admin-only: update the max published/unpublished puzzle overrides for a user.

        ``max_published`` and ``max_unpublished`` must be non-negative integers.
        Passing ``None`` for either resets it to the level-based default.
        """
        admin_id = self.auth.require_user_id(session_token)
        admin = self.user_repo.get_by_id(admin_id)
        if not admin or admin.role != UserRole.ADMIN:
            raise ValidationError("admin required")

        target = self.user_repo.get_by_id(target_user_id)
        if not target:
            raise ValidationError("user not found")

        max_published = payload.get("max_published")
        max_unpublished = payload.get("max_unpublished")

        if max_published is not None:
            if not isinstance(max_published, int) or max_published < 0:
                raise ValidationError("max_published must be a non-negative integer")
        if max_unpublished is not None:
            if not isinstance(max_unpublished, int) or max_unpublished < 0:
                raise ValidationError("max_unpublished must be a non-negative integer")

        self.user_repo.update_puzzle_limits(target_user_id, max_published, max_unpublished)

        # Return updated effective limits alongside the raw overrides
        updated = self.user_repo.get_by_id(target_user_id)
        pub_limit = self.xp.get_puzzle_published_limit(updated.xp, updated.puzzle_limit_published)
        unpub_limit = self.xp.get_puzzle_unpublished_limit(updated.xp, updated.puzzle_limit_unpublished)
        return {
            "ok": True,
            "puzzle_limit_published": updated.puzzle_limit_published,
            "puzzle_limit_unpublished": updated.puzzle_limit_unpublished,
            "effective_published_limit": pub_limit,
            "effective_unpublished_limit": unpub_limit,
        }
