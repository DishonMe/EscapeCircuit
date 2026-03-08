from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.RatingService import RatingService
from Backend.APILayer.auth_utils import verify_token


class RateReq(BaseModel):
    difficulty: int
    fun: int
    clearness: int
    elapsed_seconds: Optional[int] = None


def build_rating_router(rating_service: RatingService) -> APIRouter:
    router = APIRouter(prefix="/ratings", tags=["ratings"])

    @router.get("/puzzle/{puzzle_id}")
    def get_ratings(puzzle_id: int, token: str = Depends(verify_token)):
        """Return metrics + the current user's rating for a puzzle."""
        try:
            metrics = rating_service.get_puzzle_metrics(puzzle_id)
            my_rating = rating_service.get_my_rating(token, puzzle_id)
            return {
                "metrics": metrics,
                "my_rating": my_rating,
            }
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/puzzle/{puzzle_id}")
    def rate(puzzle_id: int, req: RateReq, token: str = Depends(verify_token)):
        try:
            payload = req.model_dump()
            return rating_service.submit_rating(token, puzzle_id, payload)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.put("/puzzle/{puzzle_id}")
    def update_rating(puzzle_id: int, req: RateReq, token: str = Depends(verify_token)):
        try:
            payload = req.model_dump()
            return rating_service.update_rating(token, puzzle_id, payload)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.delete("/puzzle/{puzzle_id}")
    def delete_rating(puzzle_id: int, token: str = Depends(verify_token)):
        """Remove the current user's rating for a puzzle."""
        try:
            ok = rating_service.remove_rating(token, puzzle_id)
            if not ok:
                raise HTTPException(status_code=404, detail="rating not found")
            return {"deleted": True}
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
