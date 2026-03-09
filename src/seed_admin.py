import sys
import os
from pathlib import Path

# Add src to path if needed
# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from Backend.PersistantLayer._db import connect
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole

def seed_admin():
    # Use same path as Backend/main.py: parent.parent.parent / "escape_circuit.db"
    db_path = Path(__file__).parent.parent / "escape_circuit.db"
    print(f"Connecting to {db_path}...")
    conn = connect(str(db_path))
    repo = UserRepo(conn)

    username = "admin"
    password = "password123"

    # Check if exists
    existing = repo.get_by_username(username)
    if existing:
        print(f"User {chr(39)}{username}{chr(39)} already exists (ID: {existing.id}).")
        # Ensure role is admin
        if existing.role != UserRole.ADMIN:
             print("Updating role to ADMIN...")
             repo.update_role(existing.id, UserRole.ADMIN)

        # Force password reset
        print("Resetting password to {chr(39)}password123{chr(39)}...")
        salt = os.urandom(16)
        pw_hash = UserRepo._hash_password(password, salt)
        conn.execute("UPDATE users SET pw_salt=?, pw_hash=? WHERE id=?", (salt, pw_hash, existing.id))
        conn.commit()
    else:
        # Create
        print(f"Creating user {chr(39)}{username}{chr(39)}...")
        # Use a temporary ID; repo will assign the real one
        admin_user = User(id=1, username=username, role=UserRole.ADMIN, xp=0)
        created = repo.create(admin_user, password)
        print(f"User {chr(39)}{username}{chr(39)} created successfully with ID: {created.id}.")
        conn.commit()

    conn.close()
    print("Done.")

if __name__ == "__main__":
    seed_admin()
