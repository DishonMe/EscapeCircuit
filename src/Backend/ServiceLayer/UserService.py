from typing import Dict, Any, List

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

import os

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
        user = User(id=0, username=username, role=UserRole.SOLVER, xp=0)
        created = self.user_repo.create(user, password=password)
        self.user_repo.conn.commit()
        
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
        return d

    def list_users(self, session_token: str, limit: int = 200, offset: int = 0) -> List[dict]:
        _ = self.auth.require_user_id(session_token)
        users = self.user_repo.list_all(limit=limit, offset=offset)
        out = []
        for u in users:
            d = u.to_dict()
            d["level"] = self.xp.calculate_level(u.xp)
            d["is_experienced"] = self.xp.is_experienced(u.xp)
            out.append(d)
        return out

    def google_login(self, token: str) -> dict:
        """Verify a Google id_token, find-or-create the user, and return a session."""
        if not token:
            raise ValidationError("token is required")

        google_client_id = os.environ.get(
            "GOOGLE_CLIENT_ID",
            "138879283241-0kfmc6auoir4a5ao9btos3hhklgee1jm.apps.googleusercontent.com",
        )

        try:
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), audience=google_client_id
            )
        except Exception as e:
            raise ValidationError(f"invalid google token: {e}")

        email = idinfo.get("email")
        name = idinfo.get("name", "")
        if not email:
            raise ValidationError("google token missing email")

        # Look up existing user by email
        user = self.user_repo.get_by_email(email)

        if not user:
            # Pick a unique username (Google name may collide with existing usernames)
            base_username = name or email.split("@")[0]
            username = base_username
            counter = 1
            while self.user_repo.get_by_username(username):
                username = f"{base_username}_{counter}"
                counter += 1

            # Create a new SOLVER user (no password)
            new_user = User(id=0, username=username, email=email, role=UserRole.SOLVER, xp=0)
            user = self.user_repo.create(new_user, password=None)

        # Log in via trusted external path (no password check)
        session_token = self.auth.login_external(user.id)

        d = user.to_dict()
        d["level"] = self.xp.calculate_level(user.xp)
        d["is_experienced"] = self.xp.is_experienced(user.xp)
        return {"token": session_token, "user": d}

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
