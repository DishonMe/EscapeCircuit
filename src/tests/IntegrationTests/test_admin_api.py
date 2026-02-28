"""Integration tests for the Admin API (/admin endpoints)."""
import sqlite3
from .conftest import register_and_login, auth_header, register_user


def _make_admin(conn: sqlite3.Connection, user_id: int):
    """Directly set a user's role to admin in the DB."""
    conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
    conn.commit()


class TestAdminAssignCreator:
    def test_assign_creator(self, client, conn):
        admin_token = register_and_login(client, "admin_user")
        # Get admin user_id
        me = client.get("/users/me", headers=auth_header(admin_token)).json()
        _make_admin(conn, me["id"])

        # Register a solver
        solver_data = register_user(client, "solver_user")
        solver_id = solver_data["user"]["id"]

        resp = client.post("/admin/assign-creator", json={
            "target_user_id": int(solver_id),
        }, headers=auth_header(admin_token))
        assert resp.status_code == 200

    def test_assign_creator_non_admin(self, client):
        token = register_and_login(client, "normie")
        other = register_user(client, "other")

        resp = client.post("/admin/assign-creator", json={
            "target_user_id": int(other["user"]["id"]),
        }, headers=auth_header(token))
        assert resp.status_code == 403

    def test_remove_creator(self, client, conn):
        admin_token = register_and_login(client, "admin_user")
        me = client.get("/users/me", headers=auth_header(admin_token)).json()
        _make_admin(conn, me["id"])

        # Register a user and make them pending_creator
        solver_data = register_user(client, "creator_user")
        solver_id = int(solver_data["user"]["id"])
        conn.execute("UPDATE users SET role = 'creator' WHERE id = ?", (solver_id,))
        conn.commit()

        resp = client.post("/admin/remove-creator", json={
            "target_user_id": solver_id,
        }, headers=auth_header(admin_token))
        assert resp.status_code == 200


class TestAdminPuzzles:
    def test_list_puzzles_admin(self, client, conn):
        admin_token = register_and_login(client, "admin_user")
        me = client.get("/users/me", headers=auth_header(admin_token)).json()
        _make_admin(conn, me["id"])

        resp = client.get("/admin/puzzles", headers=auth_header(admin_token))
        assert resp.status_code == 200

    def test_list_puzzles_non_admin(self, client):
        token = register_and_login(client, "normie")
        resp = client.get("/admin/puzzles", headers=auth_header(token))
        assert resp.status_code == 403

    def test_delete_puzzle_admin(self, client, conn):
        admin_token = register_and_login(client, "admin_user")
        me = client.get("/users/me", headers=auth_header(admin_token)).json()
        _make_admin(conn, me["id"])

        # Create a puzzle as admin
        created = client.post("/puzzles", json={
            "name": "To Delete",
            "description": "desc",
            "budget": 10,
            "default_gate_set": ["AND"],
            "difficulty": "EASY",
        }, headers=auth_header(admin_token)).json()

        resp = client.delete(
            f"/admin/puzzles/{int(created['id'])}",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200


class TestAuditLog:
    def test_get_audit_log(self, client, conn):
        admin_token = register_and_login(client, "admin_user")
        me = client.get("/users/me", headers=auth_header(admin_token)).json()
        _make_admin(conn, me["id"])

        resp = client.get("/admin/audit-log", headers=auth_header(admin_token))
        assert resp.status_code == 200

    def test_audit_log_non_admin(self, client):
        token = register_and_login(client, "normie")
        resp = client.get("/admin/audit-log", headers=auth_header(token))
        assert resp.status_code == 403

    def test_audit_log_records_actions(self, client, conn):
        admin_token = register_and_login(client, "admin_user")
        me = client.get("/users/me", headers=auth_header(admin_token)).json()
        _make_admin(conn, me["id"])

        solver_data = register_user(client, "solver")
        solver_id = int(solver_data["user"]["id"])

        # Perform an auditable action
        client.post("/admin/assign-creator", json={
            "target_user_id": solver_id,
        }, headers=auth_header(admin_token))

        # Check audit log
        resp = client.get("/admin/audit-log", headers=auth_header(admin_token))
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) >= 1
        assert logs[0]["action_type"] == "assign_creator"
