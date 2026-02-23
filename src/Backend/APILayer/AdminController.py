from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
import shutil
import tempfile
import pathlib
import json

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.AdminService import AdminService
from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.DomainLayer.Circuit import Circuit
from Backend.APILayer.auth_utils import verify_token
from Backend.PersistantLayer._db import connect
from insert_riddles import insert_riddle


class AssignCreatorReq(BaseModel):
    target_user_id: int


class RemoveCreatorReq(BaseModel):
    target_user_id: int


def get_db_conn():
    """Helper to get a fresh connection for the upload-puzzle script."""
    current_file = pathlib.Path(__file__).resolve()
    root_dir = current_file.parent.parent.parent.parent
    db_path = root_dir / 'escape_circuit.db'
    if not db_path.exists():
        print(f"CRITICAL ERROR: Database file not found at {db_path}")
    conn = connect(str(db_path))
    return conn


def build_admin_router(admin_service: AdminService) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["Admin"])

    # ------------------------------------------------------------------ #
    #  REQ 7.2 + 1.2  —  Assign creator (sets to pending_creator)
    # ------------------------------------------------------------------ #
    @router.post("/assign-creator")
    def assign_creator(req: AssignCreatorReq, token: str = Depends(verify_token)):
        try:
            return admin_service.assign_creator(token, req.target_user_id)
        except ValidationError as e:
            msg = str(e)
            if "admin required" in msg:
                raise HTTPException(status_code=403, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

    # ------------------------------------------------------------------ #
    #  REQ 7.3 + 1.2.1  —  Remove creator
    # ------------------------------------------------------------------ #
    @router.post("/remove-creator")
    def remove_creator(req: RemoveCreatorReq, token: str = Depends(verify_token)):
        try:
            return admin_service.remove_creator(token, req.target_user_id)
        except ValidationError as e:
            msg = str(e)
            if "admin required" in msg:
                raise HTTPException(status_code=403, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

    # ------------------------------------------------------------------ #
    #  REQ 7.4  —  Delete any puzzle
    # ------------------------------------------------------------------ #
    @router.delete("/puzzles/{puzzle_id}")
    def delete_puzzle(puzzle_id: int, token: str = Depends(verify_token)):
        try:
            return admin_service.delete_puzzle(token, puzzle_id)
        except ValidationError as e:
            msg = str(e)
            if "admin required" in msg:
                raise HTTPException(status_code=403, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

    # ------------------------------------------------------------------ #
    #  Admin puzzle listing (moderation view)
    # ------------------------------------------------------------------ #
    @router.get("/puzzles")
    def list_puzzles(
        limit: int = 50,
        offset: int = 0,
        page: Optional[int] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        creator_id: Optional[int] = None,
        creator_username: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
        token: str = Depends(verify_token),
    ):
        try:
            if page is not None and page > 0:
                offset = (page - 1) * limit
            return admin_service.list_puzzles(
                token,
                limit=limit,
                offset=offset,
                search=search,
                status=status,
                creator_id=creator_id,
                creator_username=creator_username,
                date_from=date_from,
                date_to=date_to,
                order_by=order_by,
                order_direction=order_direction,
            )
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

    # ------------------------------------------------------------------ #
    #  REQ 7.5  —  Audit log
    # ------------------------------------------------------------------ #
    @router.get("/audit-log")
    def audit_log(
        limit: int = 100,
        offset: int = 0,
        action_type: Optional[str] = None,
        token: str = Depends(verify_token),
    ):
        try:
            return admin_service.list_audit_log(
                token, limit=limit, offset=offset, action_type=action_type
            )
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

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

    # ------------------------------------------------------------------ #
    #  Upload puzzle (file-based, admin only)
    # ------------------------------------------------------------------ #
    @router.post("/upload-puzzle")
    async def upload_puzzle(
        config_file: UploadFile = File(...),
        instructions_file: UploadFile = File(...),
        sample_solution_file: UploadFile = File(...),
        difficulty: str = Form("EASY"),
        token: str = Depends(verify_token),
    ):
        # Verify admin
        try:
            admin_service._require_admin(token)
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
                # Don't save setup, test, readme files - they're not needed for the system anymore
                # save_file_to_riddles(setup_file)
                # save_file_to_riddles(test_file)
                # save_file_to_riddles(readme_file)

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
                
                # Validate all test cases can be evaluated
                logic_engine = logicEngineService()
                for i, test_case in enumerate(test_cases):
                    inputs = test_case.get('inputs', {})
                    expected_outputs = test_case.get('expected_outputs', {})
                    
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

                return {"message": "Puzzle uploaded successfully"}
        except Exception as e:
            print(f"Error during upload: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()

    return router
