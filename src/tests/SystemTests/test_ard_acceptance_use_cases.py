import io
import json
import sqlite3
from pathlib import Path

import pytest
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
import Backend.APILayer.PuzzleController as puzzle_controller_module

from .conftest import (
    auth_header,
    create_and_publish_puzzle,
    create_puzzle,
    get_user_info,
    get_user_xp,
    make_admin,
    make_creator,
    register_and_login,
    add_blackbox_test_case,
    validate_solution,
    _and_solution,
)


def _circuit_payload(name: str, structure: dict, cost: int) -> dict:
    return {
        "name": name,
        "cost": cost,
        "structure_json": json.dumps(structure),
    }


def _arsenal_payload(name: str, basic_gates: str = '["AND"]') -> dict:
    return {
        "name": name,
        "num_inputs": 1,
        "num_outputs": 1,
        "structure_json": json.dumps({"placedComponents": [], "wires": []}),
        "basic_gates": basic_gates,
        "truth_table": {"0": "0", "1": "1"},
    }


def _and_solution_with_extra_gate() -> dict:
    return {
        "placedComponents": [
            {"id": "and1", "componentId": "AND"},
            {"id": "not1", "componentId": "NOT"},
        ],
        "wires": [
            {"from": {"componentId": "IO:IN:A", "pinIndex": 0}, "to": {"componentId": "and1", "pinIndex": 0}},
            {"from": {"componentId": "IO:IN:B", "pinIndex": 0}, "to": {"componentId": "and1", "pinIndex": 1}},
            {"from": {"componentId": "and1", "pinIndex": 2}, "to": {"componentId": "IO:OUT:out", "pinIndex": 0}},
        ],
        "totalCost": 2,
    }


def _upload_base_config(name="Upload Puzzle", description="desc") -> dict:
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


def _upload_solution() -> dict:
    return {
        "eval_map": {
            '{"A":0,"B":0}': {"out": 0},
        }
    }


def _multipart_payload(config: dict, instructions_text: str, solution: dict):
    return {
        "config_file": (
            "puzzle_config.json",
            io.BytesIO(json.dumps(config).encode("utf-8")),
            "application/json",
        ),
        "instructions_file": (
            "puzzle_instructions.tex",
            io.BytesIO(instructions_text.encode("utf-8")),
            "text/plain",
        ),
        "sample_solution_file": (
            "puzzle_solution.json",
            io.BytesIO(json.dumps(solution).encode("utf-8")),
            "application/json",
        ),
    }


class _CopyGuard:
    def __init__(self):
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("copy2 should not be called on validation failure")


class TestUseCase1BrowseAndSearchPuzzles:
    # UC1-AT1 - Successful Search
    def test_uc1_at1_successful_search(self, client, conn):
        creator_token = make_creator(client, conn, "uc1_creator")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="UC1 Search Target",
            budget=5,
            time_limit=60,
            difficulty="HARD",
        )

        solver_token = register_and_login(client, "uc1_solver")
        resp = client.get(
            "/puzzles",
            params={"search": "Search Target"},
            headers=auth_header(solver_token),
        )

        assert resp.status_code == 200
        ids = [int(p["id"]) for p in resp.json()["data"]]
        assert pid in ids

    # UC1-AT2 - Unsuccessful Search: No Matches
    def test_uc1_at2_unsuccessful_search_no_matches(self, client):
        solver_token = register_and_login(client, "uc1_no_match_solver")
        resp = client.get(
            "/puzzles",
            params={"search": "definitely-no-match"},
            headers=auth_header(solver_token),
        )

        assert resp.status_code == 200
        assert resp.json()["data"] == []

    # UC1-AT3 - Unsuccessful unauthorized Access
    def test_uc1_at3_unsuccessful_unauthorized_access(self, client):
        resp = client.get("/puzzles", params={"search": "anything"})
        assert resp.status_code == 401


class TestUseCase2SolveAPuzzle:
    # UC2-AT1 - Successful solve within limits
    def test_uc2_at1_successful_solve_within_limits(self, client, conn):
        creator_token = make_creator(client, conn, "uc2_creator_success")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="UC2 Solve Success", budget=5, time_limit=60
        )

        solver_token = register_and_login(client, "uc2_solver_success")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert result["solved"] is True
        assert result["xp_earned"] > 0
        assert result["medal"] == "GOLD"

    # UC2-AT2 - Unsuccessful wrong solution
    def test_uc2_at2_unsuccessful_wrong_solution(self, client, conn):
        creator_token = make_creator(client, conn, "uc2_creator_wrong")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="UC2 Wrong Solution", budget=5, time_limit=60
        )

        solver_token = register_and_login(client, "uc2_solver_wrong")
        bad_solution = {"placedComponents": [], "wires": [], "totalCost": 0}
        result = validate_solution(client, solver_token, pid, bad_solution, time_taken=10)

        assert result["solved"] is False

    # UC2-AT3 - Unsuccessful exceeded the value limit
    def test_uc2_at3_unsuccessful_exceeded_the_value_limit(self, client, conn):
        creator_token = make_creator(client, conn, "uc2_creator_limit")
        puzzle = create_puzzle(client, creator_token, name="UC2 Budget Limit", budget=5, time_limit=60)
        pid = int(puzzle["id"])

        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        creator_result = validate_solution(client, creator_token, pid, _and_solution(), time_taken=10)
        assert creator_result["solved"] is True

        publish = client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token))
        assert publish.status_code == 200, publish.text

        conn.execute("UPDATE puzzles SET total_gate_count = 1 WHERE id = ?", (pid,))
        gate_limit_case = client.post(
            f"/puzzles/{pid}/testcases",
            json={"kind": "gate_count_limit", "inputs": {}, "expected_outputs": {}},
            headers=auth_header(creator_token),
        )
        assert gate_limit_case.status_code == 200, gate_limit_case.text

        solver_token = register_and_login(client, "uc2_solver_limit")
        result = validate_solution(client, solver_token, pid, _and_solution_with_extra_gate(), time_taken=10)

        assert result["solved"] is False

    # UC2-AT4 - Unsuccessful time expired
    def test_uc2_at4_unsuccessful_time_expired(self, client, conn):
        creator_token = make_creator(client, conn, "uc2_creator_time")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="UC2 Time Expired", budget=5, time_limit=60
        )

        solver_token = register_and_login(client, "uc2_solver_time")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=120)

        assert result["solved"] is True
        assert result["medal"] == "SILVER"


