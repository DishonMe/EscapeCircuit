from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, Any, Union, List

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.PuzzleService import PuzzleService
from Backend.ServiceLayer.SolvingService import SolvingService
from Backend.ServiceLayer.RatingService import RatingService
from Backend.ServiceLayer.AdminService import AdminService
from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.APILayer.auth_utils import verify_token
from Backend.PersistantLayer._db import connect
from insert_riddles import insert_riddle
import shutil
import tempfile
import pathlib
import json
from fastapi import UploadFile, File, Form


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


def get_db_conn():
    """Helper to get a fresh connection for the puzzle creation."""
    current_file = pathlib.Path(__file__).resolve()
    root_dir = current_file.parent.parent.parent.parent
    db_path = root_dir / 'escape_circuit.db'
    if not db_path.exists():
        print(f"CRITICAL ERROR: Database file not found at {db_path}")
    conn = connect(str(db_path))
    return conn


def build_puzzle_router(puzzle_service: PuzzleService, solving_service: SolvingService, rating_service: RatingService | None = None, admin_service: AdminService | None = None) -> APIRouter:
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

    # ------------------------------------------------------------------ #
    #  Create puzzle from form (available to admins and creators)
    # ------------------------------------------------------------------ #
    @router.post("/create-puzzle-form")
    async def create_puzzle_form(
        config_file: UploadFile = File(...),
        instructions_file: UploadFile = File(...),
        sample_solution_file: UploadFile = File(...),
        difficulty: str = Form("EASY"),
        token: str = Depends(verify_token),
    ):
        # Verify admin or creator
        if not admin_service:
            raise HTTPException(status_code=500, detail="Admin service not available")
        
        try:
            user_id = admin_service._require_admin_or_creator(token)
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

        conn = get_db_conn()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                current_file = pathlib.Path(__file__).resolve()
                root_dir = current_file.parent.parent.parent.parent
                riddles_dir = root_dir / 'riddles'
                if not riddles_dir.exists():
                    riddles_dir.mkdir(parents=True)

                def save_file_to_riddles(upload_file):
                    dest_path = riddles_dir / upload_file.filename
                    with open(dest_path, "wb") as buffer:
                        shutil.copyfileobj(upload_file.file, buffer)
                    return str(dest_path)

                config_path = save_file_to_riddles(config_file)
                instructions_path = save_file_to_riddles(instructions_file)
                solution_path = save_file_to_riddles(sample_solution_file)

                with open(config_path, 'r', encoding='utf-8') as cf:
                    config_data = json.load(cf)
                
                # Validate config structure
                puzzle_config = config_data.get('puzzle', {})
                if not puzzle_config:
                    raise ValidationError("Config missing 'puzzle' section")
                if not puzzle_config.get('name'):
                    raise ValidationError("Puzzle name is required")
                if not puzzle_config.get('inputs') or not isinstance(puzzle_config['inputs'], list):
                    raise ValidationError("Puzzle must have 'inputs' list")
                if not puzzle_config.get('outputs') or not isinstance(puzzle_config['outputs'], list):
                    raise ValidationError("Puzzle must have 'outputs' list")
                if not puzzle_config.get('default_gate_set'):
                    raise ValidationError("Puzzle must have 'default_gate_set'")
                
                test_cases = config_data.get('test_cases', [])
                if not test_cases:
                    raise ValidationError("Puzzle must have at least one test case")
                
                # Load and validate sample solution using logic engine
                with open(solution_path, 'r', encoding='utf-8') as sf:
                    solution_data = json.load(sf)
                
                if not isinstance(solution_data.get('eval_map'), dict):
                    raise ValidationError("Sample solution must have 'eval_map' field")
                
                puzzle_inputs = puzzle_config.get('inputs', [])
                puzzle_outputs = puzzle_config.get('outputs', [])
                eval_map = solution_data.get('eval_map', {})
                
                # Validate all functional test cases can be evaluated
                logic_engine = logicEngineService()
                for i, test_case in enumerate(test_cases):
                    # Skip validation for constraint test cases (non-functional)
                    kind = test_case.get('kind', 'blackbox')
                    if kind in ('gate_limit', 'gate_count_limit', 'latency_limit'):
                        # These are constraint specs, not functional test cases - no need to validate
                        continue
                    
                    inputs = test_case.get('inputs', {})
                    expected_outputs = test_case.get('expected_outputs', {})
                    input_stream = test_case.get('input_stream')
                    expected_output_stream = test_case.get('expected_output_stream')
                    
                    # For sequential circuits, validation is handled differently
                    if input_stream is not None or expected_output_stream is not None:
                        # Skip sequential test case validation for now - requires circuit evaluation
                        continue
                    
                    # For combinatorial circuits, verify input/output structure matches puzzle definition
                    if inputs and expected_outputs:
                        tc_input_keys = set(inputs.keys())
                        puzzle_input_keys = set(puzzle_inputs)
                        if tc_input_keys != puzzle_input_keys:
                            raise ValidationError(
                                f"Test case {i} inputs {tc_input_keys} don't match puzzle inputs {puzzle_input_keys}"
                            )
                        
                        tc_output_keys = set(expected_outputs.keys())
                        puzzle_output_keys = set(puzzle_outputs)
                        if tc_output_keys != puzzle_output_keys:
                            raise ValidationError(
                                f"Test case {i} outputs {tc_output_keys} don't match puzzle outputs {puzzle_output_keys}"
                            )
                        
                        # Validate solution can evaluate this test case
                        key = json.dumps(inputs, sort_keys=True)
                        if key not in eval_map:
                            raise ValidationError(f"Sample solution missing evaluation for test case {i}: {inputs}")
                        
                        solution_output = eval_map[key]
                        for output_name, expected_value in expected_outputs.items():
                            if output_name not in solution_output:
                                raise ValidationError(
                                    f"Sample solution test case {i} missing output '{output_name}'"
                                )
                            if solution_output[output_name] != expected_value:
                                raise ValidationError(
                                    f"Sample solution test case {i} incorrect: "
                                    f"for {inputs}, expected {output_name}={expected_value} "
                                    f"but got {solution_output[output_name]}"
                                )
                
                if difficulty in ("EASY", "MEDIUM", "HARD"):
                    config_data.setdefault('puzzle', {})['difficulty'] = difficulty
                    with open(config_path, 'w', encoding='utf-8') as cf:
                        json.dump(config_data, cf, indent=2)

                admin_id = 999
                conn.execute("PRAGMA foreign_keys = OFF")
                insert_riddle(conn, config_path, instructions_path, admin_id)

                return {"message": "Puzzle created successfully"}
        except Exception as e:
            print(f"Error during puzzle creation: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()

    return router
