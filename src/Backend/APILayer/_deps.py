from fastapi import Header
from Backend.DomainLayer.Exceptions import ValidationError

def require_session_token():
    async def _dep(authorization: str = Header(default="")) -> str:
        if not authorization.startswith("Bearer "):
            raise ValidationError("unauthorized")
        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            raise ValidationError("unauthorized")
        return token
    return _dep
