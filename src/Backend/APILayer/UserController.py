from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.UserService import UserService
from Backend.ServiceLayer.NotificationService import NotificationService
from Backend.APILayer.auth_utils import verify_token


class RegisterReq(BaseModel):
    username: str
    password: str
    email: str = ""


class LoginReq(BaseModel):
    username: str
    password: str


class GoogleLoginReq(BaseModel):
    token: str


class GoogleCompleteRegistrationReq(BaseModel):
    token: str
    username: str
    password: str


class SetRoleReq(BaseModel):
    target_user_id: int
    role: str  # "admin"/"creator"/"solver"


def build_user_router(user_service: UserService, notification_service: NotificationService = None) -> APIRouter:
    router = APIRouter(prefix="/users", tags=["users"])

    @router.post("/register")
    def register(req: RegisterReq):
        try:
            return user_service.register(req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/login")
    def login(req: LoginReq):
        try:
            return user_service.login(req.model_dump())
        except ValidationError as e:
            if str(e) == "user not found":
                raise HTTPException(status_code=404, detail="User not found. Please register.")
            else:
                raise HTTPException(status_code=401, detail=str(e))

    @router.post("/google-login")
    def google_login(req: GoogleLoginReq):
        try:
            return user_service.google_login(req.token)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.post("/google-complete-registration")
    def google_complete_registration(req: GoogleCompleteRegistrationReq):
        try:
            return user_service.google_complete_registration(req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/logout")
    def logout(token: str = Depends(verify_token)):
        try:
            return user_service.logout(token)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.get("/me")
    def me(token: str = Depends(verify_token)):
        try:
            return user_service.me(token)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.get("")
    def list_users(
        token: str = Depends(verify_token), 
        limit: int = 200, 
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
    ):
        try:
            users = user_service.list_users(
                token, 
                limit=limit, 
                offset=offset,
                username_search=username_search,
                role=role,
                date_from=date_from,
                date_to=date_to,
                min_level=min_level,
                max_level=max_level,
                experience_level=experience_level,
                order_by=order_by,
                order_direction=order_direction
            )
            return {"data": users}
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.post("/role")
    def set_role(req: SetRoleReq, token: str = Depends(verify_token)):
        try:
            return user_service.set_role(token, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

    # --- Creator Notifications ---
    @router.get("/me/notifications")
    def get_notifications(
        token: str = Depends(verify_token),
        notif_type: Optional[str] = None,
        puzzle_name: Optional[str] = None,
        actor_username: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
        limit: Optional[int] = None,
        offset: int = 0
    ):
        if not notification_service:
            return []
        try:
            return notification_service.get_unread(
                token,
                notif_type=notif_type,
                puzzle_name=puzzle_name,
                actor_username=actor_username,
                date_from=date_from,
                date_to=date_to,
                order_by=order_by,
                order_direction=order_direction,
                limit=limit,
                offset=offset
            )
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.get("/me/notifications/history")
    def get_notifications_history(
        token: str = Depends(verify_token),
        notif_type: Optional[str] = None,
        puzzle_name: Optional[str] = None,
        actor_username: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
        limit: Optional[int] = None,
        offset: int = 0
    ):
        if not notification_service:
            return []
        try:
            return notification_service.get_all(
                token,
                notif_type=notif_type,
                puzzle_name=puzzle_name,
                actor_username=actor_username,
                date_from=date_from,
                date_to=date_to,
                order_by=order_by,
                order_direction=order_direction,
                limit=limit,
                offset=offset
            )
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.patch("/me/notifications/read")
    def mark_notifications_read(token: str = Depends(verify_token)):
        if not notification_service:
            return {"marked_read": 0}
        try:
            return notification_service.mark_all_read(token)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    return router
