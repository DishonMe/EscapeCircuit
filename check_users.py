import sqlite3
conn = sqlite3.connect('escape_circuit.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT id, username, pw_hash, pw_salt FROM users').fetchall()
print('Users in DB:')
for r in rows:
    print(f'  ID {r["id"]}: {r["username"]} (hash exists={bool(r["pw_hash"])}, salt exists={bool(r["pw_salt"])})')
conn.close()