class TestUseCase3SaveAndReuseCircuits:
    # UC3-AT1 - Successful save to arsenal
    def test_uc3_at1_successful_save_to_arsenal(self, client):
        solver_token = register_and_login(client, "uc3_save_solver")
        resp = client.post("/arsenal", json=_arsenal_payload("uc3-piece-1"), headers=auth_header(solver_token))

        assert resp.status_code == 200, resp.text
        listed = client.get("/arsenal", headers=auth_header(solver_token))
        assert listed.status_code == 200
        names = [piece["name"] for piece in listed.json()]
        assert "uc3-piece-1" in names

    # UC3-AT2 - Successful reuse compatibility
    def test_uc3_at2_successful_reuse_compatibility(self, client, conn):
        creator_token = make_creator(client, conn, "uc3_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="UC3 Reuse Puzzle")

        solver_token = register_and_login(client, "uc3_reuse_solver")
        save_resp = client.post(
            "/arsenal",
            json=_arsenal_payload("uc3-compatible-piece", basic_gates='["AND"]'),
            headers=auth_header(solver_token),
        )
        assert save_resp.status_code == 200, save_resp.text

        available = client.get(
            f"/arsenal/puzzle/{pid}/available",
            params={"allowed_gates": "AND,OR,NOT"},
            headers=auth_header(solver_token),
        )
        assert available.status_code == 200
        available_names = [piece["type"] for piece in available.json()]
        assert "uc3-compatible-piece" in available_names

        missing_defaults = client.get(
            f"/arsenal/puzzle/{pid}/available",
            params={"allowed_gates": "OR,NOT"},
            headers=auth_header(solver_token),
        )
        assert missing_defaults.status_code == 200
        missing_names = [piece["type"] for piece in missing_defaults.json()]
        assert "uc3-compatible-piece" not in missing_names

    # UC3-AT3 - Unsuccessful name collision
    def test_uc3_at3_unsuccessful_name_collision(self, client):
        solver_token = register_and_login(client, "uc3_collision_solver")
        first = client.post("/arsenal", json=_arsenal_payload("same-name"), headers=auth_header(solver_token))
        assert first.status_code == 200, first.text

        second = client.post("/arsenal", json=_arsenal_payload("same-name"), headers=auth_header(solver_token))
        assert second.status_code == 400
        assert "already exists" in second.json()["detail"]

    # UC3-AT4 - Unsuccessful arsenal full
    def test_uc3_at4_unsuccessful_arsenal_full(self, client):
        solver_token = register_and_login(client, "uc3_capacity_solver")

        for idx in range(5):
            resp = client.post(
                "/arsenal",
                json=_arsenal_payload(f"piece-{idx}"),
                headers=auth_header(solver_token),
            )
            assert resp.status_code == 200, resp.text

        overflow = client.post(
            "/arsenal",
            json=_arsenal_payload("piece-overflow"),
            headers=auth_header(solver_token),
        )
        assert overflow.status_code == 400
        assert "capacity reached" in overflow.json()["detail"].lower()


class TestUseCase4CreateAndPublishPuzzle:
    # UC4-AT1 - Successful valid publish
    def test_uc4_at1_successful_valid_publish(self, client, conn):
        creator_token = make_creator(client, conn, "uc4_creator_publish")
        puzzle = create_puzzle(
            client,
            creator_token,
            name="UC4 Valid Publish",
            budget=5,
            time_limit=60,
            difficulty="HARD",
        )
        pid = int(puzzle["id"])

        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        creator_result = validate_solution(client, creator_token, pid, _and_solution(), time_taken=10)
        assert creator_result["solved"] is True

        publish = client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token))
        assert publish.status_code == 200, publish.text
        assert publish.json()["status"] == "published"
        assert publish.json()["created_at"]
        assert publish.json()["difficulty"] == "HARD"

    # UC4-AT2 - Successful basic circuits allowed
    @pytest.mark.skip(reason="Puzzle-only basic circuits are not exposed by the current backend API.")
    def test_uc4_at2_successful_basic_circuits_allowed(self):
        pass

    # UC4-AT3 - Unsuccessful self-solve fails
    def test_uc4_at3_unsuccessful_self_solve_fails(self, client, conn):
        creator_token = make_creator(client, conn, "uc4_creator_fail")
        puzzle = create_puzzle(client, creator_token, name="UC4 Self Solve Fail", budget=5, time_limit=60)
        pid = int(puzzle["id"])

        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        bad_solution = {"placedComponents": [], "wires": [], "totalCost": 0}
        failed = validate_solution(client, creator_token, pid, bad_solution, time_taken=10)
        assert failed["solved"] is False

        publish = client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token))
        assert publish.status_code == 403

    # UC4-AT4 - Unsuccessful duplicate name
    def test_uc4_at4_unsuccessful_duplicate_name(self, client, conn):
        creator_token = make_creator(client, conn, "uc4_creator_duplicate")
        first = client.post(
            "/puzzles",
            json={
                "name": "UC4 Duplicate Name",
                "description": "first",
                "budget": 5,
                "default_gate_set": ["AND", "OR", "NOT"],
                "difficulty": "EASY",
            },
            headers=auth_header(creator_token),
        )
        assert first.status_code == 200, first.text

        second = client.post(
            "/puzzles",
            json={
                "name": "UC4 Duplicate Name",
                "description": "second",
                "budget": 5,
                "default_gate_set": ["AND", "OR", "NOT"],
                "difficulty": "EASY",
            },
            headers=auth_header(creator_token),
        )
        assert second.status_code == 400
        assert "already exists" in second.json()["detail"].lower()

    # UC4-AT5 - Unsuccessful invalid limits
    def test_uc4_at5_unsuccessful_invalid_limits(self, client, conn):
        creator_token = make_creator(client, conn, "uc4_creator_invalid")
        resp = client.post(
            "/puzzles",
            json={
                "name": "UC4 Invalid Limits",
                "description": "invalid",
                "budget": -1,
                "default_gate_set": ["AND"],
                "difficulty": "EASY",
            },
            headers=auth_header(creator_token),
        )
        assert resp.status_code == 400


