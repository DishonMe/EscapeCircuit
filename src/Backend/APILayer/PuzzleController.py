from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, Any

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.PuzzleService import PuzzleService
from Backend.ServiceLayer.SolvingService import SolvingService
from Backend.APILayer.auth_utils import verify_token


class CreatePuzzleReq(BaseModel):
    name: str = "" # maps to title
    title: str = "" # also accept title directly
    description: str = ""
    budget: int = 0
    time_limit_seconds: Optional[int] = None
    timeLimit: Optional[int] = None # alias
    default_gate_set: list[str] = []

    def to_backend_dict(self):
        return {
            "name": self.title if self.title else self.name,
            "description": self.description,
            "budget": self.budget,
            "time_limit_seconds": self.timeLimit if self.timeLimit is not None else self.time_limit_seconds,
            "default_gate_set": self.default_gate_set
        }


class AddTestCaseReq(BaseModel):
    kind: str
    inputs: Dict[str, int]
    expected_outputs: Dict[str, int]


class SolveReq(BaseModel):
    circuit_id: int


class ValidateSolutionReq(BaseModel):
    solution: Dict[str, Any]
    time_taken: int = 0


def build_puzzle_router(puzzle_service: PuzzleService, solving_service: SolvingService) -> APIRouter:
    router = APIRouter(prefix="/puzzles", tags=["puzzles"])

    @router.get("")
    def browse(
        limit: int = 50, 
        offset: int = 0, 
        page: Optional[int] = None, 
        token: str = Depends(verify_token)
    ):
        try:
            # Handle pagination logic if page is provided
            if page is not None and page > 0:
                offset = (page - 1) * limit
                
            result = puzzle_service.browse(token, limit=limit, offset=offset)

            # Inject is_solved status per puzzle for the current user
            try:
                from Backend.ServiceLayer.AuthService import AuthService
                user_id = puzzle_service.auth.require_user_id(token)
                if puzzle_service.solve_repo:
                    status_map = puzzle_service.solve_repo.get_solve_status_map(user_id)
                    for p in result.get("data", []):
                        pid = p.get("id")
                        try:
                            pid = int(pid)
                        except (TypeError, ValueError):
                            pid = None
                        if pid and pid in status_map:
                            p["is_solved"] = True
                            p["best_time"] = status_map[pid].get("best_time")
                            p["total_xp"] = status_map[pid].get("total_xp", 0)
                        else:
                            p["is_solved"] = False
            except Exception:
                pass  # gracefully degrade if solve_repo unavailable

            return result
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.get("/search")
    def search(q: str, token: str = Depends(verify_token)):
        try:
            return puzzle_service.search(token, q)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.get("/{puzzle_id}")
    def get_one(puzzle_id: int, token: str = Depends(verify_token)):
        try:
            return puzzle_service.get(token, puzzle_id)
        except ValidationError as e:
            print(f"DEBUG: Controller caught ValidationError: {e}")
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("")
    def create(req: CreatePuzzleReq, token: str = Depends(verify_token)):
        try:
            # Transform req
            data = req.to_backend_dict()
            return puzzle_service.create_puzzle(token, data)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{puzzle_id}/publish")
    def publish(puzzle_id: int, token: str = Depends(verify_token)):
        try:
            return puzzle_service.publish(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @router.post("/{puzzle_id}/unpublish")
    def unpublish(puzzle_id: int, token: str = Depends(verify_token)):
        try:
            return puzzle_service.unpublish(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @router.post("/{puzzle_id}/testcases")
    def add_testcase(puzzle_id: int, req: AddTestCaseReq, token: str = Depends(verify_token)):
        try:
            return puzzle_service.add_test_case(token, puzzle_id, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{puzzle_id}/testcases")
    def list_testcases(puzzle_id: int, token: str = Depends(verify_token)):
        try:
            return puzzle_service.list_test_cases(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{puzzle_id}/attempts/start")
    def start_attempt(puzzle_id: int, token: str = Depends(verify_token)):
        try:
            return solving_service.start_attempt(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{puzzle_id}/solve")
    def solve(puzzle_id: int, req: SolveReq, token: str = Depends(verify_token)):
        try:
            return solving_service.submit_solution(token, puzzle_id, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{puzzle_id}/validate")
    def validate(puzzle_id: int, req: ValidateSolutionReq, token: str = Depends(verify_token)):
        try:
            return solving_service.validate_solution(token, puzzle_id, req.solution, time_taken=req.time_taken)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
