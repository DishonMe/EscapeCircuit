from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Optional, Any, Union, List
import re
from Backend import settings

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


class UpdatePuzzleReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    creator_comment: Optional[str] = None
    allow_arsenal: Optional[bool] = None


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


class CreateCustomPieceReq(BaseModel):
    name: str
    cost: int
    num_inputs: int
    num_outputs: int
    truth_table: Dict[str, Any]


def get_db_conn():
    """Helper to get a fresh connection for the puzzle creation."""
    current_file = pathlib.Path(__file__).resolve()
    root_dir = current_file.parent.parent.parent.parent
    db_path = root_dir / 'escape_circuit.db'
    if not db_path.exists():
        print(f"CRITICAL ERROR: Database file not found at {db_path}")
    conn = connect(str(db_path))
    return conn


def get_next_puzzle_number(riddles_dir: pathlib.Path) -> int:
    """Get the next puzzle number based on existing riddle_XX files."""
    max_num = 0
    if riddles_dir.exists():
        for file in riddles_dir.iterdir():
            match = re.match(r'riddle_(\d+)_', file.name)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)
    return max_num + 1


def sanitize_puzzle_name(name: str) -> str:
    """Convert puzzle name to a valid filename component."""
    # Replace spaces and special chars with underscores
    sanitized = re.sub(r'[^\w\s-]', '', name)
    sanitized = re.sub(r'[\s-]+', '_', sanitized)
    return sanitized.lower()


