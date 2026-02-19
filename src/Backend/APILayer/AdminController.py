from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
import shutil
import tempfile
import pathlib
import json

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.AdminService import AdminService
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
    #  Upload puzzle (existing endpoint — now with auth)
    # ------------------------------------------------------------------ #
    @router.post("/upload-puzzle")
    async def upload_puzzle(
        setup_file: UploadFile = File(...),
        test_file: UploadFile = File(...),
        sample_solution_file: UploadFile = File(...),
        instructions_file: UploadFile = File(...),
        readme_file: UploadFile = File(...),
        config_file: UploadFile = File(...),
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
                save_file_to_riddles(setup_file)
                save_file_to_riddles(test_file)
                save_file_to_riddles(sample_solution_file)
                save_file_to_riddles(readme_file)

                with open(config_path, 'r', encoding='utf-8') as cf:
                    config_data = json.load(cf)
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
