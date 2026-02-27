"""
System tests: Admin moderation workflow.

Workflow: admin assigns creator role -> creator creates puzzle -> admin
deletes puzzle -> audit log records everything -> admin removes creator role.
"""
from .conftest import (
    auth_header, make_admin, make_creator, register_and_login,
    create_puzzle, get_user_info,
)


class TestAdminCreatorManagement:
    """Admin assigns and removes creator role, affecting puzzle creation."""

    def test_assign_creator_then_create_puzzle(self, client, conn):
        admin_token = make_admin(client, conn, "admin1")

        # Register a normal solver
        solver_token = register_and_login(client, "promoted_user")
        solver_info = get_user_info(client, solver_token)
        solver_id = solver_info["id"]
        assert solver_info["role"] == "solver"

        # Solver cannot create puzzles
        resp = client.post("/puzzles", json={
            "name": "Should Fail",
            "description": "d",
            "budget": 10,
            "default_gate_set": ["AND"],
            "difficulty": "EASY",
        }, headers=auth_header(solver_token))
        assert resp.status_code == 400

        # Admin sends creator invitation (sets to pending_creator)
        resp = client.post("/admin/assign-creator", json={
            "target_user_id": solver_id,
        }, headers=auth_header(admin_token))
        assert resp.status_code == 200

        # Verify role is now pending_creator
        solver_info = get_user_info(client, solver_token)
        assert solver_info["role"] == "pending_creator"

        # Simulate user accepting invite (sets role to creator)
        conn.execute("UPDATE users SET role = 'creator' WHERE id = ?",
                     (solver_id,))

        # Now puzzle creation works
        puzzle = create_puzzle(client, solver_token, name="Creator Puzzle")
        assert puzzle["name"] == "Creator Puzzle"

    def test_remove_creator_role(self, client, conn):
        admin_token = make_admin(client, conn, "admin2")
        creator_token = make_creator(client, conn, "demoted_creator")
        creator_info = get_user_info(client, creator_token)
        creator_id = creator_info["id"]

        # Admin removes creator role
        resp = client.post("/admin/remove-creator", json={
            "target_user_id": creator_id,
        }, headers=auth_header(admin_token))
        assert resp.status_code == 200

        # Verify role reverted to solver
        creator_info = get_user_info(client, creator_token)
        assert creator_info["role"] == "solver"


class TestAdminPuzzleManagement:
    """Admin can see and delete any puzzle."""

    def test_admin_deletes_puzzle(self, client, conn):
        admin_token = make_admin(client, conn, "admin3")
        creator_token = make_creator(client, conn, "puzzle_creator")

        puzzle = create_puzzle(client, creator_token, name="Deletable Puzzle")
        pid = int(puzzle["id"])

        # Admin lists all puzzles
        resp = client.get("/admin/puzzles", headers=auth_header(admin_token))
        assert resp.status_code == 200
        all_ids = [int(p["id"]) for p in resp.json()["data"]]
        assert pid in all_ids

        # Admin deletes the puzzle
        resp = client.delete(f"/admin/puzzles/{pid}",
                             headers=auth_header(admin_token))
        assert resp.status_code == 200

        # Puzzle no longer accessible
        resp = client.get(f"/puzzles/{pid}",
                          headers=auth_header(creator_token))
        assert resp.status_code == 404


class TestAuditLog:
    """Admin actions are recorded in the audit log."""

    def test_audit_log_records_assign_and_remove(self, client, conn):
        admin_token = make_admin(client, conn, "audit_admin")
        user_token = register_and_login(client, "audit_user")
        user_info = get_user_info(client, user_token)
        user_id = user_info["id"]

        # Assign creator (sets to pending_creator)
        client.post("/admin/assign-creator", json={"target_user_id": user_id},
                    headers=auth_header(admin_token))

        # Remove creator (removes pending_creator back to solver)
        client.post("/admin/remove-creator", json={"target_user_id": user_id},
                    headers=auth_header(admin_token))

        # Check audit log
        resp = client.get("/admin/audit-log", headers=auth_header(admin_token))
        assert resp.status_code == 200
        entries = resp.json()
        actions = [e["action_type"] for e in entries]
        assert "assign_creator" in actions
        assert "remove_creator" in actions

    def test_audit_log_records_puzzle_delete(self, client, conn):
        admin_token = make_admin(client, conn, "audit_admin2")
        creator_token = make_creator(client, conn, "audit_creator")

        puzzle = create_puzzle(client, creator_token, name="Audit Puzzle")
        pid = int(puzzle["id"])

        # Admin deletes puzzle
        client.delete(f"/admin/puzzles/{pid}",
                      headers=auth_header(admin_token))

        # Audit log has delete_puzzle entry
        resp = client.get("/admin/audit-log", headers=auth_header(admin_token))
        entries = resp.json()
        actions = [e["action_type"] for e in entries]
        assert "delete_puzzle" in actions

    def test_non_admin_cannot_access_audit_log(self, client):
        user_token = register_and_login(client, "nonadmin")
        resp = client.get("/admin/audit-log", headers=auth_header(user_token))
        assert resp.status_code == 403