def _validate_uploaded_puzzle_payload(conn, config_data: dict, instructions_text: str) -> dict:
    puzzle_config = config_data.get('puzzle', {})
    if not puzzle_config:
        raise ValidationError("Config missing 'puzzle' section")

    puzzle_name = (puzzle_config.get('name') or '').strip()
    if not puzzle_name:
        raise ValidationError("Puzzle name is required")
    if len(puzzle_name) > settings.PUZZLE_NAME_MAX_LENGTH:
        raise ValidationError(
            f"Puzzle name must be at most {settings.PUZZLE_NAME_MAX_LENGTH} characters."
        )

    description = puzzle_config.get('description', '') or ''
    if len(description) > settings.PUZZLE_DESCRIPTION_MAX_LENGTH:
        raise ValidationError(
            f"Puzzle description must be at most {settings.PUZZLE_DESCRIPTION_MAX_LENGTH} characters."
        )

    if len(instructions_text.encode('utf-8')) > settings.PUZZLE_INSTRUCTIONS_MAX_BYTES:
        raise ValidationError(
            f"Puzzle instructions must be at most {settings.PUZZLE_INSTRUCTIONS_MAX_BYTES} bytes."
        )

    existing = conn.execute(
        "SELECT 1 FROM puzzles WHERE LOWER(name) = LOWER(?) LIMIT 1",
        (puzzle_name,),
    ).fetchone()
    if existing:
        raise ValidationError("Puzzle name already exists. Please choose a unique name.")

    if not puzzle_config.get('inputs') or not isinstance(puzzle_config['inputs'], list):
        raise ValidationError("Puzzle must have 'inputs' list")
    if not puzzle_config.get('outputs') or not isinstance(puzzle_config['outputs'], list):
        raise ValidationError("Puzzle must have 'outputs' list")
    if not puzzle_config.get('default_gate_set'):
        raise ValidationError("Puzzle must have 'default_gate_set'")

    test_cases = config_data.get('test_cases', [])
    if not test_cases:
        raise ValidationError("Puzzle must have at least one test case")

    return puzzle_config


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
        creator: Optional[str] = Query(None),
        creator_id: Optional[int] = None,
        creator_experience_level: Optional[str] = None,
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
                creator_username=creator,
                creator_experience_level=creator_experience_level,
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
                
                # Get saved puzzles for this user
                saved_puzzles = puzzle_service.repo.list_saved_puzzles(user_id)
                saved_puzzle_ids = {int(p.id) for p in saved_puzzles}
                
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
                        p["rating_min_attempt_seconds"] = settings.RATING_MIN_ATTEMPT_SECONDS
                        # Can-rate flag (solved OR 5 min spent)
                        if pid and rating_service:
                            try:
                                p["can_rate"] = rating_service._can_rate(user_id, pid)
                            except Exception:
                                p["can_rate"] = p.get("is_solved", False)
                        else:
                            p["can_rate"] = p.get("is_solved", False)
                        # Inject user's rating (if exists)
                        if pid and rating_service:
                            try:
                                user_rating = rating_service.rating_repo.get_by_puzzle_user(pid, user_id)
                                if user_rating:
                                    p["user_rating"] = user_rating.to_dict()
                            except Exception:
                                pass
                        # Inject saved status
                        p["is_saved"] = pid in saved_puzzle_ids if pid else False
                        # Inject rating metrics
                        _inject_rating_metrics(p)
            except Exception:
                pass  # gracefully degrade if solve_repo unavailable

            return result
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.get("/my-puzzles/list")
    def list_my_puzzles(
        limit: int = 50,
        offset: int = 0,
        page: Optional[int] = None,
        search: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
        token: str = Depends(verify_token)
    ):
        try:
            if page is not None and page > 0:
                offset = (page - 1) * limit
            
            return puzzle_service.list_my_puzzles(
                token,
                limit=limit,
                offset=offset,
                search=search,
                order_by=order_by,
                order_direction=order_direction
            )
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
                result["rating_min_attempt_seconds"] = settings.RATING_MIN_ATTEMPT_SECONDS
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

    @router.delete("/{puzzle_id}")
    def delete_puzzle(puzzle_id: int, token: str = Depends(verify_token)):
        try:
            return puzzle_service.delete_puzzle(token, puzzle_id)
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @router.patch("/{puzzle_id}")
    def update_puzzle(puzzle_id: int, req: UpdatePuzzleReq, token: str = Depends(verify_token)):
        try:
            payload = {}
            if req.name is not None:
                payload["name"] = req.name
            if req.description is not None:
                payload["description"] = req.description
            if req.instructions is not None:
                payload["instructions"] = req.instructions
            # Always include creator_comment if it was in the request (even if None for deletion)
            if "creator_comment" in req.model_fields_set or req.creator_comment is not None:
                payload["creator_comment"] = req.creator_comment
            if req.allow_arsenal is not None:
                payload["allow_arsenal"] = req.allow_arsenal
            return puzzle_service.update_puzzle(token, puzzle_id, payload)
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

    @router.get("/{puzzle_id}/leaderboard")
    def leaderboard(puzzle_id: int, type: str = "time", limit: int = 50, token: str = Depends(verify_token)):
        try:
            puzzle_service.auth.require_user_id(token)
            if type == "cost":
                entries = puzzle_service.solve_repo.get_leaderboard_by_cost(puzzle_id, limit=limit)
            else:
                entries = puzzle_service.solve_repo.get_leaderboard(puzzle_id, limit=limit)
            return {"data": entries}
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

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

                config_content = await config_file.read()
                config_data = json.loads(config_content)
                instructions_content = await instructions_file.read()
                instructions_text = instructions_content.decode('utf-8')
                _validate_uploaded_puzzle_payload(conn, config_data, instructions_text)

                puzzle_name = config_data.get('puzzle', {}).get('name', 'puzzle')
                puzzle_num = get_next_puzzle_number(riddles_dir)
                sanitized_name = sanitize_puzzle_name(puzzle_name)

                temp_path = pathlib.Path(temp_dir)

                # Helper to save files to TEMP directory (for validation)
                def save_file_to_temp(upload_file, file_type):
                    base_name = f'riddle_{puzzle_num:02d}_{sanitized_name}_{file_type}'
                    # Determine extension from original filename
                    ext = pathlib.Path(upload_file.filename).suffix
                    if not ext:
                        # Default extensions
                        if file_type == 'config':
                            ext = '.json'
                        elif file_type == 'instructions':
                            ext = '.md'
                        elif 'solution' in file_type:
                            ext = '.json'
                    dest_path = temp_path / (base_name + ext)
                    with open(dest_path, "wb") as buffer:
                        shutil.copyfileobj(upload_file.file, buffer)
                    return str(dest_path)

                solution_content = await sample_solution_file.read()

                config_path = temp_path / f'riddle_{puzzle_num:02d}_{sanitized_name}_config.json'
                instructions_path = temp_path / f'riddle_{puzzle_num:02d}_{sanitized_name}_instructions{pathlib.Path(instructions_file.filename or "").suffix or ".tex"}'
                solution_path = temp_path / f'riddle_{puzzle_num:02d}_{sanitized_name}_sample_solution.json'

                config_path.write_bytes(config_content)
                instructions_path.write_bytes(instructions_content)
                solution_path.write_bytes(solution_content)

                # ========== VALIDATION PHASE (in-memory with temp files) ==========
                with open(config_path, 'r', encoding='utf-8') as cf:
                    config_data = json.load(cf)
                puzzle_config = _validate_uploaded_puzzle_payload(conn, config_data, instructions_text)
                test_cases = config_data.get('test_cases', [])
                
                # Load and validate sample solution using logic engine
                with open(solution_path, 'r', encoding='utf-8') as sf:
                    solution_data = json.load(sf)
                
                if not isinstance(solution_data.get('eval_map'), dict):
                    raise ValidationError("Sample solution must have 'eval_map' field")
                
                # Check if solution has circuit structure for actual simulation
                solution_circuit_data = solution_data.get('circuit')
                
                puzzle_inputs = puzzle_config.get('inputs', [])
                puzzle_outputs = puzzle_config.get('outputs', [])
                eval_map = solution_data.get('eval_map', {})
                
                # Debug: Log eval_map structure
                print(f"\n=== VALIDATION DEBUG ===")
                print(f"Puzzle Inputs: {puzzle_inputs}")
                print(f"Puzzle Outputs: {puzzle_outputs}")
                print(f"Eval Map Keys Available: {list(eval_map.keys())}")
                print(f"Number of test cases: {len(test_cases)}")
                print(f"Solution has circuit data: {solution_circuit_data is not None}")
                
                # For puzzle creation, we trust that the creator tested their circuit in the debugger.
                # The eval_map provides the expected outputs that users' solutions will be validated against.
                # Actual circuit correctness is verified when users solve the puzzle and their solution
                # output must match the eval_map (which is what matters for grading).
                
                # Get min/max cycles if set
                min_cycles = puzzle_config.get('min_cycles')
                max_cycles = puzzle_config.get('max_cycles')
                
                # Validate all test cases can be evaluated
                for i, test_case in enumerate(test_cases):
                    # Get test case kind
                    tc_kind = test_case.get('kind', 'blackbox')
                    
                    if tc_kind == 'gate_limit':
                        # Gate limit constraint (per-gate maximum)
                        gate_name = test_case.get('gate_name')
                        gate_limit = test_case.get('gate_limit')
                        
                        print(f"\n[Test Case {i}] Gate Limit Constraint")
                        print(f"  Gate: {gate_name}, Max Count: {gate_limit}")
                        
                        if not gate_name:
                            raise ValidationError(f"Gate limit test case {i} missing 'gate_name'")
                        if gate_limit is None or gate_limit <= 0:
                            raise ValidationError(f"Gate limit test case {i} missing or invalid 'gate_limit'")
                        
                        print(f"  ✓ Gate limit constraint valid")
                        
                    elif tc_kind == 'gate_count_limit':
                        # Total gate count constraint
                        max_gate_count = test_case.get('max_gate_count')
                        
                        print(f"\n[Test Case {i}] Total Gate Count Limit")
                        print(f"  Max Total Gates: {max_gate_count}")
                        
                        # Skip if not properly set (helps with frontend default values)
                        if max_gate_count is None or max_gate_count <= 0:
                            print(f"  - Skipping: max_gate_count not set or invalid")
                            continue
                        
                        print(f"  ✓ Total gate count limit valid")
                    
                    elif tc_kind == 'stream':
                        # Stream test case validation
                        input_stream = test_case.get('input_stream', [])
                        expected_output_stream = test_case.get('expected_output_stream', {})
                        
                        print(f"\n[Test Case {i}] Stream")
                        print(f"  Input Stream Length: {len(input_stream)}")
                        print(f"  Input Stream: {input_stream}")
                        print(f"  Expected Output Stream: {expected_output_stream}")
                        
                        if not input_stream:
                            raise ValidationError(f"Stream test case {i} has empty input_stream")
                        if not expected_output_stream:
                            raise ValidationError(f"Stream test case {i} has empty expected_output_stream")
                        
                        num_cycles = len(input_stream)
                        
                        # Check min/max cycles constraints
                        if min_cycles is not None and num_cycles < min_cycles:
                            raise ValidationError(
                                f"Stream test case {i} has {num_cycles} cycles but minimum required is {min_cycles}"
                            )
                        if max_cycles is not None and num_cycles > max_cycles:
                            raise ValidationError(
                                f"Stream test case {i} has {num_cycles} cycles but maximum allowed is {max_cycles}"
                            )
                        
                        # Verify all inputs streams match puzzle inputs
                        if input_stream and isinstance(input_stream[0], dict):
                            tc_input_keys = set(input_stream[0].keys())
                            puzzle_input_keys = set(puzzle_inputs)
                            if tc_input_keys != puzzle_input_keys:
                                raise ValidationError(
                                    f"Stream test case {i} inputs {tc_input_keys} don't match puzzle inputs {puzzle_input_keys}"
                                )
                        
                        # Verify output keys match puzzle outputs
                        tc_output_keys = set(expected_output_stream.keys())
                        puzzle_output_keys = set(puzzle_outputs)
                        if tc_output_keys != puzzle_output_keys:
                            raise ValidationError(
                                f"Stream test case {i} outputs {tc_output_keys} don't match puzzle outputs {puzzle_output_keys}"
                            )
                        
                        # Verify all output arrays have consistent length with inputs
                        for output_name, output_values in expected_output_stream.items():
                            if not isinstance(output_values, list):
                                raise ValidationError(
                                    f"Stream test case {i} output '{output_name}' must be a list"
                                )
                            if len(output_values) != num_cycles:
                                raise ValidationError(
                                    f"Stream test case {i} output '{output_name}' length {len(output_values)} "
                                    f"doesn't match input stream length {num_cycles}"
                                )
                        
                        # Validate stream test case against sample solution
                        # For sequential circuits, simulate the stream to verify outputs
                        # (Can't use simple eval_map lookup because same input can have different outputs based on state)
                        
                        print(f"  Simulating stream from sample solution circuit...")
                        if not solution_circuit_data:
                            raise ValidationError(
                                f"Stream test case {i} requires sample solution to have circuit data for validation"
                            )
                        
                        # Use the logic engine from solving_service to simulate the stream
                        from Backend.DomainLayer.Circuit import Circuit as CircuitModel
                        
                        # Normalize the circuit structure: ensure it has placedComponents
                        normalized_circuit_data = solution_circuit_data.copy()
                        if "placed" in normalized_circuit_data and "placedComponents" not in normalized_circuit_data:
                            normalized_circuit_data["placedComponents"] = normalized_circuit_data["placed"]
                        
                        # Create a temporary circuit from solution data
                        temp_circuit = CircuitModel(
                            id=0,
                            user_id=0,
                            name="temp-validate",
                            cost=0,
                            structure_json=json.dumps(normalized_circuit_data),
                            is_arsenal=False,
                        )
                        
                        print(f"  Circuit structure keys: {list(normalized_circuit_data.keys())}")
                        
                        # Extract DFF IDs from solution circuit to track state
                        placed_components = normalized_circuit_data.get("placedComponents", []) or normalized_circuit_data.get("components", [])
                        dff_ids = []
                        for comp in placed_components:
                            if comp.get("componentId") == "DFF" or comp.get("type") == "DFF":
                                dff_ids.append(comp["id"])
                        
                        print(f"  DFFs in solution: {dff_ids}")
                        
                        # Simulate the stream, tracking state
                        current_state = {str(did): 0 for did in dff_ids}
                        actual_stream = {k: [] for k in expected_output_stream.keys()}
                        
                        for cycle_idx, input_dict in enumerate(input_stream):
                            if isinstance(input_dict, dict):
                                # Merge inputs with current DFF state
                                full_inputs = input_dict.copy()
                                full_inputs.update(current_state)
                                
                                print(f"  Cycle {cycle_idx}: inputs={input_dict}, state={current_state}")
                                
                                try:
                                    # Simulate this cycle using solving_service's logic engine
                                    cycle_outputs = solving_service.engine.evaluate(temp_circuit, full_inputs)
                                    print(f"    Outputs: {cycle_outputs}")
                                    
                                    # Record outputs for each puzzle output
                                    for output_name in expected_output_stream.keys():
                                        actual_stream[output_name].append(cycle_outputs.get(output_name, 0))
                                    
                                    # Update state for next cycle
                                    for did in dff_ids:
                                        next_val = cycle_outputs.get(f"{did}_next")
                                        current_state[str(did)] = next_val if next_val is not None else 0
                                        print(f"    DFF {did}_next = {next_val}")
                                    
                                except Exception as e:
                                    print(f"    Simulation error: {str(e)}")
                                    import traceback
                                    traceback.print_exc()
                                    raise ValidationError(
                                        f"Stream test case {i} cycle {cycle_idx}: "
                                        f"Failed to simulate circuit: {str(e)}"
                                    )
                        
                        # Compare actual stream with expected stream
                        print(f"  Expected stream: {expected_output_stream}")
                        print(f"  Actual stream: {actual_stream}")
                        
                        if actual_stream != expected_output_stream:
                            # Find which cycle mismatched
                            for output_name in expected_output_stream.keys():
                                for cycle_idx in range(len(input_stream)):
                                    if actual_stream[output_name][cycle_idx] != expected_output_stream[output_name][cycle_idx]:
                                        raise ValidationError(
                                            f"Stream test case {i} cycle {cycle_idx}: "
                                            f"expected {output_name}={expected_output_stream[output_name][cycle_idx]} "
                                            f"but simulation gives {actual_stream[output_name][cycle_idx]}"
                                        )
                        
                        print(f"  ✓ Test case {i} PASSED")
                    elif tc_kind == 'blackbox':
                        # Blackbox test case validation
                        inputs = test_case.get('inputs', {})
                        expected_outputs = test_case.get('expected_outputs', {})
                        
                        print(f"\n[Test Case {i}] Blackbox")
                        print(f"  Inputs: {inputs}")
                        print(f"  Expected Outputs: {expected_outputs}")
                        
                        # Verify input/output structure matches puzzle definition
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
                        # Match frontend's key format: no spaces in JSON (separators=(',', ':'))
                        sorted_input_keys = sorted(inputs.keys())
                        key = json.dumps({k: inputs[k] for k in sorted_input_keys}, separators=(',', ':'))
                        
                        print(f"  Looking for key: {key}")
                        print(f"  Available keys: {list(eval_map.keys())}")
                        
                        if key not in eval_map:
                            raise ValidationError(f"Sample solution missing evaluation for test case {i}: {inputs}")
                        
                        solution_output = eval_map[key]
                        print(f"  Solution output: {solution_output}")
                        print(f"  Expected outputs: {expected_outputs}")
                        
                        # CRITICAL: Validate outputs match
                        for output_name, expected_value in expected_outputs.items():
                            if output_name not in solution_output:
                                raise ValidationError(
                                    f"Sample solution test case {i} missing output '{output_name}'"
                                )
                            actual_value = solution_output[output_name]
                            print(f"    {output_name}: expected={expected_value}, actual={actual_value}")
                            
                            if actual_value != expected_value:
                                raise ValidationError(
                                    f"❌ VALIDATION FAILED: Test case {i} output mismatch!\n"
                                    f"   Input: {inputs}\n"
                                    f"   Expected: {expected_outputs}\n"
                                    f"   But your solution produces: {solution_output}\n"
                                    f"   This means your circuit doesn't correctly implement the required logic.\n"
                                    f"   Make sure to test your circuit in the Debugger and verify ALL test cases pass."
                                )
                        print(f"  ✓ Test case {i} PASSED")
                    else:
                        raise ValidationError(
                            f"Test case {i} has unknown kind '{tc_kind}'. "
                            f"Must be one of: blackbox, stream, gate_limit, gate_count_limit"
                        )
                
                print(f"\n=== ✓ ALL {len(test_cases)} TEST CASES VALIDATED SUCCESSFULLY ===")
                
                # CRITICAL: Verify solution actually works
                # For blackbox tests: eval_map should contain input -> output mappings
                # For stream tests: we validate by simulating the circuit (not by eval_map lookup)
                eval_map_size = len(eval_map)
                print(f"\n=== CRITICAL CHECK: Solution Completeness ===")
                print(f"Solution has {eval_map_size} entries in eval_map")
                print(f"Test cases defined: {len(test_cases)}")
                
                # Only require eval_map entries for blackbox tests
                # Stream tests are validated by full circuit simulation (already done above)
                blackbox_count = sum(1 for tc in test_cases if tc.get('kind', 'blackbox') == 'blackbox')
                stream_count = sum(1 for tc in test_cases if tc.get('kind') == 'stream')
                
                print(f"Blackbox tests: {blackbox_count}, Stream tests: {stream_count}")
                
                # Only check eval_map size if there are blackbox tests
                if blackbox_count > 0 and eval_map_size < blackbox_count:
                    raise ValidationError(
                        f"Solution eval_map has {eval_map_size} entries but {blackbox_count} blackbox tests require entries. "
                        f"Your circuit was not properly simulated. Make sure to test it in the Debugger first!"
                    )
                
                if blackbox_count == 0 and stream_count > 0:
                    print(f"✓ No blackbox tests to validate via eval_map (only stream tests, validated by simulation)")
                else:
                    print(f"✓ Solution completeness check passed\n")

                
                # IMPORTANT: Filter out invalid constraint test cases before saving
                # This prevents PuzzleTestCase validation errors when loading the puzzle
                valid_test_cases = []
                for tc in test_cases:
                    tc_kind = tc.get('kind', 'blackbox')
                    
                    # Remove gate_count_limit if invalid
                    if tc_kind == 'gate_count_limit':
                        max_gate_count = tc.get('max_gate_count')
                        if max_gate_count is None or max_gate_count <= 0:
                            print(f"[FILTER] Removing invalid gate_count_limit test case (max_gate_count={max_gate_count})")
                            continue
                    
                    valid_test_cases.append(tc)
                
                # Update test_cases in config to only include valid ones
                config_data['test_cases'] = valid_test_cases
                print(f"[FILTER] Keeping {len(valid_test_cases)} valid test cases (removed {len(test_cases) - len(valid_test_cases)})\n")
                
                # Update config with difficulty if valid
                if difficulty in ("EASY", "MEDIUM", "HARD"):
                    config_data.setdefault('puzzle', {})['difficulty'] = difficulty
                
                # IMPORTANT: Always write the filtered config to file (with or without difficulty)
                with open(config_path, 'w', encoding='utf-8') as cf:
                    json.dump(config_data, cf, indent=2)

                # ========== ALL VALIDATION PASSED - NOW SAVE TO RIDDLES ==========
                # Copy validated temp files to final riddles directory
                final_config_path = riddles_dir / pathlib.Path(config_path).name
                final_instructions_path = riddles_dir / pathlib.Path(instructions_path).name
                final_solution_path = riddles_dir / pathlib.Path(solution_path).name
                
                shutil.copy2(config_path, final_config_path)
                shutil.copy2(instructions_path, final_instructions_path)
                shutil.copy2(solution_path, final_solution_path)

                insert_riddle(conn, str(final_config_path), str(final_instructions_path), user_id, status='unpublished')

                # Get the puzzle ID that was just created (most recent by puzzle_id)
                puzzle_result = conn.execute("""
                    SELECT id FROM puzzles WHERE name = ? ORDER BY id DESC LIMIT 1
                """, (puzzle_name,)).fetchone()
                
                puzzle_id = puzzle_result[0] if puzzle_result else None

                return {"message": "Puzzle created successfully", "puzzle_id": puzzle_id}
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            print(f"Error during puzzle creation: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    #  Save/Bookmark puzzle
    # ------------------------------------------------------------------ #
    @router.post("/{puzzle_id}/save")
    def toggle_save_puzzle(puzzle_id: int, token: str = Depends(verify_token)):
        try:
            user_id = puzzle_service.auth.require_user_id(token)
            # Check if puzzle is already saved
            saved = puzzle_service.repo.list_saved_puzzles(user_id)
            is_saved = any(p.id == puzzle_id for p in saved)
            
            if is_saved:
                # Remove from saved
                puzzle_service.repo.remove_saved_puzzle(user_id, puzzle_id)
                puzzle_service.repo.conn.commit()
                return {"puzzle_id": puzzle_id, "is_saved": False}
            else:
                # Add to saved
                from datetime import datetime
                created_at = datetime.utcnow().isoformat()
                puzzle_service.repo.save_for_later(user_id, puzzle_id, created_at)
                puzzle_service.repo.conn.commit()
                return {"puzzle_id": puzzle_id, "is_saved": True}
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ------------------------------------------------------------------ #
    #  Puzzle custom pieces (special gates for a puzzle)
    # ------------------------------------------------------------------ #
    @router.post("/{puzzle_id}/custom-pieces")
    def create_custom_piece(
        puzzle_id: int,
        req: CreateCustomPieceReq,
        token: str = Depends(verify_token)
    ):
        """Create a custom piece for a puzzle"""
        try:
            user_id = puzzle_service.auth.require_user_id(token)
            
            # Verify user is the puzzle creator
            puzzle = puzzle_service.repo.get_by_id(puzzle_id)
            if not puzzle:
                raise ValidationError("Puzzle not found")
            if puzzle.creator_user_id != user_id:
                raise ValidationError("Only puzzle creator can add custom pieces")
            
            # Validate inputs/outputs limits
            if req.num_inputs < settings.PUZZLE_CUSTOM_PIECES_MIN_INPUTS or req.num_inputs > settings.PUZZLE_CUSTOM_PIECES_MAX_INPUTS:
                raise ValidationError(
                    f"Inputs must be between {settings.PUZZLE_CUSTOM_PIECES_MIN_INPUTS} and {settings.PUZZLE_CUSTOM_PIECES_MAX_INPUTS}"
                )
            if req.num_outputs < settings.PUZZLE_CUSTOM_PIECES_MIN_OUTPUTS or req.num_outputs > settings.PUZZLE_CUSTOM_PIECES_MAX_OUTPUTS:
                raise ValidationError(
                    f"Outputs must be between {settings.PUZZLE_CUSTOM_PIECES_MIN_OUTPUTS} and {settings.PUZZLE_CUSTOM_PIECES_MAX_OUTPUTS}"
                )
            
            if req.cost < 0:
                raise ValidationError("Cost must be non-negative")
            
            # Validate piece name
            if not req.name or not req.name.strip():
                raise ValidationError("Piece name is required")
            
            # Check current count of custom pieces
            from Backend.PersistantLayer.CircuitRepo import CircuitRepo
            circuit_repo = CircuitRepo(puzzle_service.repo.conn)
            existing_pieces = circuit_repo.list_custom_pieces_by_puzzle(puzzle_id)
            if len(existing_pieces) >= settings.PUZZLE_CUSTOM_PIECES_MAX_COUNT:
                raise ValidationError(
                    f"Cannot add more than {settings.PUZZLE_CUSTOM_PIECES_MAX_COUNT} custom pieces per puzzle"
                )
            
            # Create the custom piece
            from Backend.DomainLayer.Circuit import Circuit
            
            custom_piece = Circuit(
                id=0,
                user_id=user_id,
                name=req.name,
                cost=req.cost,
                structure_json="",  # Empty structure for custom puzzle pieces
                is_arsenal=True,
                basic_gates="",  # Empty basic gates
                truth_table=json.dumps(req.truth_table),
                num_inputs=req.num_inputs,
                num_outputs=req.num_outputs,
                puzzle_id=puzzle_id,
            )
            
            circuit_repo = CircuitRepo(puzzle_service.repo.conn)
            custom_piece = circuit_repo.create(custom_piece)
            
            return custom_piece.to_dict()
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/{puzzle_id}/custom-pieces")
    def list_custom_pieces(puzzle_id: int, token: str = Depends(verify_token)):
        """Get all custom pieces for a puzzle"""
        try:
            puzzle_service.auth.require_user_id(token)
            
            # Verify puzzle exists
            puzzle = puzzle_service.repo.get_by_id(puzzle_id)
            if not puzzle:
                raise ValidationError("Puzzle not found")
            
            # Get custom pieces for this puzzle
            from Backend.PersistantLayer.CircuitRepo import CircuitRepo
            circuit_repo = CircuitRepo(puzzle_service.repo.conn)
            custom_pieces = circuit_repo.list_custom_pieces_by_puzzle(puzzle_id)
            
            return {"data": [p.to_dict() for p in custom_pieces]}
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/{puzzle_id}/custom-pieces/{piece_id}")
    def delete_custom_piece(puzzle_id: int, piece_id: int, token: str = Depends(verify_token)):
        """Delete a custom piece"""
        try:
            user_id = puzzle_service.auth.require_user_id(token)
            
            # Verify user is the puzzle creator
            puzzle = puzzle_service.repo.get_by_id(puzzle_id)
            if not puzzle:
                raise ValidationError("Puzzle not found")
            if puzzle.creator_user_id != user_id:
                raise ValidationError("Only puzzle creator can delete custom pieces")
            
            # Verify piece belongs to this puzzle and delete it
            from Backend.PersistantLayer.CircuitRepo import CircuitRepo
            circuit_repo = CircuitRepo(puzzle_service.repo.conn)
            piece = circuit_repo.get_by_id(piece_id)
            
            if not piece or piece.puzzle_id != puzzle_id:
                raise ValidationError("Custom piece not found")
            
            circuit_repo.delete(piece_id, user_id)
            return {"message": "Custom piece deleted successfully"}
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
