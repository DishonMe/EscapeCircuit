import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

# Set encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

# Database path
DB_PATH = 'escape_circuit.db'

def utcnow():
    return datetime.now(timezone.utc)

def insert_riddle(config_path, instructions_path):
    print(f"Processing {config_path}...")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    instruction_text = ""
    if os.path.exists(instructions_path):
        with open(instructions_path, 'r') as f:
            instruction_text = f.read()

    puzzle_data = config['puzzle']
    test_cases = config.get('test_cases', [])

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Get or Create Admin User (to be the creator)
    c.execute("SELECT id FROM users WHERE username = ?", ('admin',))
    row = c.fetchone()
    if row:
        creator_id = row[0]
    else:
        print("Admin user not found, creating...")
        c.execute("INSERT INTO users (username, role, xp, created_at) VALUES (?, ?, ?, ?)",
                  ('admin', 'admin', 0, utcnow()))
        creator_id = c.lastrowid

    # 2. Insert Puzzle
    # Note: Puzzle table columns based on model: 
    # id, name, creator_user_id, description, status, budget, time_limit_seconds, 
    # default_gate_set, rating_count...
    
    # Map gates to string 
    gates_json = json.dumps(puzzle_data.get('default_gate_set', []))
    
    # Inputs/Outputs are not seemingly in the main schema based on previous checks, 
    # but let's check if we can store them in description or if I should assume schema lacks them.
    # For now, I will append the requested inputs/outputs to the description if they aren't there.
    full_description = instruction_text
    
    # We might want to store inputs/outputs in the description for now as a workaround 
    # if the DB schema doesn't support them, but for now I'll just use the instruction text.

    try:
        c.execute("""
            INSERT INTO puzzles (
                name, creator_user_id, description, status, budget, 
                time_limit_seconds, default_gate_set, rating_count, 
                avg_difficulty, avg_fun, avg_clearness,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            puzzle_data['name'],
            creator_id,
            full_description,
            'published', # Set to published so it shows up
            puzzle_data.get('budget', 0),
            puzzle_data.get('time_limit_seconds'), # Can be None
            gates_json, # Store as JSON string? Or comma separated?
                        # PuzzleRepo typically handles this. 
                        # Let's check how PuzzleRepo stores it. 
                        # In SQL, usually it's a string.
            0, 0.0, 0.0, 0.0, 
            utcnow()
        ))
        puzzle_id = c.lastrowid
        print(f"Inserted Puzzle '{puzzle_data['name']}' with ID {puzzle_id}")
    except sqlite3.IntegrityError:
        c.execute("SELECT id FROM puzzles WHERE name = ?", (puzzle_data['name'],))
        puzzle_id = c.fetchone()[0]
        c.execute("""
            UPDATE puzzles SET 
                creator_user_id = ?, description = ?, status = ?, budget = ?, 
                time_limit_seconds = ?, default_gate_set = ?
            WHERE id = ?
        """, (
            creator_id, full_description, 'published', 
            puzzle_data.get('budget', 0), puzzle_data.get('time_limit_seconds'), 
            gates_json, puzzle_id
        ))
        print(f"Updated Puzzle '{puzzle_data['name']}' with ID {puzzle_id}")

    # 3. Handle Test Cases
    # Clear old test cases to avoid duplicates on update
    c.execute("DELETE FROM puzzle_test_cases WHERE puzzle_id = ?", (puzzle_id,))

    # 3. Insert Test Cases
    for tc in test_cases:
        inputs_json = json.dumps(tc['inputs'])
        outputs_json = json.dumps(tc['expected_outputs'])
        
        c.execute("""
            INSERT INTO puzzle_test_cases (
                puzzle_id, kind, inputs, expected_outputs, created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            puzzle_id,
            'blackbox', # Assuming blackbox for the riddle config
            inputs_json,
            outputs_json,
            utcnow()
        ))
        
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == '__main__':
    # Locate all riddles using absolute path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    riddles_dir = os.path.join(project_root, 'riddles')
    
    # Update DB_PATH to be absolute as well
    DB_PATH = os.path.join(project_root, 'escape_circuit.db')
    print(f"Project Root: {project_root}")
    print(f"Riddles Dir: {riddles_dir}")
    print(f"DB Path: {DB_PATH}")

    if not os.path.exists(riddles_dir):
        print(f"Directory '{riddles_dir}' not found.")
        exit(1)

    for filename in os.listdir(riddles_dir):
        if filename.endswith('_config.json'):
            config_path = os.path.join(riddles_dir, filename)
            base_name = filename.replace('_config.json', '')
            instr_path = os.path.join(riddles_dir, f"{base_name}_instructions.md")
            insert_riddle(config_path, instr_path)
