import io
import sqlite3

from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
import Backend.APILayer.PuzzleController as puzzle_controller_module
import Backend.APILayer.AdminController as admin_controller_module

from .conftest import auth_header, register_and_login


def _make_creator(conn: sqlite3.Connection, user_id: int):
    conn.execute("UPDATE users SET role = 'creator' WHERE id = ?", (user_id,))
    conn.commit()


def _make_admin(conn: sqlite3.Connection, user_id: int):
    conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
    conn.commit()


def _base_config(name="Upload Puzzle", description="desc"):
    return {
        "puzzle": {
            "name": name,
            "description": description,
            "budget": 5,
            "default_gate_set": ["AND", "OR", "NOT"],
            "inputs": ["A", "B"],
            "outputs": ["out"],
        },
        "test_cases": [
            {
                "kind": "blackbox",
                "inputs": {"A": 0, "B": 0},
                "expected_outputs": {"out": 0},
            }
        ],
    }


def _solution():
    return {
        "eval_map": {
            '{"A":0,"B":0}': {"out": 0},
        }
    }


def _multipart_payload(config: dict, instructions_text: str, solution: dict):
    return {
        "config_file": ("puzzle_config.json", io.BytesIO(__import__("json").dumps(config).encode("utf-8")), "application/json"),
        "instructions_file": ("puzzle_instructions.tex", io.BytesIO(instructions_text.encode("utf-8")), "text/plain"),
        "sample_solution_file": ("puzzle_solution.json", io.BytesIO(__import__("json").dumps(solution).encode("utf-8")), "application/json"),
    }


class _CopyGuard:
    def __init__(self):
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("copy2 should not be called on validation failure")


class _InsertGuard:
    def __init__(self):
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("insert_riddle should not be called on validation failure")