class TestUseCase5RateAPuzzle:
    # UC5-AT1 - Successful valid rating (Pre-10)
    def test_uc5_at1_successful_valid_rating_pre_10(self, client, conn):
        creator_token = make_creator(client, conn, "uc5_creator_pre10")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="UC5 Pre10", budget=5, time_limit=60, difficulty="HARD"
        )

        solver_token = register_and_login(client, "uc5_solver_pre10")
        rate = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 1, "fun": 4, "clearness": 4, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert rate.status_code == 200, rate.text

        metrics = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(solver_token))
        assert metrics.status_code == 200
        weighted = metrics.json()["metrics"]["weighted_difficulty"]
        assert weighted == 4.2

    # UC5-AT2 - Successful experienced weighting
    def test_uc5_at2_successful_experienced_weighting(self, client, conn):
        creator_token = make_creator(client, conn, "uc5_creator_exp")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="UC5 Experienced")

        solver_token = register_and_login(client, "uc5_solver_exp")
        me = get_user_info(client, solver_token)
        conn.execute("UPDATE users SET xp = 1600 WHERE id = ?", (me["id"],))

        rate = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 3, "fun": 4, "clearness": 5, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert rate.status_code == 200, rate.text

        metrics = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(solver_token))
        body = metrics.json()["metrics"]
        assert body["count"] == 1
        assert body["experienced"]["count"] == 1

    # UC5-AT3 - Successful post-10 shift
    def test_uc5_at3_successful_post_10_shift(self, client, conn):
        creator_token = make_creator(client, conn, "uc5_creator_post10")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="UC5 Post10", difficulty="HARD"
        )

        for idx in range(10):
            token = register_and_login(client, f"uc5_post10_solver_{idx}")
            rate = client.post(
                f"/ratings/puzzle/{pid}",
                json={"difficulty": 1, "fun": 3, "clearness": 3, "elapsed_seconds": 300},
                headers=auth_header(token),
            )
            assert rate.status_code == 200, rate.text

        metrics = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(register_and_login(client, "uc5_reader")))
        assert metrics.status_code == 200
        assert metrics.json()["metrics"]["count"] == 10
        assert metrics.json()["metrics"]["weighted_difficulty"] == 2.6

    # UC5-AT4 - Successful edit rating
    def test_uc5_at4_successful_edit_rating(self, client, conn):
        creator_token = make_creator(client, conn, "uc5_creator_edit")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="UC5 Edit")

        solver_token = register_and_login(client, "uc5_solver_edit")
        xp_before = get_user_xp(client, solver_token)

        first = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 2, "fun": 2, "clearness": 2, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert first.status_code == 200, first.text
        xp_after_first = get_user_xp(client, solver_token)
        assert xp_after_first > xp_before

        second = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 5, "fun": 5, "clearness": 4, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert second.status_code == 200, second.text

        xp_after_second = get_user_xp(client, solver_token)
        assert xp_after_second == xp_after_first

        metrics = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(solver_token))
        assert metrics.json()["my_rating"]["difficulty"] == 5

    # UC5-AT5 - Unsuccessful ineligible rating
    def test_uc5_at5_unsuccessful_ineligible_rating(self, client, conn):
        creator_token = make_creator(client, conn, "uc5_creator_ineligible")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="UC5 Ineligible")

        solver_token = register_and_login(client, "uc5_solver_ineligible")
        resp = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 3, "fun": 3, "clearness": 3, "elapsed_seconds": 120},
            headers=auth_header(solver_token),
        )
        assert resp.status_code == 400


class TestUseCase6EarnRewardsAndLevelUp:
    # UC6-AT1 - Successful standard XP
    def test_uc6_at1_successful_standard_xp(self, client, conn):
        creator_token = make_creator(client, conn, "uc6_creator_xp")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="UC6 Standard XP",
            budget=0,
            time_limit=None,
            difficulty="HARD",
        )

        solver_token = register_and_login(client, "uc6_solver_xp")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert result["solved"] is True
        assert result["medal"] == "BRONZE"
        assert result["xp_earned"] == 200

    # UC6-AT2 - Successful timer medal
    def test_uc6_at2_successful_timer_medal(self, client, conn):
        creator_token = make_creator(client, conn, "uc6_creator_timer")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="UC6 Timer Medal",
            budget=0,
            time_limit=60,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "uc6_solver_timer")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert result["solved"] is True
        assert result["medal"] == "SILVER"

    # UC6-AT3 - Successful medal upgrade
    def test_uc6_at3_successful_medal_upgrade(self, client, conn):
        creator_token = make_creator(client, conn, "uc6_creator_upgrade")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="UC6 Medal Upgrade",
            budget=1,
            time_limit=60,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "uc6_solver_upgrade")
        first = validate_solution(client, solver_token, pid, _and_solution(), time_taken=120)
        second = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert first["solved"] is True
        assert first["medal"] == "SILVER"
        assert second["solved"] is True
        assert second["medal"] == "GOLD"
        assert second["xp_earned"] > 0

    # UC6-AT4 - Successful level up
    def test_uc6_at4_successful_level_up(self, client, conn):
        creator_token = make_creator(client, conn, "uc6_creator_level")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="UC6 Level Up",
            budget=0,
            time_limit=None,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "uc6_solver_level")
        me = get_user_info(client, solver_token)
        conn.execute("UPDATE users SET xp = 399 WHERE id = ?", (me["id"],))

        before = get_user_info(client, solver_token)
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)
        after = get_user_info(client, solver_token)

        assert result["solved"] is True
        assert before["xp"] == 399
        assert after["xp"] >= 449
        assert after["level"] == before["level"] + 1

    # UC6-AT5 - Unsuccessful repeat timer
    def test_uc6_at5_unsuccessful_repeat_timer(self, client, conn):
        creator_token = make_creator(client, conn, "uc6_creator_repeat")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="UC6 Repeat Timer",
            budget=5,
            time_limit=60,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "uc6_solver_repeat")
        first = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)
        second = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert first["solved"] is True
        assert second["solved"] is True
        assert second["xp_earned"] == 0


class TestUseCase7ManagePuzzlesCreatorsOnly:
    # UC7-AT1 - Successful comment addition
    def test_uc7_at1_successful_comment_addition(self, client, conn):
        creator_token = make_creator(client, conn, "uc7_creator_add")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="UC7 Comment Add")

        resp = client.patch(
            f"/puzzles/{pid}",
            json={"description": "New creator comment"},
            headers=auth_header(creator_token),
        )
        assert resp.status_code == 200, resp.text

        got = client.get(f"/puzzles/{pid}", headers=auth_header(creator_token))
        assert got.status_code == 200
        assert got.json()["description"] == "New creator comment"

    # UC7-AT2 - Successful edit comment
    def test_uc7_at2_successful_edit_comment(self, client, conn):
        creator_token = make_creator(client, conn, "uc7_creator_edit")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="UC7 Comment Edit")

        first = client.patch(
            f"/puzzles/{pid}",
            json={"description": "Old comment"},
            headers=auth_header(creator_token),
        )
        assert first.status_code == 200, first.text

        second = client.patch(
            f"/puzzles/{pid}",
            json={"description": "Updated comment"},
            headers=auth_header(creator_token),
        )
        assert second.status_code == 200, second.text

        got = client.get(f"/puzzles/{pid}", headers=auth_header(creator_token))
        assert got.json()["description"] == "Updated comment"

    # UC7-AT3 - Successful delete comment
    def test_uc7_at3_successful_delete_comment(self, client, conn):
        creator_token = make_creator(client, conn, "uc7_creator_delete_comment")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="UC7 Comment Delete")

        seeded = client.patch(
            f"/puzzles/{pid}",
            json={"description": "Delete me"},
            headers=auth_header(creator_token),
        )
        assert seeded.status_code == 200, seeded.text

        deleted = client.patch(
            f"/puzzles/{pid}",
            json={"description": ""},
            headers=auth_header(creator_token),
        )
        assert deleted.status_code == 200, deleted.text

        got = client.get(f"/puzzles/{pid}", headers=auth_header(creator_token))
        assert got.json()["description"] == ""

    # UC7-AT4 - Successful delete puzzle
    def test_uc7_at4_successful_delete_puzzle(self, client, conn):
        creator_token = make_creator(client, conn, "uc7_creator_delete")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="UC7 Delete Puzzle")

        deleted = client.delete(f"/puzzles/{pid}", headers=auth_header(creator_token))
        assert deleted.status_code == 200, deleted.text

        missing = client.get(f"/puzzles/{pid}", headers=auth_header(creator_token))
        assert missing.status_code == 404

    # UC7-AT5 - Unsuccessful unauthorized
    def test_uc7_at5_unsuccessful_unauthorized(self, client, conn):
        owner_token = make_creator(client, conn, "uc7_owner")
        pid, _ = create_and_publish_puzzle(client, conn, owner_token, name="UC7 Forbidden")

        other_creator_token = make_creator(client, conn, "uc7_other_creator")
        patch_resp = client.patch(
            f"/puzzles/{pid}",
            json={"description": "forbidden"},
            headers=auth_header(other_creator_token),
        )
        delete_resp = client.delete(f"/puzzles/{pid}", headers=auth_header(other_creator_token))

        assert patch_resp.status_code == 403
        assert delete_resp.status_code == 403


