import json

import pytest

from .conftest import (
    auth_header,
    create_and_publish_puzzle,
    create_puzzle,
    get_user_info,
    get_user_xp,
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

        with pytest.raises(Exception):
            client.post(
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
