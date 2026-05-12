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
from insert_riddles import insert_riddle, insert_puzzle_to_db


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


def build_riddle_paths(riddles_dir: pathlib.Path, riddle_base_name: str, instructions_ext: str) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path, pathlib.Path]:
    """Build canonical per-riddle file paths under riddles/<riddle_base_name>/. 
    Returns: (config_path, instructions_path, solution_path, tests_path)
    """
    riddle_dir = riddles_dir / riddle_base_name
    return (
        riddle_dir / f"{riddle_base_name}_config.json",
        riddle_dir / f"{riddle_base_name}_instructions{instructions_ext}",
        riddle_dir / f"{riddle_base_name}_sample_solution.json",
        riddle_dir / f"{riddle_base_name}_tests.py",
    )


def _count_non_io_gates_in_solution(solution_data: dict) -> int:
    """Count placed gate-like components in a sample solution.

    IO endpoints are ignored. A solution with only wires and no placed gates
    is considered empty.
    """
    if not isinstance(solution_data, dict):
        return 0

    circuit_data = solution_data.get('circuit')
    if not isinstance(circuit_data, dict):
        return 0

    placed_components = (
        circuit_data.get('placedComponents')
        or circuit_data.get('placed')
        or []
    )
    if not isinstance(placed_components, list):
        return 0

    gate_count = 0
    for component in placed_components:
        if not isinstance(component, dict):
            continue

        component_id = component.get('componentId')
        if component_id is None:
            component_id = component.get('type')
        if component_id is None:
            continue

        component_name = str(component_id).strip()
        if not component_name:
            continue
        if component_name.upper().startswith('IO:'):
            continue

        gate_count += 1

    return gate_count