class TestUseCase8PuzzleSolutionValidation:
    # UC8-AT1 - Successful correct solution
    def test_uc8_at1_successful_correct_solution(self, client, conn):
        creator_token = make_creator(client, conn, "uc8_creator_correct")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="UC8 Correct")

        solver_token = register_and_login(client, "uc8_solver_correct")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert result["solved"] is True

    # UC8-AT2 - Unsuccessful incorrect solution
    def test_uc8_at2_unsuccessful_incorrect_solution(self, client, conn):
        creator_token = make_creator(client, conn, "uc8_creator_incorrect")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="UC8 Incorrect")

        solver_token = register_and_login(client, "uc8_solver_incorrect")
        bad_solution = {"placedComponents": [], "wires": [], "totalCost": 0}
        result = validate_solution(client, solver_token, pid, bad_solution, time_taken=10)

        assert result["solved"] is False

    # UC8-AT3 - Unsuccessful limits were broken
    def test_uc8_at3_unsuccessful_limits_were_broken(self, client, conn):
        creator_token = make_creator(client, conn, "uc8_creator_limits")
        puzzle = create_puzzle(client, creator_token, name="UC8 Limits Broken", budget=5, time_limit=60)
        pid = int(puzzle["id"])

        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        validate_solution(client, creator_token, pid, _and_solution(), time_taken=10)

        publish = client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token))
        assert publish.status_code == 200, publish.text

        conn.execute("UPDATE puzzles SET total_gate_count = 1 WHERE id = ?", (pid,))
        gate_limit_case = client.post(
            f"/puzzles/{pid}/testcases",
            json={"kind": "gate_count_limit", "inputs": {}, "expected_outputs": {}},
            headers=auth_header(creator_token),
        )
        assert gate_limit_case.status_code == 200, gate_limit_case.text

        solver_token = register_and_login(client, "uc8_solver_limits")
        result = validate_solution(client, solver_token, pid, _and_solution_with_extra_gate(), time_taken=10)

        assert result["solved"] is False


# ADD acceptance tests


