import sqlite3
from typing import Dict, Any, List, Optional

from Backend import settings

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
        email = (payload.get("email") or "").strip()
        
        if not username or not password:
            raise ValidationError("username and password required")
        if not email:
            raise ValidationError("email is required")
        if self.user_repo.get_by_username(username):
            raise ValidationError("username already exists")
        if self.user_repo.get_by_email(email):
            raise ValidationError("email already exists")

        # Domain objects require a truthy id; repo will replace it on insert.
        user = User(id=0, username=username, email=email, role=UserRole.SOLVER, xp=0)
        try:
            created = self.user_repo.create(user, password=password)
        except sqlite3.IntegrityError:
            # Concurrent registration with same username/email beat our check
            raise ValidationError("username or email already exists")
        self.user_repo.conn.commit()
        
        # Auto login
        token, _ = self.auth.login(username, password)

        d = created.to_dict()
        d["level"] = self.xp.calculate_level(created.xp)
        d["is_experienced"] = self.xp.is_experienced(created.xp)
        return {"token": token, "user": d}

    def login(self, payload: Dict[str, Any]) -> dict:
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        token, user = self.auth.login(username, password)

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

    def list_users(
        self,
        session_token: str,
        limit: int = settings.LIST_USERS_DEFAULT_LIMIT,
        offset: int = 0,
        username_search: Optional[str] = None,
        role: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_level: Optional[int] = None,
        max_level: Optional[int] = None,
        experience_level: str = "all",
        order_by: str = "created_at",
        order_direction: str = "DESC"
    ) -> dict:
        """List users with optional filters, ordering, and server-side pagination."""
        _ = self.auth.require_user_id(session_token)

        # Convert level ranges to xp ranges
        min_xp = None
        max_xp = None
        if min_level is not None or max_level is not None:
            if min_level is not None:
                min_xp = self.xp.calculate_xp_for_level(min_level) if hasattr(self.xp, 'calculate_xp_for_level') else (min_level - 1) * settings.LEVEL_XP_DIVISOR
            if max_level is not None:
                max_xp = self.xp.calculate_xp_for_level(max_level + 1) - 1 if hasattr(self.xp, 'calculate_xp_for_level') else (max_level * settings.LEVEL_XP_DIVISOR) + (settings.LEVEL_XP_DIVISOR - 1)

        filter_kwargs = dict(
            username_search=username_search, role=role,
            date_from=date_from, date_to=date_to,
            min_xp=min_xp, max_xp=max_xp,
            experience_level=experience_level,
        )

        users = self.user_repo.list_all(
            limit=limit, offset=offset,
            order_by=order_by, order_direction=order_direction,
            **filter_kwargs,
        )
        total = self.user_repo.count_all(**filter_kwargs)

        out = []
        for u in users:
            d = u.to_dict()
            d["level"] = self.xp.calculate_level(u.xp)
            d["is_experienced"] = self.xp.is_experienced(u.xp)
            out.append(d)

        return {"data": out, "total": total, "limit": limit, "offset": offset}

    def google_login(self, token: str) -> dict:
        """Verify a Google id_token, find-or-create the user, and return a session."""
        if not token:
            raise ValidationError("token is required")

        google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
        if not google_client_id:
            raise ValidationError("google_login_disabled")

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
            # User doesn't exist - need to set up password
            # Return info for frontend to redirect to password setup
            return {
                "requires_password": True,
                "email": email,
                "name": name,
                "token": token  # Pass token to complete registration later
            }

        # User exists - log in normally
        session_token = self.auth.login_external(user.id)

        d = user.to_dict()
        d["level"] = self.xp.calculate_level(user.xp)
        d["is_experienced"] = self.xp.is_experienced(user.xp)
        return {"token": session_token, "user": d}

    def google_complete_registration(self, payload: Dict[str, Any]) -> dict:
        """Complete Google registration by setting username and password.
        
        This is called when a user logs in with Google for the first time.
        If an account with the same email already exists, this links to that account
        instead of creating a new one.
        """
        token = payload.get("token") or ""
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""

        if not token:
            raise ValidationError("token is required")
        if not username or not password:
            raise ValidationError("username and password required")

        # Verify the Google token again
        google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
        if not google_client_id:
            raise ValidationError("google_login_disabled")

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

        # Check if user with this email already exists (link to existing account)
        existing_user = self.user_repo.get_by_email(email)
        if existing_user:
            # Link to existing account by logging in
            session_token = self.auth.login_external(existing_user.id)
            d = existing_user.to_dict()
            d["level"] = self.xp.calculate_level(existing_user.xp)
            d["is_experienced"] = self.xp.is_experienced(existing_user.xp)
            return {"token": session_token, "user": d}

        # Email doesn't exist yet. Check if username is available
        if self.user_repo.get_by_username(username):
            raise ValidationError("username already exists")

        # Create new user with username, email, and password
        new_user = User(id=0, username=username, email=email, role=UserRole.SOLVER, xp=0)
        try:
            user = self.user_repo.create(new_user, password=password)
        except sqlite3.IntegrityError:
            raise ValidationError("username or email already exists")
        self.user_repo.conn.commit()

        # Log in via trusted external path
        session_token = self.auth.login_external(user.id)

        d = user.to_dict()
        d["level"] = self.xp.calculate_level(user.xp)
        d["is_experienced"] = self.xp.is_experienced(user.xp)
        return {"token": session_token, "user": d}

    def accept_creator_role(self, session_token: str) -> dict:
        """User accepts the pending_creator invitation."""
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")
        if user.role != UserRole.PENDING_CREATOR:
            raise ValidationError("no pending creator invitation")

        # Atomic role update to prevent accept+decline race from two tabs
        changed = self.user_repo.update_role_if(user_id, UserRole.CREATOR, UserRole.PENDING_CREATOR)
        if not changed:
            raise ValidationError("no pending creator invitation")
        self.user_repo.conn.commit()

        d = user.to_dict()
        d["role"] = UserRole.CREATOR.value
        d["level"] = self.xp.calculate_level(user.xp)
        d["is_experienced"] = self.xp.is_experienced(user.xp)
        return {"ok": True, "new_role": UserRole.CREATOR.value, "user": d}

    def decline_creator_role(self, session_token: str) -> dict:
        """User declines the pending_creator invitation."""
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")
        if user.role != UserRole.PENDING_CREATOR:
            raise ValidationError("no pending creator invitation")

        # Atomic role update to prevent accept+decline race from two tabs
        changed = self.user_repo.update_role_if(user_id, UserRole.SOLVER, UserRole.PENDING_CREATOR)
        if not changed:
            raise ValidationError("no pending creator invitation")
        self.user_repo.conn.commit()

        d = user.to_dict()
        d["role"] = UserRole.SOLVER.value
        d["level"] = self.xp.calculate_level(user.xp)
        d["is_experienced"] = self.xp.is_experienced(user.xp)
        return {"ok": True, "new_role": UserRole.SOLVER.value, "user": d}

    def delete_user(self, session_token: str, target_user_id: int) -> dict:
        """Admin-only: delete a user by ID."""
        admin_id = self.auth.require_user_id(session_token)
        admin = self.user_repo.get_by_id(admin_id)
        if not admin or admin.role != UserRole.ADMIN:
            raise ValidationError("admin required")
        if target_user_id == admin_id:
            raise ValidationError("cannot delete yourself")

        target = self.user_repo.get_by_id(target_user_id)
        if not target:
            raise ValidationError("user not found")

        deleted = self.user_repo.delete(target_user_id)
        self.user_repo.conn.commit()
        if not deleted:
            raise ValidationError("user not found")
        return {"ok": True}

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
        self.user_repo.conn.commit()
        return {"ok": True}
