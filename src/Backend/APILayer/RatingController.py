from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.RatingService import RatingService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


class RateReq(BaseModel):
    difficulty: int
    fun: int
    clearness: int


def build_rating_router(rating_service: RatingService) -> APIRouter:
    router = APIRouter(prefix="/ratings", tags=["ratings"])

    @router.get("/puzzle/{puzzle_id}")
    def list_for_puzzle(puzzle_id: int, token: str = Depends(oauth2_scheme)):
        try:
            return rating_service.list_ratings(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/puzzle/{puzzle_id}")
    def rate(puzzle_id: int, req: RateReq, token: str = Depends(oauth2_scheme)):
        try:
            return rating_service.submit_rating(token, puzzle_id, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
