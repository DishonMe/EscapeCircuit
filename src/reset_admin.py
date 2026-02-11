import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'escape_circuit.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

row = conn.execute("SELECT id, username, xp FROM users WHERE LOWER(username)='admin'").fetchone()
if not row:
    print("Admin user not found!")
    conn.close()
    exit(1)

admin_id = row["id"]
print(f"Admin found: id={admin_id}, current xp={row['xp']}")

# Delete all solve attempts for admin
cur1 = conn.execute("DELETE FROM solve_attempts WHERE user_id=?", (admin_id,))
print(f"Deleted {cur1.rowcount} solve_attempts")

# Delete all puzzle progress for admin
cur2 = conn.execute("DELETE FROM puzzle_progress WHERE user_id=?", (admin_id,))
print(f"Deleted {cur2.rowcount} puzzle_progress records")

# Reset XP to 0
conn.execute("UPDATE users SET xp=0 WHERE id=?", (admin_id,))
print("Reset Admin xp=0, level=0")

conn.commit()
conn.close()
print("Done! Admin is back to a fresh start.")
