from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, Any, Union, List

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.PuzzleService import PuzzleService
from Backend.ServiceLayer.SolvingService import SolvingService
from Backend.ServiceLayer.RatingService import RatingService
from Backend.APILayer.auth_utils import verify_token


class CreatePuzzleReq(BaseModel):
    name: str = "" # maps to title
    title: str = "" # also accept title directly
    description: str = ""
    budget: int = 0
    time_limit_seconds: Optional[int] = None
    timeLimit: Optional[int] = None # alias
    default_gate_set: list[str] = []
    difficulty: str = "EASY"

    def to_backend_dict(self):
        return {
            "name": self.title if self.title else self.name,
            "description": self.description,
            "budget": self.budget,
            "time_limit_seconds": self.timeLimit if self.timeLimit is not None else self.time_limit_seconds,
            "default_gate_set": self.default_gate_set,
            "difficulty": self.difficulty
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


class SimulateReq(BaseModel):
    solution: Dict[str, Any]
    inputs: Union[Dict[str, int], List[Dict[str, int]], Dict[str, List[int]]]
    isSequence: Optional[bool] = None


def build_puzzle_router(puzzle_service: PuzzleService, solving_service: SolvingService, rating_service: RatingService | None = None) -> APIRouter:
    router = APIRouter(prefix="/puzzles", tags=["puzzles"])

    def _inject_rating_metrics(puzzle_dict: dict) -> dict:
        """Inject rating_metrics into a puzzle dict if rating_service is available."""
        if not rating_service:
            return puzzle_dict
        try:
            pid = puzzle_dict.get("id")
            if pid is not None:
                metrics = rating_service.get_puzzle_metrics(int(pid))
                puzzle_dict["rating_metrics"] = metrics
        except Exception:
            pass
        return puzzle_dict

    @router.get("")
    def browse(
        limit: int = 50, 
        offset: int = 0, 
        page: Optional[int] = None,
        search: Optional[str] = None,
        creator_id: Optional[int] = None,
        min_difficulty: Optional[float] = None,
        max_difficulty: Optional[float] = None,
        only_experienced_difficulty: bool = False,
        min_clearness: Optional[float] = None,
        max_clearness: Optional[float] = None,
        only_experienced_clearness: bool = False,
        min_fun: Optional[float] = None,
        max_fun: Optional[float] = None,
        only_experienced_fun: bool = False,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
        order_only_experienced: bool = False,
        token: str = Depends(verify_token)
    ):
        try:
            # Handle pagination logic if page is provided
            if page is not None and page > 0:
                offset = (page - 1) * limit
                
            result = puzzle_service.browse(
                token, 
                limit=limit, 
                offset=offset,
                search=search,
                creator_id=creator_id,
                min_difficulty=min_difficulty,
                max_difficulty=max_difficulty,
                only_experienced_difficulty=only_experienced_difficulty,
                min_clearness=min_clearness,
                max_clearness=max_clearness,
                only_experienced_clearness=only_experienced_clearness,
                min_fun=min_fun,
                max_fun=max_fun,
                only_experienced_fun=only_experienced_fun,
                date_from=date_from,
                date_to=date_to,
                order_by=order_by,
                order_direction=order_direction,
                order_only_experienced=order_only_experienced
            )

            # Inject is_solved status per puzzle for the current user
            try:
                from Backend.ServiceLayer.AuthService import AuthService
                user_id = puzzle_service.auth.require_user_id(token)
                if puzzle_service.solve_repo:
                    status_map = puzzle_service.solve_repo.get_solve_status_map(user_id)
                    solved_counts = puzzle_service.solve_repo.get_solved_counts()
                    for p in result.get("data", []):
                        pid = p.get("id")
                        try:
                            pid = int(pid)
                        except (TypeError, ValueError):
                            pid = None
                        # Per-user solved status
                        if pid and pid in status_map:
                            p["is_solved"] = True
                            p["best_time"] = status_map[pid].get("best_time")
                            p["total_xp"] = status_map[pid].get("total_xp", 0)
                            p["best_medal"] = status_map[pid].get("best_medal", 0)
                        else:
                            p["is_solved"] = False
                            p["best_medal"] = 0
                        # Global solved count (all users)
                        p["solvedCount"] = solved_counts.get(pid, 0) if pid else 0
                        # Can-rate flag (solved OR 5 min spent)
                        if pid and rating_service:
                            try:
                                p["can_rate"] = rating_service._can_rate(user_id, pid)
                            except Exception:
                                p["can_rate"] = p.get("is_solved", False)
                        else:
                            p["can_rate"] = p.get("is_solved", False)
                        # Inject rating metrics
                        _inject_rating_metrics(p)
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
            result = puzzle_service.get(token, puzzle_id)
            _inject_rating_metrics(result)

            # Inject per-user solve status (same as browse does)
            try:
                user_id = puzzle_service.auth.require_user_id(token)
                if puzzle_service.solve_repo:
                    is_passed = puzzle_service.solve_repo.has_passed(user_id, puzzle_id)
                    result["is_solved"] = is_passed
                    if is_passed:
                        status_map = puzzle_service.solve_repo.get_solve_status_map(user_id)
                        info = status_map.get(puzzle_id, {})
                        result["best_time"] = info.get("best_time")
                        result["total_xp"] = info.get("total_xp", 0)
                        result["best_medal"] = info.get("best_medal", 0)
                    else:
                        result["best_medal"] = 0
                    # Can-rate flag (solved OR 5 min spent)
                    if rating_service:
                        try:
                            result["can_rate"] = rating_service._can_rate(user_id, puzzle_id)
                        except Exception:
                            result["can_rate"] = is_passed
                    else:
                        result["can_rate"] = is_passed
            except Exception:
                pass

            return result
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

    @router.post("/{puzzle_id}/simulate")
    def simulate(puzzle_id: int, req: SimulateReq, token: str = Depends(verify_token)):
        try:
            # Determine if it's a sequence simulation
            is_sequence = req.isSequence if req.isSequence is not None else (
                isinstance(req.inputs, dict) and 
                any(isinstance(v, list) for v in req.inputs.values())
            )
            return solving_service.simulate_solution(token, puzzle_id, req.solution, req.inputs, is_sequence=is_sequence)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
