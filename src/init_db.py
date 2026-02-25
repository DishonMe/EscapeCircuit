import sys
import os
import sqlite3
from pathlib import Path

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from Backend.PersistantLayer._db import connect
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.RatingRepo import RatingRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo

def init_db():
    # DB in project root (src/..)
    db_path = Path(current_dir).parent / "escape_circuit.db"
    print(f"Initializing DB at: {db_path}")

    conn = connect(str(db_path))

    print("Creating schemas...")
    UserRepo(conn)
    CircuitRepo(conn)
    PuzzleRepo(conn)
    RatingRepo(conn)
    SolveRepo(conn)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
