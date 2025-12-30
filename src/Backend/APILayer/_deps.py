from fastapi import Header
from Backend.DomainLayer.Exceptions import ValidationError

from Backend.ServiceLayer.AuthService import AuthService


def require_user(auth: AuthService):
    async def _dep(authorization: str = Header(default="")):
        if not authorization.startswith("Bearer "):
            raise ValidationError("unauthorized")
        token = authorization.removeprefix("Bearer ").strip()
        return auth.require_user(token)
    return _dep
