from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.UserService import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


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
            raise HTTPException(status_code=401, detail=str(e))

    @router.post("/logout")
    def logout(token: str = Depends(oauth2_scheme)):
        try:
            return user_service.logout(token)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.get("/me")
    def me(token: str = Depends(oauth2_scheme)):
        try:
            return user_service.me(token)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.get("")
    def list_users(token: str = Depends(oauth2_scheme), limit: int = 200, offset: int = 0):
        try:
            return user_service.list_users(token, limit=limit, offset=offset)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.post("/role")
    def set_role(req: SetRoleReq, token: str = Depends(oauth2_scheme)):
        try:
            return user_service.set_role(token, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

    return router