def _validate_uploaded_puzzle_payload(
    conn,
    config_data: dict,
    instructions_text: str,
    allow_python_tests_only: bool = False,
) -> dict:
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
    if not test_cases and not allow_python_tests_only:
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

    @router.get("/users/{user_id}/profile")
    def get_user_profile(user_id: int, token: str = Depends(verify_token)):
        try:
            return admin_service.get_user_profile(token, user_id)
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

    @router.get("/solving-attempts")
    def solving_attempts(
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[int] = None,
        puzzle_id: Optional[int] = None,
        passed: Optional[bool] = None,
        token: str = Depends(verify_token),
    ):
        try:
            return admin_service.list_solving_attempts(
                token,
                limit=limit,
                offset=offset,
                user_id=user_id,
                puzzle_id=puzzle_id,
                passed=passed,
            )
        except ValidationError as e:
            raise HTTPException(status_code=403, detail=str(e))

    @router.get("/auth-attempts")
    def auth_attempts(
        limit: int = 100,
        offset: int = 0,
        action: Optional[str] = None,
        success: Optional[bool] = None,
        token: str = Depends(verify_token),
    ):
        try:
            return admin_service.list_auth_attempts(
                token,
                limit=limit,
                offset=offset,
                action=action,
                success=success,
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
        python_tests_file: UploadFile = File(None),
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

                temp_path = pathlib.Path(temp_dir)

                # Read and save files to temp directory first
                config_content = await config_file.read()
                config_data = json.loads(config_content)
                instructions_content = await instructions_file.read()
                instructions_text = instructions_content.decode('utf-8')
                solution_content = await sample_solution_file.read()

                # Use temporary naming for temp files (will be renamed after DB insertion)
                temp_base_name = 'temp_puzzle'
                config_path = temp_path / f'{temp_base_name}_config.json'
                instructions_path = temp_path / f'{temp_base_name}_instructions{pathlib.Path(instructions_file.filename or "").suffix or ".tex"}'
                solution_path = temp_path / f'{temp_base_name}_sample_solution.json'

                config_path.write_bytes(config_content)
                instructions_path.write_bytes(instructions_content)
                solution_path.write_bytes(solution_content)

                # ========== VALIDATION PHASE (in-memory with temp files) ==========
                with open(config_path, 'r', encoding='utf-8') as cf:
                    config_data = json.load(cf)
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
                allow_python_tests_only = python_tests_file is not None
                if not test_cases and not allow_python_tests_only:
                    raise ValidationError("Puzzle must have at least one test case or provide a Python tests file")
                
                # Load and validate sample solution using logic engine
                with open(solution_path, 'r', encoding='utf-8') as sf:
                    solution_data = json.load(sf)
                
                if not isinstance(solution_data.get('eval_map'), dict):
                    raise ValidationError("Sample solution must have 'eval_map' field")

                if _count_non_io_gates_in_solution(solution_data) == 0:
                    raise ValidationError(
                        "Sample solution cannot be empty. It must include at least one gate; wires alone are not enough."
                    )
                
                # Keep only minimal validation here.
                # The sample solution has already been export-validated, so we
                # only require a non-empty eval_map and a non-empty circuit.
                eval_map = solution_data.get('eval_map', {})
                
                # Update config with difficulty if valid
                if difficulty in ("EASY", "MEDIUM", "HARD"):
                    config_data.setdefault('puzzle', {})['difficulty'] = difficulty
                    with open(config_path, 'w', encoding='utf-8') as cf:
                        json.dump(config_data, cf, indent=2)

                # ========== DATABASE INSERTION FIRST (to get puzzle_id for naming) ==========
                conn.execute("PRAGMA foreign_keys = OFF")
                puzzle_id = insert_puzzle_to_db(conn, config_data, instructions_text, user_id)
                
                # ========== CREATE DIRECTORY WITH PUZZLE ID NAMING CONVENTION ==========
                # Directory name format: riddle_{puzzle_id}_{sanitized_puzzle_name}
                puzzle_name = config_data.get('puzzle', {}).get('name', 'puzzle')
                sanitized_name = sanitize_puzzle_name(puzzle_name)
                riddle_base_name = f'riddle_{puzzle_id}_{sanitized_name}'
                
                instructions_ext = pathlib.Path(instructions_file.filename or "").suffix or ".tex"
                final_config_path, final_instructions_path, final_solution_path, final_tests_path = build_riddle_paths(
                    riddles_dir,
                    riddle_base_name,
                    instructions_ext,
                )
                final_config_path.parent.mkdir(parents=True, exist_ok=True)
                
                # ========== SAVE FILES TO THE FINAL DIRECTORY ==========
                shutil.copy2(config_path, final_config_path)
                shutil.copy2(instructions_path, final_instructions_path)
                shutil.copy2(solution_path, final_solution_path)
                
                # ========== SAVE PYTHON TESTS FILE IF PROVIDED ==========
                if python_tests_file is not None:
                    tests_content = await python_tests_file.read()
                    final_tests_path.write_bytes(tests_content)
                
                # ========== INSERT TEST CASES AND COMPLETE PUZZLE SETUP ==========
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
        python_tests_file: UploadFile = File(None),
        token: str = Depends(verify_token),
    ):
        # Verify admin and get their user_id
        try:
            admin_id = admin_service._require_admin(token)
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
                allow_python_tests_only = python_tests_file is not None
                _validate_uploaded_puzzle_payload(conn, config_data, instructions_text, allow_python_tests_only=allow_python_tests_only)

                solution_content = await sample_solution_file.read()
                
                # Use temporary naming for temp files (will be renamed after DB insertion)
                temp_base_name = 'temp_puzzle'
                config_path = temp_path / f'{temp_base_name}_config.json'
                instructions_path = temp_path / f'{temp_base_name}_instructions{pathlib.Path(instructions_file.filename or "").suffix or ".tex"}'
                solution_path = temp_path / f'{temp_base_name}_sample_solution.json'

                config_path.write_bytes(config_content)
                instructions_path.write_bytes(instructions_content)
                solution_path.write_bytes(solution_content)

                # ========== VALIDATION PHASE (in-memory with temp files) ==========
                with open(config_path, 'r', encoding='utf-8') as cf:
                    config_data = json.load(cf)
                puzzle_config = _validate_uploaded_puzzle_payload(conn, config_data, instructions_text, allow_python_tests_only=allow_python_tests_only)
                test_cases = config_data.get('test_cases', [])
                
                # Load and validate sample solution using logic engine
                with open(solution_path, 'r', encoding='utf-8') as sf:
                    solution_data = json.load(sf)
                
                if not isinstance(solution_data.get('eval_map'), dict):
                    raise ValidationError("Sample solution must have 'eval_map' field")

                if _count_non_io_gates_in_solution(solution_data) == 0:
                    raise ValidationError(
                        "Sample solution cannot be empty. It must include at least one gate; wires alone are not enough."
                    )
                
                # Keep only minimal validation here.
                # The sample solution has already been export-validated, so we
                # only require a non-empty eval_map and a non-empty circuit.
                eval_map = solution_data.get('eval_map', {})
                
                # Update config with difficulty if valid
                if difficulty in ("EASY", "MEDIUM", "HARD"):
                    config_data.setdefault('puzzle', {})['difficulty'] = difficulty
                    with open(config_path, 'w', encoding='utf-8') as cf:
                        json.dump(config_data, cf, indent=2)

                # ========== DATABASE INSERTION FIRST (to get puzzle_id for naming) ==========
                conn.execute("PRAGMA foreign_keys = OFF")
                puzzle_id = insert_puzzle_to_db(conn, config_data, instructions_text, admin_id)
                
                # ========== CREATE DIRECTORY WITH PUZZLE ID NAMING CONVENTION ==========
                # Directory name format: riddle_{puzzle_id}_{sanitized_puzzle_name}
                puzzle_name = config_data.get('puzzle', {}).get('name', 'puzzle')
                sanitized_name = sanitize_puzzle_name(puzzle_name)
                riddle_base_name = f'riddle_{puzzle_id}_{sanitized_name}'
                
                instructions_ext = pathlib.Path(instructions_file.filename or "").suffix or ".tex"
                final_config_path, final_instructions_path, final_solution_path, final_tests_path = build_riddle_paths(
                    riddles_dir,
                    riddle_base_name,
                    instructions_ext,
                )
                final_config_path.parent.mkdir(parents=True, exist_ok=True)
                
                # ========== SAVE FILES TO THE FINAL DIRECTORY ==========
                shutil.copy2(config_path, final_config_path)
                shutil.copy2(instructions_path, final_instructions_path)
                shutil.copy2(solution_path, final_solution_path)
                
                # ========== SAVE PYTHON TESTS FILE IF PROVIDED ==========
                if python_tests_file is not None:
                    tests_content = await python_tests_file.read()
                    final_tests_path.write_bytes(tests_content)
                
                # ========== INSERT TEST CASES AND COMPLETE PUZZLE SETUP ==========
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
