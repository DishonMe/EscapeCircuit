from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from Backend.PersistantLayer.DraftRepo import DraftRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.APILayer.auth_utils import verify_token


class SaveDraftReq(BaseModel):
    state_json: str
    expected_updated_at: Optional[float] = None


def build_draft_router(draft_repo: DraftRepo, auth_service: AuthService) -> APIRouter:
    router = APIRouter(prefix="/puzzles", tags=["drafts"])

    @router.put("/{puzzle_id}/draft")
    def save_draft(puzzle_id: int, req: SaveDraftReq, token: str = Depends(verify_token)):
        user_id = auth_service.require_user_id(token)
        try:
            result = draft_repo.upsert(
                user_id, puzzle_id, req.state_json,
                expected_updated_at=req.expected_updated_at,
            )
        except ValueError:
            return JSONResponse(
                status_code=409,
                content={"detail": "Draft was modified in another session. Reload to get latest."},
            )
        return {"ok": True, "updated_at": result["updated_at"]}

    @router.get("/{puzzle_id}/draft")
    def get_draft(puzzle_id: int, token: str = Depends(verify_token)):
        user_id = auth_service.require_user_id(token)
        draft = draft_repo.get(user_id, puzzle_id)
        if not draft:
            return {"state_json": None, "updated_at": None}
        return draft

    @router.delete("/{puzzle_id}/draft")
    def delete_draft(puzzle_id: int, token: str = Depends(verify_token)):
        user_id = auth_service.require_user_id(token)
        draft_repo.delete(user_id, puzzle_id)
        return {"ok": True}

    return router
