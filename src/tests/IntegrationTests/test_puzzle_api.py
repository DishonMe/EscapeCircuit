"""Integration tests for the Puzzle API (/puzzles endpoints)."""
from .conftest import register_and_login, auth_header, register_user


def _register_creator(client, conn, username="creator"):
    """Register a user and make them a creator (required to create puzzles)."""
    token = register_and_login(client, username)
    me = client.get("/users/me", headers=auth_header(token)).json()
    conn.execute("UPDATE users SET role = 'creator' WHERE id = ?", (me["id"],))
    conn.commit()
    return token


def _create_puzzle(client, token, name="Test Puzzle"):
    """Helper to create a puzzle via API."""
    resp = client.post("/puzzles", json={
        "name": name,
        "description": "A test puzzle",
        "budget": 100,
        "default_gate_set": ["AND", "OR", "NOT"],
        "difficulty": "EASY",
    }, headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestPuzzleCreate:
    def test_create_puzzle(self, client, conn):
        token = _register_creator(client, conn)
        body = _create_puzzle(client, token)
        assert "id" in body
        assert body["name"] == "Test Puzzle"

    def test_create_puzzle_rejects_duplicate_name(self, client, conn):
        token = _register_creator(client, conn)
        _create_puzzle(client, token, "Unique Puzzle")

        resp = client.post("/puzzles", json={
            "name": "Unique Puzzle",
            "description": "Another puzzle",
            "budget": 100,
            "default_gate_set": ["AND", "OR", "NOT"],
            "difficulty": "EASY",
        }, headers=auth_header(token))
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_create_puzzle_rejects_name_too_long(self, client, conn):
        token = _register_creator(client, conn)
        resp = client.post("/puzzles", json={
            "name": "x" * 101,
            "description": "Y",
            "budget": 10,
            "default_gate_set": ["AND"],
            "difficulty": "EASY",
        }, headers=auth_header(token))
        assert resp.status_code == 400
        assert "100 characters" in resp.json()["detail"]

    def test_create_puzzle_rejects_description_too_long(self, client, conn):
        token = _register_creator(client, conn)
        resp = client.post("/puzzles", json={
            "name": "Long Description Puzzle",
            "description": "d" * 2001,
            "budget": 10,
            "default_gate_set": ["AND"],
            "difficulty": "EASY",
        }, headers=auth_header(token))
        assert resp.status_code == 400
        assert "2000 characters" in resp.json()["detail"]

    def test_create_puzzle_no_auth(self, client):
        resp = client.post("/puzzles", json={
            "name": "X", "description": "Y", "budget": 10,
            "default_gate_set": ["AND"], "difficulty": "EASY",
        })
        assert resp.status_code == 401

    def test_create_puzzle_solver_forbidden(self, client):
        token = register_and_login(client, "solver")
        resp = client.post("/puzzles", json={
            "name": "X", "description": "Y", "budget": 10,
            "default_gate_set": ["AND"], "difficulty": "EASY",
        }, headers=auth_header(token))
        assert resp.status_code == 400


class TestPuzzleGet:
    def test_get_puzzle(self, client, conn):
        token = _register_creator(client, conn)
        created = _create_puzzle(client, token)
        pid = int(created["id"])

        resp = client.get(f"/puzzles/{pid}", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Puzzle"

    def test_get_nonexistent(self, client):
        token = register_and_login(client)
        resp = client.get("/puzzles/999", headers=auth_header(token))
        assert resp.status_code == 404


class TestPuzzleUpdate:
    def test_update_puzzle(self, client, conn):
        token = _register_creator(client, conn)
        created = _create_puzzle(client, token)
        pid = int(created["id"])

        resp = client.patch(f"/puzzles/{pid}", json={
            "name": "Updated Name",
            "description": "Updated desc",
        }, headers=auth_header(token))
        assert resp.status_code == 200

        got = client.get(f"/puzzles/{pid}", headers=auth_header(token))
        assert got.json()["name"] == "Updated Name"


class TestPuzzlePublish:
    def test_publish_requires_test_cases(self, client, conn):
        token = _register_creator(client, conn)
        created = _create_puzzle(client, token)
        pid = int(created["id"])

        resp = client.post(f"/puzzles/{pid}/publish", headers=auth_header(token))
        assert resp.status_code == 403

    def test_add_test_case(self, client, conn):
        token = _register_creator(client, conn)
        created = _create_puzzle(client, token)
        pid = int(created["id"])

        resp = client.post(f"/puzzles/{pid}/testcases", json={
            "kind": "blackbox",
            "inputs": {"A": 0, "B": 0},
            "expected_outputs": {"OUT": 0},
        }, headers=auth_header(token))
        assert resp.status_code == 200

    def test_list_test_cases(self, client, conn):
        token = _register_creator(client, conn)
        created = _create_puzzle(client, token)
        pid = int(created["id"])

        client.post(f"/puzzles/{pid}/testcases", json={
            "kind": "blackbox",
            "inputs": {"A": 0}, "expected_outputs": {"OUT": 0},
        }, headers=auth_header(token))

        resp = client.get(f"/puzzles/{pid}/testcases", headers=auth_header(token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestPuzzleDelete:
    def test_delete_own_puzzle(self, client, conn):
        token = _register_creator(client, conn)
        created = _create_puzzle(client, token)
        pid = int(created["id"])

        resp = client.delete(f"/puzzles/{pid}", headers=auth_header(token))
        assert resp.status_code == 200

        resp = client.get(f"/puzzles/{pid}", headers=auth_header(token))
        assert resp.status_code == 404


class TestPuzzleBrowse:
    def test_browse_published(self, client):
        token = register_and_login(client)
        resp = client.get("/puzzles", headers=auth_header(token))
        assert resp.status_code == 200

    def test_my_puzzles(self, client, conn):
        token = _register_creator(client, conn)
        _create_puzzle(client, token, "P1")
        _create_puzzle(client, token, "P2")

        resp = client.get("/puzzles/my-puzzles/list", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2

    def test_search_puzzles(self, client):
        token = register_and_login(client)
        resp = client.get("/puzzles/search?q=nonexistent", headers=auth_header(token))
        assert resp.status_code == 200

    def test_browse_only_experienced_fun_filters_without_bounds(self, client, conn):
        creator_token = _register_creator(client, conn, "exp_filter_creator")

        p_non = _create_puzzle(client, creator_token, "NonExpOnly")
        p_exp = _create_puzzle(client, creator_token, "ExpRated")

        conn.execute(
            "UPDATE puzzles SET status='published' WHERE id IN (?, ?)",
            (int(p_non["id"]), int(p_exp["id"])),
        )

        conn.execute(
            "INSERT INTO ratings (puzzle_id, user_id, difficulty, fun, clearness, created_at, is_experienced_at_rating, rating_xp_awarded) VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?)",
            (int(p_non["id"]), 2001, 2, 2, 2, 0, 0),
        )
        conn.execute(
            "INSERT INTO ratings (puzzle_id, user_id, difficulty, fun, clearness, created_at, is_experienced_at_rating, rating_xp_awarded) VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?)",
            (int(p_exp["id"]), 2002, 5, 5, 5, 1, 0),
        )
        conn.commit()

        viewer_token = register_and_login(client, "exp_filter_viewer")
        resp = client.get("/puzzles?only_experienced_fun=true&limit=50", headers=auth_header(viewer_token))
        assert resp.status_code == 200

        data = resp.json().get("data", [])
        names = {p.get("name") for p in data}
        assert "ExpRated" in names
        assert "NonExpOnly" not in names

    def test_browse_filters_by_creator_experience_level(self, client, conn):
        exp_creator_token = _register_creator(client, conn, "exp_creator")
        exp_creator_me = client.get("/users/me", headers=auth_header(exp_creator_token)).json()

        inxp_creator_token = _register_creator(client, conn, "inxp_creator")
        inxp_creator_me = client.get("/users/me", headers=auth_header(inxp_creator_token)).json()

        conn.execute("UPDATE users SET xp=? WHERE id=?", (2000, int(exp_creator_me["id"])))
        conn.execute("UPDATE users SET xp=? WHERE id=?", (100, int(inxp_creator_me["id"])))

        p_exp = _create_puzzle(client, exp_creator_token, "PuzzleByExperiencedCreator")
        p_inxp = _create_puzzle(client, inxp_creator_token, "PuzzleByInexperiencedCreator")

        conn.execute(
            "UPDATE puzzles SET status='published' WHERE id IN (?, ?)",
            (int(p_exp["id"]), int(p_inxp["id"])),
        )
        conn.commit()

        viewer_token = register_and_login(client, "creator_exp_filter_viewer")

        experienced_resp = client.get(
            "/puzzles?creator_experience_level=experienced&limit=50",
            headers=auth_header(viewer_token),
        )
        assert experienced_resp.status_code == 200
        experienced_names = {p.get("name") for p in experienced_resp.json().get("data", [])}
        assert "PuzzleByExperiencedCreator" in experienced_names
        assert "PuzzleByInexperiencedCreator" not in experienced_names

        inexperienced_resp = client.get(
            "/puzzles?creator_experience_level=inexperienced&limit=50",
            headers=auth_header(viewer_token),
        )
        assert inexperienced_resp.status_code == 200
        inexperienced_names = {p.get("name") for p in inexperienced_resp.json().get("data", [])}
        assert "PuzzleByInexperiencedCreator" in inexperienced_names
        assert "PuzzleByExperiencedCreator" not in inexperienced_names
