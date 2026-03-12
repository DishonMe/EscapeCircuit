from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
import shutil
import tempfile
import pathlib
import json
import re

from Backend import settings
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


class ConfirmRemoveCreatorReq(BaseModel):
    target_user_id: int
    action: str  # "unpublish", "delete", or "leave"


class UpdatePuzzleLimitsReq(BaseModel):
    max_published: Optional[int] = None
    max_unpublished: Optional[int] = None


def get_db_conn():
    """Helper to get a fresh connection for the upload-puzzle script."""
    current_file = pathlib.Path(__file__).resolve()
    root_dir = current_file.parent.parent.parent.parent
    db_path = root_dir / 'escape_circuit.db'
    if not db_path.exists():
        print(f"CRITICAL ERROR: Database file not found at {db_path}")
    conn = connect(str(db_path))
    return conn


def get_next_puzzle_number(riddles_dir: pathlib.Path) -> int:
    """Get the next puzzle number based on existing riddle_XX items."""
    max_num = 0
    if riddles_dir.exists():
        for item in riddles_dir.iterdir():
            match = re.match(r'riddle_(\d+)_', item.name)
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


def build_riddle_paths(riddles_dir: pathlib.Path, riddle_base_name: str, instructions_ext: str) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    """Build canonical per-riddle file paths under riddles/<riddle_base_name>/."""
    riddle_dir = riddles_dir / riddle_base_name
    return (
        riddle_dir / f"{riddle_base_name}_config.json",
        riddle_dir / f"{riddle_base_name}_instructions{instructions_ext}",
        riddle_dir / f"{riddle_base_name}_sample_solution.json",
    )


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
    #  REQ 7.3 + 1.2.1  —  Confirm remove creator with action
    # ------------------------------------------------------------------ #
    @router.post("/confirm-remove-creator")
    def confirm_remove_creator(req: ConfirmRemoveCreatorReq, token: str = Depends(verify_token)):
        try:
            return admin_service.confirm_remove_creator(token, req.target_user_id, req.action)
        except ValidationError as e:
            msg = str(e)
            if "admin required" in msg:
                raise HTTPException(status_code=403, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

    # ------------------------------------------------------------------ #
    #  REQ 7.4  —  Delete any puzzle (only non-published)
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
    #  Admin unpublish a published puzzle
    # ------------------------------------------------------------------ #
    @router.post("/puzzles/{puzzle_id}/unpublish")
    def unpublish_puzzle(puzzle_id: int, token: str = Depends(verify_token)):
        try:
            return admin_service.admin_unpublish_puzzle(token, puzzle_id)
        except ValidationError as e:
            msg = str(e)
            if "admin required" in msg:
                raise HTTPException(status_code=403, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

    # ------------------------------------------------------------------ #
    #  Admin: update creator puzzle capacity overrides
    # ------------------------------------------------------------------ #
    @router.patch("/users/{user_id}/puzzle-limits")
    def update_puzzle_limits(
        user_id: int,
        req: UpdatePuzzleLimitsReq,
        token: str = Depends(verify_token),
    ):
        try:
            return admin_service.update_creator_puzzle_limits(
                token, user_id, req.max_published, req.max_unpublished
            )
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

                # Read config first to get puzzle name
                config_content = await config_file.read()
                config_data = json.loads(config_content)
                puzzle_name = config_data.get('puzzle', {}).get('name', 'puzzle')
                puzzle_num = get_next_puzzle_number(riddles_dir)
                sanitized_name = sanitize_puzzle_name(puzzle_name)
                riddle_base_name = f'riddle_{puzzle_num:02d}_{sanitized_name}'

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

                # Reset file pointers after reading config
                await config_file.seek(0)

                # Save to TEMP directory first
                config_path = save_file_to_temp(config_file, 'config')
                instructions_path = save_file_to_temp(instructions_file, 'instructions')
                solution_path = save_file_to_temp(sample_solution_file, 'sample_solution')

                # ========== VALIDATION PHASE (in-memory with temp files) ==========
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
                
                # Update config with difficulty if valid
                if difficulty in ("EASY", "MEDIUM", "HARD"):
                    config_data.setdefault('puzzle', {})['difficulty'] = difficulty
                    with open(config_path, 'w', encoding='utf-8') as cf:
                        json.dump(config_data, cf, indent=2)

                # ========== ALL VALIDATION PASSED - NOW SAVE TO RIDDLES ==========
                instructions_ext = pathlib.Path(instructions_path).suffix or '.tex'
                final_config_path, final_instructions_path, final_solution_path = build_riddle_paths(
                    riddles_dir,
                    riddle_base_name,
                    instructions_ext,
                )
                final_config_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(config_path, final_config_path)
                shutil.copy2(instructions_path, final_instructions_path)
                shutil.copy2(solution_path, final_solution_path)

                admin_id = 999
                conn.execute("PRAGMA foreign_keys = OFF")
                insert_riddle(conn, str(final_config_path), str(final_instructions_path), user_id)

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

                temp_path = pathlib.Path(temp_dir)

                config_content = await config_file.read()
                config_data = json.loads(config_content)
                instructions_content = await instructions_file.read()
                instructions_text = instructions_content.decode('utf-8')
                _validate_uploaded_puzzle_payload(conn, config_data, instructions_text)

                puzzle_name = config_data.get('puzzle', {}).get('name', 'puzzle')
                puzzle_num = get_next_puzzle_number(riddles_dir)
                sanitized_name = sanitize_puzzle_name(puzzle_name)
                riddle_base_name = f'riddle_{puzzle_num:02d}_{sanitized_name}'
                solution_content = await sample_solution_file.read()

                config_path = temp_path / f'{riddle_base_name}_config.json'
                instructions_path = temp_path / f'{riddle_base_name}_instructions{pathlib.Path(instructions_file.filename or "").suffix or ".tex"}'
                solution_path = temp_path / f'{riddle_base_name}_sample_solution.json'

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
                
                # Update config with difficulty if valid
                if difficulty in ("EASY", "MEDIUM", "HARD"):
                    config_data.setdefault('puzzle', {})['difficulty'] = difficulty
                    with open(config_path, 'w', encoding='utf-8') as cf:
                        json.dump(config_data, cf, indent=2)

                # ========== ALL VALIDATION PASSED - NOW SAVE TO RIDDLES ==========
                instructions_ext = instructions_path.suffix or '.tex'
                final_config_path, final_instructions_path, final_solution_path = build_riddle_paths(
                    riddles_dir,
                    riddle_base_name,
                    instructions_ext,
                )
                final_config_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(config_path, final_config_path)
                shutil.copy2(instructions_path, final_instructions_path)
                shutil.copy2(solution_path, final_solution_path)

                admin_id = 999
                conn.execute("PRAGMA foreign_keys = OFF")
                insert_riddle(conn, str(final_config_path), str(final_instructions_path), admin_id)

                return {"message": "Puzzle uploaded successfully"}
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            print(f"Error during upload: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()

    return router
