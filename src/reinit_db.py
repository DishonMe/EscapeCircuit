import sys
import os
import sqlite3
from pathlib import Path

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.RatingRepo import RatingRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo

def init_db():
    # DB in project root
    # src/reinit_db.py -> parent = src -> parent = root
    db_path = Path(current_dir).parent / "escape_circuit.db"
    print(f"Initializing DB at: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    print("Creating schemas...")
    try:
        UserRepo(conn)
        CircuitRepo(conn)
        PuzzleRepo(conn)
        RatingRepo(conn)
        SolveRepo(conn)
        print("Schema creation successful.")
    except Exception as e:
        print(f"Error creating schema: {e}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