class TestPuzzleFormUploadValidation:
    def test_create_puzzle_form_rejects_name_too_long_without_creating_files(self, client, conn, monkeypatch):
        token = register_and_login(client, "upload_creator_name_limit")
        me = client.get("/users/me", headers=auth_header(token)).json()
        _make_creator(conn, me["id"])

        upload_conn = sqlite3.connect(":memory:", check_same_thread=False)
        upload_conn.row_factory = sqlite3.Row
        PuzzleRepo(upload_conn)
        monkeypatch.setattr(puzzle_controller_module, "get_db_conn", lambda: upload_conn)

        copy_guard = _CopyGuard()
        insert_guard = _InsertGuard()
        monkeypatch.setattr(puzzle_controller_module.shutil, "copy2", copy_guard)
        monkeypatch.setattr(puzzle_controller_module, "insert_riddle", insert_guard)

        files = _multipart_payload(
            _base_config(name="x" * 101),
            "short instructions",
            _solution(),
        )

        resp = client.post("/puzzles/create-puzzle-form", files=files, headers=auth_header(token))

        assert resp.status_code == 400
        assert "100 characters" in resp.json()["detail"]
        assert copy_guard.calls == 0
        assert insert_guard.calls == 0

    def test_create_puzzle_form_rejects_description_too_long_without_creating_files(self, client, conn, monkeypatch):
        token = register_and_login(client, "upload_creator_desc_limit")
        me = client.get("/users/me", headers=auth_header(token)).json()
        _make_creator(conn, me["id"])

        upload_conn = sqlite3.connect(":memory:", check_same_thread=False)
        upload_conn.row_factory = sqlite3.Row
        PuzzleRepo(upload_conn)
        monkeypatch.setattr(puzzle_controller_module, "get_db_conn", lambda: upload_conn)

        copy_guard = _CopyGuard()
        insert_guard = _InsertGuard()
        monkeypatch.setattr(puzzle_controller_module.shutil, "copy2", copy_guard)
        monkeypatch.setattr(puzzle_controller_module, "insert_riddle", insert_guard)

        files = _multipart_payload(
            _base_config(description="d" * 2001),
            "short instructions",
            _solution(),
        )

        resp = client.post("/puzzles/create-puzzle-form", files=files, headers=auth_header(token))

        assert resp.status_code == 400
        assert "2000 characters" in resp.json()["detail"]
        assert copy_guard.calls == 0
        assert insert_guard.calls == 0

    def test_create_puzzle_form_rejects_instructions_too_large_without_creating_files(self, client, conn, monkeypatch):
        token = register_and_login(client, "upload_creator_instr_limit")
        me = client.get("/users/me", headers=auth_header(token)).json()
        _make_creator(conn, me["id"])

        upload_conn = sqlite3.connect(":memory:", check_same_thread=False)
        upload_conn.row_factory = sqlite3.Row
        PuzzleRepo(upload_conn)
        monkeypatch.setattr(puzzle_controller_module, "get_db_conn", lambda: upload_conn)

        copy_guard = _CopyGuard()
        insert_guard = _InsertGuard()
        monkeypatch.setattr(puzzle_controller_module.shutil, "copy2", copy_guard)
        monkeypatch.setattr(puzzle_controller_module, "insert_riddle", insert_guard)

        files = _multipart_payload(
            _base_config(),
            "a" * 5121,
            _solution(),
        )

        resp = client.post("/puzzles/create-puzzle-form", files=files, headers=auth_header(token))

        assert resp.status_code == 400
        assert "5120 bytes" in resp.json()["detail"]
        assert copy_guard.calls == 0
        assert insert_guard.calls == 0

    def test_create_puzzle_form_rejects_duplicate_name_without_creating_files(self, client, conn, monkeypatch):
        token = register_and_login(client, "upload_creator_duplicate")
        me = client.get("/users/me", headers=auth_header(token)).json()
        _make_creator(conn, me["id"])

        upload_conn = sqlite3.connect(":memory:", check_same_thread=False)
        upload_conn.row_factory = sqlite3.Row
        repo = PuzzleRepo(upload_conn)
        upload_conn.execute(
            """
            INSERT INTO puzzles(
                name, creator_user_id, description, instructions, status, budget,
                time_limit_seconds, difficulty, default_gate_set, rating_count,
                avg_difficulty, avg_fun, avg_clearness, total_gate_count, min_cycles, max_cycles, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            ("Existing Upload Puzzle", 1, "desc", "", "draft", 5, None, "EASY", '["AND"]', 0, 0.0, 0.0, 0.0, None, None, None),
        )
        upload_conn.commit()
        monkeypatch.setattr(puzzle_controller_module, "get_db_conn", lambda: upload_conn)

        copy_guard = _CopyGuard()
        insert_guard = _InsertGuard()
        monkeypatch.setattr(puzzle_controller_module.shutil, "copy2", copy_guard)
        monkeypatch.setattr(puzzle_controller_module, "insert_riddle", insert_guard)

        files = _multipart_payload(
            _base_config(name="Existing Upload Puzzle"),
            "short instructions",
            _solution(),
        )

        resp = client.post("/puzzles/create-puzzle-form", files=files, headers=auth_header(token))

        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]
        assert copy_guard.calls == 0
        assert insert_guard.calls == 0

    def test_admin_upload_rejects_duplicate_name_without_creating_files(self, client, conn, monkeypatch):
        token = register_and_login(client, "upload_admin_duplicate")
        me = client.get("/users/me", headers=auth_header(token)).json()
        _make_admin(conn, me["id"])

        upload_conn = sqlite3.connect(":memory:", check_same_thread=False)
        upload_conn.row_factory = sqlite3.Row
        PuzzleRepo(upload_conn)
        upload_conn.execute(
            """
            INSERT INTO puzzles(
                name, creator_user_id, description, instructions, status, budget,
                time_limit_seconds, difficulty, default_gate_set, rating_count,
                avg_difficulty, avg_fun, avg_clearness, total_gate_count, min_cycles, max_cycles, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            ("Existing Admin Upload Puzzle", 1, "desc", "", "published", 5, None, "EASY", '["AND"]', 0, 0.0, 0.0, 0.0, None, None, None),
        )
        upload_conn.commit()
        monkeypatch.setattr(admin_controller_module, "get_db_conn", lambda: upload_conn)

        copy_guard = _CopyGuard()
        insert_guard = _InsertGuard()
        monkeypatch.setattr(admin_controller_module.shutil, "copy2", copy_guard)
        monkeypatch.setattr(admin_controller_module, "insert_riddle", insert_guard)

        files = _multipart_payload(
            _base_config(name="Existing Admin Upload Puzzle"),
            "short instructions",
            _solution(),
        )

        resp = client.post("/admin/upload-puzzle", files=files, headers=auth_header(token))

        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]
        assert copy_guard.calls == 0
        assert insert_guard.calls == 0
