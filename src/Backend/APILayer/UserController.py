from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.UserService import UserService
from Backend.APILayer.auth_utils import verify_token


class RegisterReq(BaseModel):
    username: str
    password: str
    email: str = ""


class LoginReq(BaseModel):
    username: str
    password: str


class SetRoleReq(BaseModel):
    target_user_id: int
    role: str  # "admin"/"creator"/"solver"


class UpdatePuzzleLimitsReq(BaseModel):
    max_published: Optional[int] = None
    max_unpublished: Optional[int] = None


def build_user_router(user_service: UserService) -> APIRouter:
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

    @router.patch("/{user_id}/puzzle-limits")
    def update_puzzle_limits(user_id: int, req: UpdatePuzzleLimitsReq, token: str = Depends(verify_token)):
        try:
            return user_service.update_puzzle_limits(token, user_id, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

    return router
