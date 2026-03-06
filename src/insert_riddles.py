import json
import os
import sqlite3
import sys
import re
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

def latex_to_html(latex_text: str) -> str:
    """Convert LaTeX to HTML for display"""
    if not latex_text:
        return ""
    
    html = latex_text
    
    # Convert \section*{...} to <h2>...</h2>
    html = re.sub(r'\\section\*\s*\{([^}]+)\}', r'<h2>\1</h2>', html)
    
    # Convert \subsection*{...} to <h3>...</h3>
    html = re.sub(r'\\subsection\*\s*\{([^}]+)\}', r'<h3>\1</h3>', html)
    
    # Convert \textbf{...} to <strong>...</strong>
    html = re.sub(r'\\textbf\s*\{([^}]+)\}', r'<strong>\1</strong>', html)
    
    # Convert \textit{...} to <em>...</em>
    html = re.sub(r'\\textit\s*\{([^}]+)\}', r'<em>\1</em>', html)
    
    # Convert \texttt{...} to <code>...</code>
    html = re.sub(r'\\texttt\s*\{([^}]+)\}', r'<code>\1</code>', html)
    
    # Handle \begin{itemize}...\end{itemize}
    html = re.sub(r'\\begin\{itemize\}', '<ul>', html)
    html = re.sub(r'\\end\{itemize\}', '</ul>', html)
    
    # Handle \begin{enumerate}...\end{enumerate}
    html = re.sub(r'\\begin\{enumerate\}', '<ol>', html)
    html = re.sub(r'\\end\{enumerate\}', '</ol>', html)
    
    # Convert \item to <li>
    html = re.sub(r'\\item\s+', '<li>', html)
    
    # Close li tags before next \item or closing tags
    html = re.sub(r'(<li>.*?)(?=<li>|</ul>|</ol>)', r'\1</li>', html, flags=re.DOTALL)
    
    # Handle \begin{center}...\end{center}
    html = re.sub(r'\\begin\{center\}', '<div style="text-align:center;">', html)
    html = re.sub(r'\\end\{center\}', '</div>', html)
    
    # Handle \begin{tabular}...\end{tabular} - convert to HTML table
    def convert_tabular(match):
        content = match.group(1)
        # Extract table content and convert to HTML table
        rows = [r.strip() for r in content.split('\\\\') if r.strip()]
        html_rows = []
        for row in rows:
            cells = [c.strip() for c in row.split('&')]
            # Check if this is a header row (first row)
            is_header = rows.index(row) == 0
            row_html = '<tr>'
            for cell in cells:
                tag = 'th' if is_header else 'td'
                row_html += f'<{tag}>{cell}</{tag}>'
            row_html += '</tr>'
            html_rows.append(row_html)
        return '<table border="1" style="border-collapse:collapse;width:100%;">' + ''.join(html_rows) + '</table>'
    
    html = re.sub(r'\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}', convert_tabular, html, flags=re.DOTALL)
    
    # Handle \hline (table lines) - already handled by border
    html = html.replace('\\hline', '')
    
    # Convert $...$ to <span> with katex class (frontend will render it)
    html = re.sub(r'\$([^$\n]+?)\$', r'<span class="katex-math">\1</span>', html)
    
    # Handle line breaks
    html = html.replace('\\\\', '<br/>')
    
    # Remove any remaining backslashes at line starts
    html = re.sub(r'^\s*\\', '', html, flags=re.MULTILINE)
    
    # Convert blank lines to paragraphs
    paragraphs = html.split('\n\n')
    html_paras = []
    for para in paragraphs:
        para = para.strip()
        if para and not para.startswith('<'):
            para = f'<p>{para}</p>'
        html_paras.append(para)
    html = '\n'.join(html_paras)
    
    return html

def get_seed_puzzle_names(riddles_dir):
    """
    Get the set of puzzle names that are defined in the riddles/ directory.
    These are the 'seed' puzzles that should be imported/updated.
    """
    seed_names = set()
    if not os.path.exists(riddles_dir):
        return seed_names
    
    for filename in os.listdir(riddles_dir):
        if not filename.endswith('_config.json'):
            continue
        config_path = os.path.join(riddles_dir, filename)
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            puzzle_name = cfg.get('puzzle', {}).get('name', '')
            if puzzle_name:
                seed_names.add(puzzle_name)
        except Exception:
            pass
    return seed_names

