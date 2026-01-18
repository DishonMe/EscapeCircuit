from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
import shutil
import os
import tempfile
import pathlib
from Backend.PersistantLayer._db import connect
from insert_riddles import insert_riddle, get_or_create_admin

def get_db_conn():
    # Helper to get connection for the script
    # This is a bit hacky as insert_riddle expects a sqlite3 connection object, not a generator
    # We will create a fresh connection just for this operation
    # Go up 4 levels to find project root: AdminController -> APILayer -> Backend -> src -> root
    current_file = pathlib.Path(__file__).resolve()
    # APILayer -> Backend -> src -> root
    root_dir = current_file.parent.parent.parent.parent
    db_path = root_dir / 'escape_circuit.db'
    
    # print(f"DEBUG: Connecting to DB at {db_path}")
    if not db_path.exists():
        print(f"CRITICAL ERROR: Database file not found at {db_path}")
        
    conn = connect(str(db_path))
    return conn

def build_admin_router():
    router = APIRouter(prefix="/admin", tags=["Admin"])

    @router.post("/upload-puzzle")
    async def upload_puzzle(
        setup_file: UploadFile = File(...),
        test_file: UploadFile = File(...),
        sample_solution_file: UploadFile = File(...),
        instructions_file: UploadFile = File(...),
        readme_file: UploadFile = File(...),
        config_file: UploadFile = File(...)
    ):
        conn = get_db_conn()
        try:
            # Create a temporary directory to store uploaded files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save files to project 'riddles' directory
                # Go up 4 levels to find project root: AdminController -> APILayer -> Backend -> src -> root
                current_file = pathlib.Path(__file__).resolve()
                root_dir = current_file.parent.parent.parent.parent
                riddles_dir = root_dir / 'riddles'
                
                # Check if riddles dir exists, create if not
                if not riddles_dir.exists():
                    riddles_dir.mkdir(parents=True)

                def save_file_to_riddles(upload_file):
                    dest_path = riddles_dir / upload_file.filename
                    with open(dest_path, "wb") as buffer:
                        shutil.copyfileobj(upload_file.file, buffer)
                    return str(dest_path)

                # Save files directly to riddles folder
                config_path = save_file_to_riddles(config_file)
                instructions_path = save_file_to_riddles(instructions_file)
                
                save_file_to_riddles(setup_file)
                save_file_to_riddles(test_file)
                save_file_to_riddles(sample_solution_file)
                save_file_to_riddles(readme_file)

                # Ignore users for now - hardcoded ID
                # admin_id = get_or_create_admin(conn)
                admin_id = 999 

                # Disable foreign keys temporarily for this connection to bypass user check
                conn.execute("PRAGMA foreign_keys = OFF")

                # Insert Riddle
                insert_riddle(conn, config_path, instructions_path, admin_id)
                
                return {"message": "Puzzle uploaded successfully"}
        except Exception as e:
            # print error to console for debug
            print(f"Error during upload: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()

    return router
