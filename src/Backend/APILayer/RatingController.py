from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.RatingService import RatingService
from Backend.APILayer.auth_utils import verify_token


class RateReq(BaseModel):
    difficulty: int
    fun: int
    clearness: int


def build_rating_router(rating_service: RatingService) -> APIRouter:
    router = APIRouter(prefix="/ratings", tags=["ratings"])

    @router.get("/puzzle/{puzzle_id}")
    def list_for_puzzle(puzzle_id: int, token: str = Depends(verify_token)):
        try:
            return rating_service.list_ratings(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/puzzle/{puzzle_id}")
    def rate(puzzle_id: int, req: RateReq, token: str = Depends(verify_token)):
        try:
            return rating_service.submit_rating(token, puzzle_id, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