def clean_database(conn):
    """
    Clears ratings and test cases for seed puzzles (for fresh re-import).
    DOES NOT delete puzzles - preserves user-created puzzles.
    Seed puzzles will be updated in-place if they exist.
    """
    print("Cleaning re-importable data...")
    c = conn.cursor()
    
    # Get seed puzzle IDs to clear their test cases
    seed_names = get_seed_puzzle_names(RIDDLES_DIR)
    if seed_names:
        placeholders = ','.join('?' * len(seed_names))
        try:
            # Clear test cases for seed puzzles only
            c.execute(
                f"DELETE FROM puzzle_test_cases WHERE puzzle_id IN "
                f"(SELECT id FROM puzzles WHERE name IN ({placeholders}))",
                list(seed_names)
            )
            print(f"  - Cleared test cases for seed puzzles")
            
            # Clear ratings for seed puzzles only
            c.execute(
                f"DELETE FROM rating WHERE puzzle_id IN "
                f"(SELECT id FROM puzzles WHERE name IN ({placeholders}))",
                list(seed_names)
            )
            print(f"  - Cleared ratings for seed puzzles")
        except sqlite3.OperationalError as e:
            print(f"  - Warning: Could not clear seed puzzle data: {e}")
    
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
    
    instructions_text = ""
    if os.path.exists(instructions_path):
        with open(instructions_path, 'r', encoding='utf-8') as f:
            instructions_text = f.read()
        
        # For .tex files, keep raw LaTeX - frontend will render with KaTeX
        # (don't convert to HTML - KaTeX handles LaTeX natively)

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
    
    # Get description from config file or use instructions_text as fallback
    description = puzzle_data.get('description', instructions_text)
    
    c = conn.cursor()
    
    # Check if puzzle already exists by name — preserve its ID for solve_attempts
    existing = c.execute("SELECT id FROM puzzles WHERE name = ?", (puzzle_data['name'],)).fetchone()
    
    if existing:
        puzzle_id = existing[0]
        # Update description/budget/instructions/config but keep the same ID
        c.execute("""
            UPDATE puzzles SET
                description=?, instructions=?, budget=?, time_limit_seconds=?,
                default_gate_set=?, difficulty=?,
                total_gate_count=?, min_cycles=?, max_cycles=?
            WHERE id=?
        """, (
            description,
            instructions_text,
            puzzle_data.get('budget', 0),
            puzzle_data.get('time_limit_seconds'),
            gates_json,
            difficulty,
            puzzle_data.get('total_gate_count'),
            puzzle_data.get('min_cycles'),
            puzzle_data.get('max_cycles'),
            puzzle_id
        ))
        # Clear old test cases for this puzzle (they get re-imported below)
        c.execute("DELETE FROM puzzle_test_cases WHERE puzzle_id=?", (puzzle_id,))
    else:
        # INSERT new puzzle
        c.execute("""
            INSERT INTO puzzles (
                name, creator_user_id, description, instructions, status, budget, 
                time_limit_seconds, difficulty, default_gate_set, rating_count, 
                avg_difficulty, avg_fun, avg_clearness,
                total_gate_count, min_cycles, max_cycles,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            puzzle_data['name'],
            creator_id,
            description,
            instructions_text,
            'published',
            puzzle_data.get('budget', 0),
            puzzle_data.get('time_limit_seconds'),
            difficulty,
            gates_json,
            0, 0.0, 0.0, 0.0,
            puzzle_data.get('total_gate_count'),
            puzzle_data.get('min_cycles'),
            puzzle_data.get('max_cycles'),
            utcnow()
        ))
        puzzle_id = c.lastrowid
    
    # INSERT Test Cases
    for tc in test_cases:
        # Determine test case kind - could be 'blackbox', 'gate_limit', or 'gate_count_limit'
        kind = tc.get('kind', 'blackbox')
        
        # Handle sequential variation
        inputs = tc.get('inputs')
        expected_outputs = tc.get('expected_outputs')
        input_stream = tc.get('input_stream')
        expected_output_stream = tc.get('expected_output_stream')
        
        # Handle test case data based on kind
        inputs = tc.get('inputs')
        expected_outputs = tc.get('expected_outputs')
        input_stream = tc.get('input_stream')
        expected_output_stream = tc.get('expected_output_stream')
        
        # IMPORTANT: For stream test cases, normalize input_stream to dict format
        # Puzzle 3 uses: [1, 1, 1] (list of ints)
        # Puzzle 7 uses: [{"input_0": 0}, ...] (list of dicts)
        # We need both to be converted to the dict format for consistency
        
        if kind == 'stream' and input_stream:
            # Normalize input_stream to list of dicts if it's currently list of ints
            if input_stream and isinstance(input_stream[0], (int, float)):
                # Convert [1, 1, 1] to [{"X": 1}, {"X": 1}, {"X": 1}]
                input_names = puzzle_data.get('inputs') or puzzle_data.get('input') or []
                input_name = input_names[0] if input_names else 'input_0'
                input_stream = [{input_name: val} for val in input_stream]
            
            # For stream: use input_stream and expected_output_stream directly
            # Leave inputs and expected_outputs empty
            inputs = {}
            expected_outputs = {}
        else:
            # For blackbox/other kinds: try to use inputs/expected_outputs
            # Fallback conversion only for backward compatibility
            if inputs is None and input_stream is not None:
                # It's a stream (list), map it to input names if possible
                # Get input names from puzzle config
                input_names = puzzle_data.get('inputs') or puzzle_data.get('input') or []
                if len(input_names) == 1:
                    # Single input case (e.g. "X")
                    inputs = {input_names[0]: input_stream}
                else:
                    # Fallback if multiple inputs or unknown structure
                    inputs = {"IN": input_stream}
            
            # Map expected_output_stream to expected_outputs if needed
            if expected_outputs is None and expected_output_stream is not None:
                expected_outputs = expected_output_stream
            
        inputs_json = json.dumps(inputs or {})
        expected_outputs_json = json.dumps(expected_outputs or {})
        input_stream_json = json.dumps(input_stream) if input_stream else None
        expected_output_stream_json = json.dumps(expected_output_stream) if expected_output_stream else None
        
        # Handle gate limit test cases
        gate_name = None
        gate_limit = None
        
        if kind == 'gate_limit':
            # New structure: gate_name and gate_limit
            gate_name = tc.get('gate_name')
            gate_limit = tc.get('gate_limit')
        
        # Note: Constraint values (max_gate_count, min_cycles, max_cycles) are now stored
        # at the puzzle level, not per test case. Test cases only mark the constraint KIND.
        
        c.execute("""
            INSERT INTO puzzle_test_cases (
                puzzle_id, kind, inputs, expected_outputs, input_stream, expected_output_stream, gate_name, gate_limit, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            puzzle_id,
            kind,
            inputs_json,
            expected_outputs_json,
            input_stream_json,
            expected_output_stream_json,
            gate_name,
            gate_limit,
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
        
        # 3. Build set of puzzle names that were deleted (should not be re-imported)
        # Query both user_deleted_puzzles and admin_deleted_puzzles tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_deleted_puzzles (
                name TEXT PRIMARY KEY,
                deleted_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_deleted_puzzles (
                name TEXT PRIMARY KEY,
                deleted_at TEXT NOT NULL
            )
        """)
        conn.commit()
        
        deleted_names = set()
        try:
            # Get user deletions
            user_deleted = conn.execute("SELECT name FROM user_deleted_puzzles").fetchall()
            deleted_names.update(r[0] for r in user_deleted)
            # Get admin deletions
            admin_deleted = conn.execute("SELECT name FROM admin_deleted_puzzles").fetchall()
            deleted_names.update(r[0] for r in admin_deleted)
        except sqlite3.OperationalError:
            pass
        if deleted_names:
            print(f"  Skipping {len(deleted_names)} deleted puzzle(s).")

        # 4. Iterate and insert/update ALL riddles from files,
        #    but skip any whose name was deleted (user or admin).
        print("Importing riddles...")
        count = 0
        for filename in os.listdir(RIDDLES_DIR):
            if not filename.endswith('_config.json'):
                continue
            config_path = os.path.join(RIDDLES_DIR, filename)

            # Read the puzzle name from the config to check against deleted list
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                puzzle_name = cfg.get('puzzle', {}).get('name', '')
            except Exception:
                puzzle_name = ''

            if puzzle_name in deleted_names:
                print(f"  Skipped (admin-deleted): {puzzle_name}")
                continue

            base_name = filename.replace('_config.json', '')
            instr_path = os.path.join(RIDDLES_DIR, f"{base_name}_instructions.tex")
            
            # Fallback to .md if .tex not found
            if not os.path.exists(instr_path):
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