class TestAddedAcceptanceTestsDuplicates:
    ROOT = Path("/Users/dorsteinlauf/Desktop/EscapeCircuit")
    # UC1-AT1 - Successful Search
    # Description: User 123 searches with filters and the system returns puzzles meeting filters.
    def test_add_uc1_at1_successful_search(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc1_creator")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="ADD UC1 Search Target",
            budget=5,
            time_limit=60,
            difficulty="HARD",
        )

        solver_token = register_and_login(client, "add_uc1_solver")
        resp = client.get(
            "/puzzles",
            params={"search": "ADD UC1 Search"},
            headers=auth_header(solver_token),
        )

        assert resp.status_code == 200
        ids = [int(p["id"]) for p in resp.json()["data"]]
        assert pid in ids

    # UC1-AT2 - Unsuccessful Search: No Matches
    # Description: Empty list and appropriate no-match message behavior.
    def test_add_uc1_at2_unsuccessful_search_no_matches(self, client):
        solver_token = register_and_login(client, "add_uc1_no_match_solver")
        resp = client.get(
            "/puzzles",
            params={"search": "no-add-uc1-match"},
            headers=auth_header(solver_token),
        )

        assert resp.status_code == 200
        assert resp.json()["data"] == []

    # UC1-AT3 - Unsuccessful unauthorized Access
    # Description: Anonymous browse/search request is rejected.
    def test_add_uc1_at3_unsuccessful_unauthorized_access(self, client):
        resp = client.get("/puzzles", params={"search": "anything"})
        assert resp.status_code == 401

    # UC2-AT1 - Successful solve within limits
    # Description: Puzzle solved, XP and Timer Medal awarded.
    def test_add_uc2_at1_successful_solve_within_limits(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc2_creator_success")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ADD UC2 Solve Success", budget=5, time_limit=60
        )

        solver_token = register_and_login(client, "add_uc2_solver_success")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert result["solved"] is True
        assert result["xp_earned"] > 0
        assert result["medal"] == "GOLD"

    # UC2-AT2 - Unsuccessful wrong solution
    # Description: Invalid circuit returns not solved and no XP.
    def test_add_uc2_at2_unsuccessful_wrong_solution(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc2_creator_wrong")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ADD UC2 Wrong Solution", budget=5, time_limit=60
        )

        solver_token = register_and_login(client, "add_uc2_solver_wrong")
        bad_solution = {"placedComponents": [], "wires": [], "totalCost": 0}
        result = validate_solution(client, solver_token, pid, bad_solution, time_taken=10)

        assert result["solved"] is False

    # UC2-AT3 - Unsuccessful exceeded the value limit
    # Description: Addition exceeding limit is blocked and puzzle stays unsolved.
    def test_add_uc2_at3_unsuccessful_exceeded_the_value_limit(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc2_creator_limit")
        puzzle = create_puzzle(client, creator_token, name="ADD UC2 Budget Limit", budget=5, time_limit=60)
        pid = int(puzzle["id"])

        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        validate_solution(client, creator_token, pid, _and_solution(), time_taken=10)

        publish = client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token))
        assert publish.status_code == 200, publish.text

        conn.execute("UPDATE puzzles SET total_gate_count = 1 WHERE id = ?", (pid,))
        gate_limit_case = client.post(
            f"/puzzles/{pid}/testcases",
            json={"kind": "gate_count_limit", "inputs": {}, "expected_outputs": {}},
            headers=auth_header(creator_token),
        )
        assert gate_limit_case.status_code == 200, gate_limit_case.text

        solver_token = register_and_login(client, "add_uc2_solver_limit")
        result = validate_solution(client, solver_token, pid, _and_solution_with_extra_gate(), time_taken=10)

        assert result["solved"] is False

    # UC2-AT4 - Unsuccessful time expired
    # Description: Correct solve after timer expiration yields no Timer Medal.
    def test_add_uc2_at4_unsuccessful_time_expired(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc2_creator_time")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ADD UC2 Time Expired", budget=5, time_limit=60
        )

        solver_token = register_and_login(client, "add_uc2_solver_time")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=120)

        assert result["solved"] is True
        assert result["medal"] == "SILVER"

    # UC2-AT5 - Successful leaderboard ranking
    # Description: User 123's solve time appears on the puzzle leaderboard, ranked by fastest time. Top 3 solvers shown on podium.
    def test_add_uc2_at5_successful_leaderboard_ranking(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc2_creator_leaderboard")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ADD UC2 Leaderboard Ranking", budget=5, time_limit=60
        )

        slow_token = register_and_login(client, "add_uc2_slow_solver")
        fast_token = register_and_login(client, "add_uc2_fast_solver")
        mid_token = register_and_login(client, "add_uc2_mid_solver")

        validate_solution(client, slow_token, pid, _and_solution(), time_taken=30)
        validate_solution(client, fast_token, pid, _and_solution(), time_taken=15)
        validate_solution(client, mid_token, pid, _and_solution(), time_taken=20)

        leaderboard = client.get(f"/puzzles/{pid}/leaderboard", headers=auth_header(fast_token))
        assert leaderboard.status_code == 200, leaderboard.text

        entries = leaderboard.json()["data"]
        assert [entry["rank"] for entry in entries[:4]] == [1, 2, 3, 4]
        assert [entry["username"] for entry in entries[:4]] == [
            "add_uc2_creator_leaderboard",
            "add_uc2_fast_solver",
            "add_uc2_mid_solver",
            "add_uc2_slow_solver",
        ]
        assert [entry["best_time"] for entry in entries[:4]] == [10, 15, 20, 30]

    # UC3-AT1 - Successful save to arsenal
    # Description: Legal circuit is saved and appears in arsenal.
    def test_add_uc3_at1_successful_save_to_arsenal(self, client):
        solver_token = register_and_login(client, "add_uc3_save_solver")
        resp = client.post("/arsenal", json=_arsenal_payload("add-uc3-piece-1"), headers=auth_header(solver_token))

        assert resp.status_code == 200, resp.text
        listed = client.get("/arsenal", headers=auth_header(solver_token))
        assert listed.status_code == 200
        names = [piece["name"] for piece in listed.json()]
        assert "add-uc3-piece-1" in names

    # UC3-AT2 - Successful reuse compatibility
    # Description: Compatible arsenal circuit appears for puzzles with required defaults.
    def test_add_uc3_at2_successful_reuse_compatibility(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc3_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ADD UC3 Reuse Puzzle")

        solver_token = register_and_login(client, "add_uc3_reuse_solver")
        save_resp = client.post(
            "/arsenal",
            json=_arsenal_payload("add-uc3-compatible-piece", basic_gates='["AND"]'),
            headers=auth_header(solver_token),
        )
        assert save_resp.status_code == 200, save_resp.text

        available = client.get(
            f"/arsenal/puzzle/{pid}/available",
            params={"allowed_gates": "AND,OR,NOT"},
            headers=auth_header(solver_token),
        )
        assert available.status_code == 200
        available_names = [piece["type"] for piece in available.json()]
        assert "add-uc3-compatible-piece" in available_names

    # UC3-AT3 - Unsuccessful name collision
    # Description: Duplicate arsenal name is rejected.
    def test_add_uc3_at3_unsuccessful_name_collision(self, client):
        solver_token = register_and_login(client, "add_uc3_collision_solver")
        first = client.post("/arsenal", json=_arsenal_payload("add-same-name"), headers=auth_header(solver_token))
        assert first.status_code == 200, first.text

        second = client.post("/arsenal", json=_arsenal_payload("add-same-name"), headers=auth_header(solver_token))
        assert second.status_code == 400

    # UC3-AT4 - Unsuccessful arsenal full
    # Description: Save denied when arsenal reaches capacity.
    def test_add_uc3_at4_unsuccessful_arsenal_full(self, client):
        solver_token = register_and_login(client, "add_uc3_capacity_solver")

        for idx in range(5):
            resp = client.post(
                "/arsenal",
                json=_arsenal_payload(f"add-piece-{idx}"),
                headers=auth_header(solver_token),
            )
            assert resp.status_code == 200, resp.text

        overflow = client.post(
            "/arsenal",
            json=_arsenal_payload("add-piece-overflow"),
            headers=auth_header(solver_token),
        )
        assert overflow.status_code == 400

    # UC4-AT1 - Successful valid publish
    # Description: Valid puzzle is published successfully.
    def test_add_uc4_at1_successful_valid_publish(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc4_creator_publish")
        puzzle = create_puzzle(
            client,
            creator_token,
            name="ADD UC4 Valid Publish",
            budget=5,
            time_limit=60,
            difficulty="HARD",
        )
        pid = int(puzzle["id"])

        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        creator_result = validate_solution(client, creator_token, pid, _and_solution(), time_taken=10)
        assert creator_result["solved"] is True

        publish = client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token))
        assert publish.status_code == 200, publish.text

    # UC4-AT2 - Successful basic circuits allowed
    # Description: Circuits stored as puzzle-only, solvers cannot save.
    @pytest.mark.skip(reason="Puzzle-only basic circuits are not exposed by the current backend API.")
    def test_add_uc4_at2_successful_basic_circuits_allowed(self):
        pass

    # UC4-AT3 - Unsuccessful self-solve fails
    # Description: Upload blocked if creator cannot self-solve within limits.
    def test_add_uc4_at3_unsuccessful_self_solve_fails(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc4_creator_fail")
        puzzle = create_puzzle(client, creator_token, name="ADD UC4 Self Solve Fail", budget=5, time_limit=60)
        pid = int(puzzle["id"])

        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        bad_solution = {"placedComponents": [], "wires": [], "totalCost": 0}
        failed = validate_solution(client, creator_token, pid, bad_solution, time_taken=10)
        assert failed["solved"] is False

        publish = client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token))
        assert publish.status_code == 403

    # UC4-AT4 - Unsuccessful duplicate name
    # Description: Name rejected and user must choose a unique one.
    def test_add_uc4_at4_unsuccessful_duplicate_name(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc4_creator_duplicate")
        first = client.post(
            "/puzzles",
            json={
                "name": "ADD UC4 Duplicate Name",
                "description": "first",
                "budget": 5,
                "default_gate_set": ["AND", "OR", "NOT"],
                "difficulty": "EASY",
            },
            headers=auth_header(creator_token),
        )
        assert first.status_code == 200, first.text

        second = client.post(
            "/puzzles",
            json={
                "name": "ADD UC4 Duplicate Name",
                "description": "second",
                "budget": 5,
                "default_gate_set": ["AND", "OR", "NOT"],
                "difficulty": "EASY",
            },
            headers=auth_header(creator_token),
        )
        assert second.status_code == 400

    # UC4-AT5 - Unsuccessful invalid limits
    # Description: Invalid limits block upload.
    def test_add_uc4_at5_unsuccessful_invalid_limits(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc4_creator_invalid")
        resp = client.post(
            "/puzzles",
            json={
                "name": "ADD UC4 Invalid Limits",
                "description": "invalid",
                "budget": -1,
                "default_gate_set": ["AND"],
                "difficulty": "EASY",
            },
            headers=auth_header(creator_token),
        )
        assert resp.status_code == 400

    # UC4-AT6 - Unsuccessful name too long
    # Description: User 123 creates a puzzle with a name exceeding 100 characters. Upload blocked, validation error displayed.
    def test_add_uc4_at6_unsuccessful_name_too_long(self, client, conn, monkeypatch):
        token = register_and_login(client, "add_uc4_name_limit_creator")
        me = client.get("/users/me", headers=auth_header(token)).json()
        conn.execute("UPDATE users SET role = 'creator' WHERE id = ?", (me["id"],))

        upload_conn = sqlite3.connect(":memory:", check_same_thread=False)
        upload_conn.row_factory = sqlite3.Row
        PuzzleRepo(upload_conn)
        monkeypatch.setattr(puzzle_controller_module, "get_db_conn", lambda: upload_conn)

        copy_guard = _CopyGuard()
        monkeypatch.setattr(puzzle_controller_module.shutil, "copy2", copy_guard)

        resp = client.post(
            "/puzzles/create-puzzle-form",
            files=_multipart_payload(_upload_base_config(name="x" * 101), "short instructions", _upload_solution()),
            headers=auth_header(token),
        )

        assert resp.status_code == 400
        assert "100 characters" in resp.json()["detail"]
        assert copy_guard.calls == 0

    # UC4-AT7 - Unsuccessful description too long
    # Description: User 123 creates a puzzle with description exceeding the allowed limit. Upload blocked, validation error displayed.
    def test_add_uc4_at7_unsuccessful_description_too_long(self, client, conn, monkeypatch):
        token = register_and_login(client, "add_uc4_description_limit_creator")
        me = client.get("/users/me", headers=auth_header(token)).json()
        conn.execute("UPDATE users SET role = 'creator' WHERE id = ?", (me["id"],))

        upload_conn = sqlite3.connect(":memory:", check_same_thread=False)
        upload_conn.row_factory = sqlite3.Row
        PuzzleRepo(upload_conn)
        monkeypatch.setattr(puzzle_controller_module, "get_db_conn", lambda: upload_conn)

        copy_guard = _CopyGuard()
        monkeypatch.setattr(puzzle_controller_module.shutil, "copy2", copy_guard)

        resp = client.post(
            "/puzzles/create-puzzle-form",
            files=_multipart_payload(
                _upload_base_config(description="d" * 2001),
                "short instructions",
                _upload_solution(),
            ),
            headers=auth_header(token),
        )

        assert resp.status_code == 400
        assert "2000 characters" in resp.json()["detail"]
        assert copy_guard.calls == 0

    # UC4-AT8 - Successful custom board size
    # Description: User 123 creates a puzzle and sets board rows to 15. Puzzle creation flow keeps custom board size wiring and default grid constants.
    def test_add_uc4_at8_successful_custom_board_size(self):
        create_puzzle_source = (
            self.ROOT / "apps/nextjs-app/src/app/app/create-puzzle/page.tsx"
        ).read_text()
        workstation_grid_source = (
            self.ROOT / "apps/nextjs-app/src/app/app/puzzles/[id]/_components/workstation-grid.tsx"
        ).read_text()

        assert "const DEFAULT_BOARD_ROWS = 15;" in create_puzzle_source
        assert "boardRows: DEFAULT_BOARD_ROWS," in create_puzzle_source
        assert "rows: data.basic.boardRows," in create_puzzle_source
        assert "boardRows={data.basic.boardRows}" in create_puzzle_source
        assert "const DEFAULT_GRID_ROWS = 15;" in workstation_grid_source
        assert "boardRows = DEFAULT_GRID_ROWS," in workstation_grid_source

    # UC5-AT1 - Successful valid rating (Pre-10)
    # Description: Weighted difficulty reflects creator/user weighting before 10 ratings.
    def test_add_uc5_at1_successful_valid_rating_pre_10(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc5_creator_pre10")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ADD UC5 Pre10", budget=5, time_limit=60, difficulty="HARD"
        )

        solver_token = register_and_login(client, "add_uc5_solver_pre10")
        rate = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 1, "fun": 4, "clearness": 4, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert rate.status_code == 200, rate.text

        metrics = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(solver_token))
        assert metrics.status_code == 200
        assert metrics.json()["metrics"]["weighted_difficulty"] == 4.2

    # UC5-AT2 - Successful experienced weighting
    # Description: Experienced user rating contributes to experienced-only averages.
    def test_add_uc5_at2_successful_experienced_weighting(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc5_creator_exp")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ADD UC5 Experienced")

        solver_token = register_and_login(client, "add_uc5_solver_exp")
        me = get_user_info(client, solver_token)
        conn.execute("UPDATE users SET xp = 1600 WHERE id = ?", (me["id"],))

        rate = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 3, "fun": 4, "clearness": 5, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert rate.status_code == 200, rate.text

        metrics = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(solver_token))
        assert metrics.json()["metrics"]["experienced"]["count"] == 1

    # UC5-AT3 - Successful post-10 shift
    # Description: Weighting shifts after puzzle reaches 10 ratings.
    def test_add_uc5_at3_successful_post_10_shift(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc5_creator_post10")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ADD UC5 Post10", difficulty="HARD"
        )

        for idx in range(10):
            token = register_and_login(client, f"add_uc5_post10_solver_{idx}")
            rate = client.post(
                f"/ratings/puzzle/{pid}",
                json={"difficulty": 1, "fun": 3, "clearness": 3, "elapsed_seconds": 300},
                headers=auth_header(token),
            )
            assert rate.status_code == 200, rate.text

        metrics = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(register_and_login(client, "add_uc5_reader")))
        assert metrics.status_code == 200
        assert metrics.json()["metrics"]["count"] == 10

    # UC5-AT4 - Successful edit rating
    # Description: Editing a rating recalculates aggregates and grants no extra XP.
    def test_add_uc5_at4_successful_edit_rating(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc5_creator_edit")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ADD UC5 Edit")

        solver_token = register_and_login(client, "add_uc5_solver_edit")
        xp_before = get_user_xp(client, solver_token)

        first = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 2, "fun": 2, "clearness": 2, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert first.status_code == 200, first.text
        xp_after_first = get_user_xp(client, solver_token)
        assert xp_after_first > xp_before

        second = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 5, "fun": 5, "clearness": 4, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert second.status_code == 200, second.text
        assert get_user_xp(client, solver_token) == xp_after_first

    # UC5-AT5 - Unsuccessful ineligible rating
    # Description: Rating attempt below minimum attempt time is denied.
    def test_add_uc5_at5_unsuccessful_ineligible_rating(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc5_creator_ineligible")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ADD UC5 Ineligible")

        solver_token = register_and_login(client, "add_uc5_solver_ineligible")
        resp = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 3, "fun": 3, "clearness": 3, "elapsed_seconds": 120},
            headers=auth_header(solver_token),
        )
        assert resp.status_code == 400

    # UC5-AT6 - Unsuccessful duplicate rating
    # Description: User 123 has already rated this puzzle. User 123 submits a new rating (not via edit).
    @pytest.mark.skip(reason="Current API treats repeated rating submission as edit-in-place; duplicate-create rejection flow is not exposed.")
    def test_add_uc5_at6_unsuccessful_duplicate_rating(self):
        pass

    # UC6-AT1 - Successful standard XP
    # Description: XP awarded per difficulty tier.
    def test_add_uc6_at1_successful_standard_xp(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc6_creator_xp")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="ADD UC6 Standard XP",
            budget=0,
            time_limit=None,
            difficulty="HARD",
        )

        solver_token = register_and_login(client, "add_uc6_solver_xp")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert result["solved"] is True
        assert result["xp_earned"] == 200

    # UC6-AT2 - Successful medal upgrade
    # Description: Medal upgrades when greater limits are respected.
    def test_add_uc6_at2_successful_medal_upgrade(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc6_creator_upgrade")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="ADD UC6 Medal Upgrade",
            budget=1,
            time_limit=60,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "add_uc6_solver_upgrade")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert result["solved"] is True
        assert result["medal"] == "GOLD"

    # UC6-AT3 - Successful level up
    # Description: User level increases when XP crosses threshold.
    def test_add_uc6_at3_successful_level_up(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc6_creator_level")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="ADD UC6 Level Up",
            budget=0,
            time_limit=None,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "add_uc6_solver_level")
        me = get_user_info(client, solver_token)
        conn.execute("UPDATE users SET xp = 399 WHERE id = ?", (me["id"],))

        before = get_user_info(client, solver_token)
        validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)
        after = get_user_info(client, solver_token)

        assert after["level"] == before["level"] + 1

    # UC6-AT4 - Unsuccessful repeat timer
    # Description: Subsequent solve does not award extra timer medal or bonus.
    def test_add_uc6_at4_unsuccessful_repeat_timer(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc6_creator_repeat")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="ADD UC6 Repeat Timer",
            budget=5,
            time_limit=60,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "add_uc6_solver_repeat")
        validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)
        second = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert second["xp_earned"] == 0

    # UC6-AT6 - Successful medal tie at boundary
    # Description: User 123 solves a puzzle with cost exactly equal to the greater value limit. Boundary value is treated as within limits.
    def test_add_uc6_at6_successful_medal_tie_at_boundary(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc6_creator_boundary")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="ADD UC6 Boundary Medal",
            budget=1,
            time_limit=None,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "add_uc6_boundary_solver")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert result["solved"] is True
        assert result["medal"] == "SILVER"

    # UC6-AT7 - Successful leaderboard after reward
    # Description: User 123 solves a puzzle and earns gold medal. XP and medal awarded; user appears on puzzle leaderboard ranked by solve time.
    def test_add_uc6_at7_successful_leaderboard_after_reward(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc6_creator_leaderboard")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="ADD UC6 Reward Leaderboard",
            budget=1,
            time_limit=60,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "add_uc6_reward_solver")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=5)
        assert result["solved"] is True
        assert result["medal"] == "GOLD"
        assert result["xp_earned"] > 0

        leaderboard = client.get(f"/puzzles/{pid}/leaderboard", headers=auth_header(solver_token))
        assert leaderboard.status_code == 200, leaderboard.text

        entries = leaderboard.json()["data"]
        assert entries[0]["username"] == "add_uc6_reward_solver"
        assert entries[0]["rank"] == 1
        assert entries[0]["best_time"] == 5

    # UC7-AT1 - Successful comment addition
    # Description: Creator comment is stored and visible.
    def test_add_uc7_at1_successful_comment_addition(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc7_creator_add")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ADD UC7 Comment Add")

        resp = client.patch(
            f"/puzzles/{pid}",
            json={"description": "ADD new creator comment"},
            headers=auth_header(creator_token),
        )
        assert resp.status_code == 200, resp.text

    # UC7-AT2 - Successful edit comment
    # Description: Existing creator comment is replaced.
    def test_add_uc7_at2_successful_edit_comment(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc7_creator_edit")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ADD UC7 Comment Edit")

        client.patch(f"/puzzles/{pid}", json={"description": "Old"}, headers=auth_header(creator_token))
        resp = client.patch(f"/puzzles/{pid}", json={"description": "Updated"}, headers=auth_header(creator_token))

        assert resp.status_code == 200, resp.text

    # UC7-AT3 - Successful delete comment
    # Description: Comment is removed from puzzle page.
    def test_add_uc7_at3_successful_delete_comment(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc7_creator_delete_comment")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ADD UC7 Comment Delete")

        client.patch(f"/puzzles/{pid}", json={"description": "Delete me"}, headers=auth_header(creator_token))
        resp = client.patch(f"/puzzles/{pid}", json={"description": ""}, headers=auth_header(creator_token))

        assert resp.status_code == 200, resp.text

    # UC7-AT4 - Successful delete puzzle
    # Description: Puzzle is removed from public listings.
    def test_add_uc7_at4_successful_delete_puzzle(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc7_creator_delete")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ADD UC7 Delete Puzzle")

        deleted = client.delete(f"/puzzles/{pid}", headers=auth_header(creator_token))
        assert deleted.status_code == 200, deleted.text

    # UC7-AT5 - Unsuccessful unauthorized
    # Description: Different creator cannot edit or delete someone else's puzzle.
    def test_add_uc7_at5_unsuccessful_unauthorized(self, client, conn):
        owner_token = make_creator(client, conn, "add_uc7_owner")
        pid, _ = create_and_publish_puzzle(client, conn, owner_token, name="ADD UC7 Forbidden")

        other_creator_token = make_creator(client, conn, "add_uc7_other_creator")
        patch_resp = client.patch(
            f"/puzzles/{pid}",
            json={"description": "forbidden"},
            headers=auth_header(other_creator_token),
        )
        delete_resp = client.delete(f"/puzzles/{pid}", headers=auth_header(other_creator_token))

        assert patch_resp.status_code == 403
        assert delete_resp.status_code == 403

    # UC8-AT1 - Successful correct solution
    # Description: System returns true for a correct solution.
    def test_add_uc8_at1_successful_correct_solution(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc8_creator_correct")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ADD UC8 Correct")

        solver_token = register_and_login(client, "add_uc8_solver_correct")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert result["solved"] is True

    # UC8-AT2 - Unsuccessful incorrect solution
    # Description: System returns false for an incorrect solution.
    def test_add_uc8_at2_unsuccessful_incorrect_solution(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc8_creator_incorrect")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ADD UC8 Incorrect")

        solver_token = register_and_login(client, "add_uc8_solver_incorrect")
        bad_solution = {"placedComponents": [], "wires": [], "totalCost": 0}
        result = validate_solution(client, solver_token, pid, bad_solution, time_taken=10)

        assert result["solved"] is False

    # UC8-AT3 - Unsuccessful limits were broken
    # Description: Validation returns false when puzzle limits are broken.
    def test_add_uc8_at3_unsuccessful_limits_were_broken(self, client, conn):
        creator_token = make_creator(client, conn, "add_uc8_creator_limits")
        puzzle = create_puzzle(client, creator_token, name="ADD UC8 Limits Broken", budget=5, time_limit=60)
        pid = int(puzzle["id"])

        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        validate_solution(client, creator_token, pid, _and_solution(), time_taken=10)

        publish = client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token))
        assert publish.status_code == 200, publish.text

        conn.execute("UPDATE puzzles SET total_gate_count = 1 WHERE id = ?", (pid,))
        gate_limit_case = client.post(
            f"/puzzles/{pid}/testcases",
            json={"kind": "gate_count_limit", "inputs": {}, "expected_outputs": {}},
            headers=auth_header(creator_token),
        )
        assert gate_limit_case.status_code == 200, gate_limit_case.text

        solver_token = register_and_login(client, "add_uc8_solver_limits")
        result = validate_solution(client, solver_token, pid, _and_solution_with_extra_gate(), time_taken=10)

        assert result["solved"] is False


