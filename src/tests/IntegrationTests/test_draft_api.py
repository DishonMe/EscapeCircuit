"""Integration tests for the Draft API (/puzzles/{id}/draft endpoints)."""
import time
from .conftest import register_and_login, auth_header


def _register_creator(client, conn, username="creator"):
    """Register a user and make them a creator (required to create puzzles)."""
    token = register_and_login(client, username)
    me = client.get("/users/me", headers=auth_header(token)).json()
    conn.execute("UPDATE users SET role = 'creator' WHERE id = ?", (me["id"],))
    conn.commit()
    return token


def _create_puzzle(client, token):
    resp = client.post("/puzzles", json={
        "name": "Draft Puzzle",
        "description": "d",
        "budget": 10,
        "default_gate_set": ["AND"],
        "difficulty": "EASY",
    }, headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestDraftCRUD:
    def test_save_and_get_draft(self, client, conn):
        token = _register_creator(client, conn)
        puzzle = _create_puzzle(client, token)
        pid = int(puzzle["id"])

        # Save draft
        resp = client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"wip": true}',
        }, headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert "updated_at" in resp.json()

        # Get draft
        resp = client.get(f"/puzzles/{pid}/draft", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["state_json"] == '{"wip": true}'

    def test_get_nonexistent_draft(self, client, conn):
        token = _register_creator(client, conn)
        puzzle = _create_puzzle(client, token)
        pid = int(puzzle["id"])

        resp = client.get(f"/puzzles/{pid}/draft", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["state_json"] is None

    def test_delete_draft(self, client, conn):
        token = _register_creator(client, conn)
        puzzle = _create_puzzle(client, token)
        pid = int(puzzle["id"])

        # Save then delete
        client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"x": 1}',
        }, headers=auth_header(token))

        resp = client.delete(f"/puzzles/{pid}/draft", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Should be empty again
        resp = client.get(f"/puzzles/{pid}/draft", headers=auth_header(token))
        assert resp.json()["state_json"] is None

    def test_overwrite_draft(self, client, conn):
        token = _register_creator(client, conn)
        puzzle = _create_puzzle(client, token)
        pid = int(puzzle["id"])

        client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"v": 1}',
        }, headers=auth_header(token))

        client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"v": 2}',
        }, headers=auth_header(token))

        resp = client.get(f"/puzzles/{pid}/draft", headers=auth_header(token))
        assert resp.json()["state_json"] == '{"v": 2}'


class TestDraftConflict:
    def test_optimistic_concurrency_conflict(self, client, conn):
        token = _register_creator(client, conn)
        puzzle = _create_puzzle(client, token)
        pid = int(puzzle["id"])

        # Save initial draft
        save1 = client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"v": 1}',
        }, headers=auth_header(token)).json()
        ts = save1["updated_at"]

        # Small delay to ensure timestamps differ beyond tolerance (1ms)
        time.sleep(0.01)

        # Save again with the correct timestamp (should work)
        save2 = client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"v": 2}',
            "expected_updated_at": ts,
        }, headers=auth_header(token))
        assert save2.status_code == 200

        # Save with the OLD timestamp (should conflict)
        save3 = client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"v": 3}',
            "expected_updated_at": ts,  # stale
        }, headers=auth_header(token))
        assert save3.status_code == 409


class TestDraftAuth:
    def test_no_token(self, client):
        resp = client.get("/puzzles/1/draft")
        assert resp.status_code == 401

    def test_user_isolation(self, client, conn):
        token_a = _register_creator(client, conn, "alice")
        token_b = register_and_login(client, "bob")
        puzzle = _create_puzzle(client, token_a)
        pid = int(puzzle["id"])

        # Alice saves a draft
        client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"alice": true}',
        }, headers=auth_header(token_a))

        # Bob should see no draft for the same puzzle
        resp = client.get(f"/puzzles/{pid}/draft", headers=auth_header(token_b))
        assert resp.json()["state_json"] is None
