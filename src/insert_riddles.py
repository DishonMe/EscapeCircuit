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

def clean_database(conn):
    """
    Clears ratings, test cases, and puzzles (for fresh re-import).
    Also resets AUTOINCREMENT sequence counters so IDs start at 1.
    """
    print("Cleaning re-importable data...")
    c = conn.cursor()
    
    # Clear old data
    for table in ["rating", "puzzle_test_cases", "puzzles"]:
        try:
            c.execute(f"DELETE FROM {table}")
            print(f"  - Cleared table: {table}")
        except sqlite3.OperationalError as e:
            print(f"  - Warning: Could not clear {table} (maybe doesn't exist): {e}")
    
    # Reset AUTOINCREMENT sequence so IDs start at 1
    try:
        c.execute("DELETE FROM sqlite_sequence WHERE name IN ('puzzles', 'puzzle_test_cases')")
        print(f"  - Reset ID sequences for puzzles and puzzle_test_cases")
    except sqlite3.OperationalError:
        pass  # sqlite_sequence table may not exist yet
            
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
        
        # 3. Build set of puzzle names that were admin-deleted (should not be re-imported)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deleted_puzzle_names (
                name TEXT PRIMARY KEY
            )
        """)
        conn.commit()
        deleted_names = set()
        try:
            rows = conn.execute("SELECT name FROM deleted_puzzle_names").fetchall()
            deleted_names = {r[0] for r in rows}
        except sqlite3.OperationalError:
            pass
        if deleted_names:
            print(f"  Skipping {len(deleted_names)} admin-deleted puzzle(s).")

        # 4. Iterate and insert/update ALL riddles from files,
        #    but skip any whose name was admin-deleted.
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