class TestAddedAcceptanceTestsUC9ToUC12:
    # UC9-AT1 - Successful Appointment
    # Description: User 123 (admin) appoints User 456. System records appointment or sends invite to User 456.
    def test_add_uc9_at1_successful_appointment(self, client, conn):
        admin_token = make_admin(client, conn, "add_uc9_admin_success")
        target_token = register_and_login(client, "add_uc9_target_solver")
        target_info = get_user_info(client, target_token)

        resp = client.post(
            "/admin/assign-creator",
            json={"target_user_id": target_info["id"]},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200, resp.text

        updated = get_user_info(client, target_token)
        assert updated["role"] == "pending_creator"

    # UC9-AT2 - Successful already appointed
    # Description: System notify that this user is already a creator.
    def test_add_uc9_at2_successful_already_appointed(self, client, conn):
        admin_token = make_admin(client, conn, "add_uc9_admin_existing")
        creator_token = make_creator(client, conn, "add_uc9_existing_creator")
        creator_info = get_user_info(client, creator_token)

        resp = client.post(
            "/admin/assign-creator",
            json={"target_user_id": creator_info["id"]},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 400
        assert "already" in resp.json()["detail"].lower()

    # UC9-AT3 - Unsuccessful - Unauthorized
    # Description: User 789 tries to access the appointment interface. System denies access or hides the option.
    def test_add_uc9_at3_unsuccessful_unauthorized(self, client):
        solver_token = register_and_login(client, "add_uc9_unauthorized_solver")
        target_token = register_and_login(client, "add_uc9_target_other")
        target_info = get_user_info(client, target_token)

        resp = client.post(
            "/admin/assign-creator",
            json={"target_user_id": target_info["id"]},
            headers=auth_header(solver_token),
        )
        assert resp.status_code == 403

    # UC10-AT1 - Successful Profile Load
    # Description: System displays profile progress metrics.
    @pytest.mark.skip(reason="Current /users/me API does not expose medal aggregates or saved-puzzle profile sections.")
    def test_add_uc10_at1_successful_profile_load(self):
        pass

    # UC10-AT2 - Successful Puzzle Access
    # Description: System displays a clickable list of saved puzzles from the profile page.
    @pytest.mark.skip(reason="Saved-for-later puzzles are not exposed by the current backend profile contract.")
    def test_add_uc10_at2_successful_puzzle_access(self):
        pass

    # UC11-AT1 - Successful Sandbox Save
    # Description: User 123 builds a valid circuit and saves it as "MyAdder".
    def test_add_uc11_at1_successful_sandbox_save(self, client):
        solver_token = register_and_login(client, "add_uc11_sandbox_save_solver")

        resp = client.post(
            "/arsenal",
            json=_arsenal_payload("MyAdder"),
            headers=auth_header(solver_token),
        )
        assert resp.status_code == 200, resp.text

        listed = client.get("/arsenal", headers=auth_header(solver_token))
        assert listed.status_code == 200
        names = [piece["name"] for piece in listed.json()]
        assert "MyAdder" in names

    # UC11-AT2 - Unsuccessful - Arsenal Full
    # Description: The system rejects save and displays a capacity error.
    def test_add_uc11_at2_unsuccessful_arsenal_full(self, client):
        solver_token = register_and_login(client, "add_uc11_sandbox_capacity_solver")

        for idx in range(5):
            resp = client.post(
                "/arsenal",
                json=_arsenal_payload(f"add-uc11-piece-{idx}"),
                headers=auth_header(solver_token),
            )
            assert resp.status_code == 200, resp.text

        overflow = client.post(
            "/arsenal",
            json=_arsenal_payload("add-uc11-overflow"),
            headers=auth_header(solver_token),
        )
        assert overflow.status_code == 400
        assert "capacity reached" in overflow.json()["detail"].lower()

    # UC11-AT3 - Unsuccessful - Name collision
    # Description: The system rejects save and displays a naming error.
    def test_add_uc11_at3_unsuccessful_name_collision(self, client):
        solver_token = register_and_login(client, "add_uc11_sandbox_collision_solver")

        first = client.post(
            "/arsenal",
            json=_arsenal_payload("A"),
            headers=auth_header(solver_token),
        )
        assert first.status_code == 200, first.text

        second = client.post(
            "/arsenal",
            json=_arsenal_payload("A"),
            headers=auth_header(solver_token),
        )
        assert second.status_code == 400
        assert "already exists" in second.json()["detail"]

    # UC12-AT1 - Successful Deletion
    # Description: The system deletes the file and updates the count.
    def test_add_uc12_at1_successful_deletion(self, client):
        solver_token = register_and_login(client, "add_uc12_delete_solver")

        created = client.post(
            "/arsenal",
            json=_arsenal_payload("Old_Circuit"),
            headers=auth_header(solver_token),
        )
        assert created.status_code == 200, created.text
        piece_id = created.json()["id"]

        deleted = client.delete(f"/arsenal/{piece_id}", headers=auth_header(solver_token))
        assert deleted.status_code == 200, deleted.text

        listed = client.get("/arsenal", headers=auth_header(solver_token))
        assert listed.status_code == 200
        names = [piece["name"] for piece in listed.json()]
        assert "Old_Circuit" not in names

    # UC12-AT2 - Successful Rename
    # Description: System updates the name in the list.
    def test_add_uc12_at2_successful_rename(self, client):
        solver_token = register_and_login(client, "add_uc12_rename_solver")

        created = client.post(
            "/arsenal",
            json=_arsenal_payload("Circuit_A"),
            headers=auth_header(solver_token),
        )
        assert created.status_code == 200, created.text
        piece_id = created.json()["id"]

        renamed = client.put(
            f"/arsenal/{piece_id}",
            json={"new_name": "Circuit_B"},
            headers=auth_header(solver_token),
        )
        assert renamed.status_code == 200, renamed.text

        listed = client.get("/arsenal", headers=auth_header(solver_token))
        assert listed.status_code == 200
        names = [piece["name"] for piece in listed.json()]
        assert "Circuit_B" in names
        assert "Circuit_A" not in names
