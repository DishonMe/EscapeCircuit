import sqlite3
import sys
import os
from pathlib import Path

# Add src to path if needed (though running from root usually works if we import from Backend)
# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole

def seed_admin():
    # Use same path as Backend/main.py: parent.parent.parent / "escape_circuit.db"
    db_path = Path(__file__).parent.parent / "escape_circuit.db"
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    repo = UserRepo(conn)
    
    username = "admin"
    password = "password123"

    # Check if exists
    existing = repo.get_by_username(username)
    if existing:
        print(f"User '{username}' already exists (ID: {existing.id}).")
        # Ensure role is admin
        if existing.role != UserRole.ADMIN:
             print("Updating role to ADMIN...")
             repo.update_role(existing.id, UserRole.ADMIN)
        
        # Force password reset
        print("Resetting password to 'password123'...")
        salt = os.urandom(16)
        pw_hash = UserRepo._hash_password(password, salt)
        conn.execute("UPDATE users SET pw_salt=?, pw_hash=? WHERE id=?", (salt, pw_hash, existing.id))
        conn.commit()
    else:
        # Create
        print(f"Creating user '{username}'...")
        # Use a temporary ID; repo will assign the real one
        admin_user = User(id=1, username=username, role=UserRole.ADMIN, xp=0)
        created = repo.create(admin_user, password)
        print(f"User '{username}' created successfully with ID: {created.id}.")
        conn.commit()

    conn.close()
    print("Done.")

if __name__ == "__main__":
    seed_admin()
