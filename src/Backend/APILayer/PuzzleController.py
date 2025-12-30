from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Dict, Optional

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.PuzzleService import PuzzleService
from Backend.ServiceLayer.SolvingService import SolvingService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


class CreatePuzzleReq(BaseModel):
    name: str
    description: str = ""
    budget: int = 0
    time_limit_seconds: Optional[int] = None
    default_gate_set: list[str] = []


class AddTestCaseReq(BaseModel):
    kind: str
    inputs: Dict[str, int]
    expected_outputs: Dict[str, int]


class SolveReq(BaseModel):
    circuit_id: int


def build_puzzle_router(puzzle_service: PuzzleService, solving_service: SolvingService) -> APIRouter:
    router = APIRouter(prefix="/puzzles", tags=["puzzles"])

    @router.get("")
    def browse(limit: int = 50, offset: int = 0, token: str = Depends(oauth2_scheme)):
        try:
            return puzzle_service.browse(token, limit=limit, offset=offset)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.get("/search")
    def search(q: str, token: str = Depends(oauth2_scheme)):
        try:
            return puzzle_service.search(token, q)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.get("/{puzzle_id}")
    def get_one(puzzle_id: int, token: str = Depends(oauth2_scheme)):
        try:
            return puzzle_service.get(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("")
    def create(req: CreatePuzzleReq, token: str = Depends(oauth2_scheme)):
        try:
            return puzzle_service.create_puzzle(token, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{puzzle_id}/publish")
    def publish(puzzle_id: int, token: str = Depends(oauth2_scheme)):
        try:
            return puzzle_service.publish(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @router.post("/{puzzle_id}/unpublish")
    def unpublish(puzzle_id: int, token: str = Depends(oauth2_scheme)):
        try:
            return puzzle_service.unpublish(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @router.post("/{puzzle_id}/testcases")
    def add_testcase(puzzle_id: int, req: AddTestCaseReq, token: str = Depends(oauth2_scheme)):
        try:
            return puzzle_service.add_test_case(token, puzzle_id, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{puzzle_id}/testcases")
    def list_testcases(puzzle_id: int, token: str = Depends(oauth2_scheme)):
        try:
            return puzzle_service.list_test_cases(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{puzzle_id}/attempts/start")
    def start_attempt(puzzle_id: int, token: str = Depends(oauth2_scheme)):
        try:
            return solving_service.start_attempt(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{puzzle_id}/solve")
    def solve(puzzle_id: int, req: SolveReq, token: str = Depends(oauth2_scheme)):
        try:
            return solving_service.submit_solution(token, puzzle_id, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
