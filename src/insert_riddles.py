import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

# Set encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

# Robust path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RIDDLES_DIR = os.path.join(PROJECT_ROOT, 'riddles')
DB_PATH = os.path.join(PROJECT_ROOT, 'escape_circuit.db')

def utcnow():
    return datetime.now(timezone.utc)

def clean_database(conn):
    """
    Only clears ratings and test cases (which get re-imported).
    Preserves puzzles, solve_attempts, and puzzle_progress so user
    progress is NOT lost across server restarts.
    """
    print("Cleaning re-importable data...")
    c = conn.cursor()
    
    for table in ["rating", "puzzle_test_cases"]:
        try:
            c.execute(f"DELETE FROM {table}")
            print(f"  - Cleared table: {table}")
        except sqlite3.OperationalError as e:
            print(f"  - Warning: Could not clear {table} (maybe doesn't exist): {e}")
            
    conn.commit()
    print("Done.")

def get_or_create_admin(conn):
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", ('admin',))
    row = c.fetchone()
    if row:
        return row[0]
    
    print("Creating admin user...")
    c.execute("INSERT INTO users (username, role, xp, created_at) VALUES (?, ?, ?, ?)",
              ('admin', 'admin', 0, utcnow()))
    conn.commit()
    return c.lastrowid

def insert_riddle(conn, config_path, instructions_path, creator_id):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    instruction_text = ""
    if os.path.exists(instructions_path):
        with open(instructions_path, 'r', encoding='utf-8') as f:
            instruction_text = f.read()

    puzzle_data = config['puzzle']
    test_cases = config.get('test_cases', [])
    
    # Determine gates JSON
    gates_json = json.dumps(puzzle_data.get('default_gate_set', []))

    # Difficulty mapping for seed puzzles
    SEED_DIFFICULTY = {
        "Binary Adder": "EASY",
        "Half Adder": "EASY",
        "Sequential Adder": "MEDIUM",
        "Palindrome Detector": "EASY",
        "2-Bit Comparator": "HARD",
    }
    difficulty = puzzle_data.get('difficulty', SEED_DIFFICULTY.get(puzzle_data['name'], 'EASY'))
    
    c = conn.cursor()
    
    # Check if puzzle already exists by name — preserve its ID for solve_attempts
    existing = c.execute("SELECT id FROM puzzles WHERE name = ?", (puzzle_data['name'],)).fetchone()
    
    if existing:
        puzzle_id = existing[0]
        # Update description/budget/config but keep the same ID
        c.execute("""
            UPDATE puzzles SET
                description=?, budget=?, time_limit_seconds=?,
                default_gate_set=?, difficulty=?
            WHERE id=?
        """, (
            instruction_text,
            puzzle_data.get('budget', 0),
            puzzle_data.get('time_limit_seconds'),
            gates_json,
            difficulty,
            puzzle_id
        ))
        # Clear old test cases for this puzzle (they get re-imported below)
        c.execute("DELETE FROM puzzle_test_cases WHERE puzzle_id=?", (puzzle_id,))
    else:
        # INSERT new puzzle
        c.execute("""
            INSERT INTO puzzles (
                name, creator_user_id, description, status, budget, 
                time_limit_seconds, difficulty, default_gate_set, rating_count, 
                avg_difficulty, avg_fun, avg_clearness,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            puzzle_data['name'],
            creator_id,
            instruction_text,
            'published',
            puzzle_data.get('budget', 0),
            puzzle_data.get('time_limit_seconds'),
            difficulty,
            gates_json,
            0, 0.0, 0.0, 0.0,
            utcnow()
        ))
        puzzle_id = c.lastrowid
    
    # INSERT Test Cases
    for tc in test_cases:
        # Handle sequential variation
        inputs = tc.get('inputs')
        expected_outputs = tc.get('expected_outputs')
        input_stream = tc.get('input_stream')
        expected_output_stream = tc.get('expected_output_stream')
        
        # For backward compatibility: convert input_stream to inputs if needed
        if inputs is None and input_stream is not None:
            # It's a stream (list), map it to input names if possible
            # Get input names from puzzle config
            # Config might have "inputs" or "input"
            input_names = puzzle_data.get('inputs') or puzzle_data.get('input') or []
            if len(input_names) == 1:
                # Single input case (e.g. "X")
                inputs = {input_names[0]: input_stream}
            else:
                # Fallback if multiple inputs or unknown structure
                inputs = {"IN": input_stream}
        
        # Map expected_output_stream to expected_outputs if needed
        if expected_outputs is None:
            expected_outputs = expected_output_stream
            
        inputs_json = json.dumps(inputs or {})
        expected_outputs_json = json.dumps(expected_outputs or {})
        input_stream_json = json.dumps(input_stream) if input_stream else None
        expected_output_stream_json = json.dumps(expected_output_stream) if expected_output_stream else None
        
        c.execute("""
            INSERT INTO puzzle_test_cases (
                puzzle_id, kind, inputs, expected_outputs, input_stream, expected_output_stream, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            puzzle_id,
            'blackbox',
            inputs_json,
            expected_outputs_json,
            input_stream_json,
            expected_output_stream_json,
            utcnow()
        ))
        
    conn.commit()
    print(f"Inserted: {puzzle_data['name']}")

def main():
    print(f"Using Riddles Directory: {RIDDLES_DIR}")
    print(f"Using Database: {DB_PATH}")
    
    if not os.path.exists(RIDDLES_DIR):
        print("Riddles directory not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    
    try:
        # 1. Clean re-importable data (test cases, ratings) — preserves puzzles & solves
        clean_database(conn)
        
        # 2. Get Admin
        admin_id = get_or_create_admin(conn)
        
        # 3. Iterate and Insertion
        print("Importing riddles...")
        count = 0
        for filename in os.listdir(RIDDLES_DIR):
            if filename.endswith('_config.json'):
                config_path = os.path.join(RIDDLES_DIR, filename)
                base_name = filename.replace('_config.json', '')
                instr_path = os.path.join(RIDDLES_DIR, f"{base_name}_instructions.md")
                
                try:
                    insert_riddle(conn, config_path, instr_path, admin_id)
                    count += 1
                except Exception as e:
                    print(f"Error inserting {filename}: {e}")
                    
        print(f"Done. Imported {count} riddles.")
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()
