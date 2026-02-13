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
    def list_users(token: str = Depends(verify_token), limit: int = 200, offset: int = 0):
        try:
            return user_service.list_users(token, limit=limit, offset=offset)
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
    def get_notifications(token: str = Depends(verify_token)):
        if not notification_service:
            return []
        try:
            return notification_service.get_unread(token)
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
