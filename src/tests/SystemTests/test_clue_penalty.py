import json

from .conftest import (
    auth_header,
    create_and_publish_puzzle,
    make_creator,
    register_and_login,
    validate_solution,
    _and_solution,
)


def _attach_clues(conn, puzzle_id, clues, clue_penalty_seconds=None):
    conn.execute(
        "UPDATE puzzles SET clues_json=?, clue_penalty_seconds=? WHERE id=?",
        (json.dumps(clues), clue_penalty_seconds, int(puzzle_id)),
    )
    conn.commit()


def _start_attempt(client, token, pid):
    resp = client.post(
        f"/puzzles/{pid}/attempts/start",
        headers=auth_header(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _request_clue(client, token, pid, attempt_id, request_id=None):
    resp = client.post(
        f"/puzzles/{pid}/clue",
        json={"attempt_id": attempt_id, "request_id": request_id},
        headers=auth_header(token),
    )
    return resp


def _validate_with_attempt(client, token, pid, solution, time_taken_raw, attempt_id):
    resp = client.post(
        f"/puzzles/{pid}/validate",
        json={
            "solution": solution,
            "time_taken_raw": time_taken_raw,
            "attempt_id": attempt_id,
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestClueExposure:
    def test_puzzle_payload_redacts_clue_text(self, client, conn):
        creator_token = make_creator(client, conn, "clue_redact_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="Clue Redact",
            budget=10, time_limit=60, difficulty="EASY",
        )
        _attach_clues(conn, pid, ["secret hint A", "secret hint B"])

        solver_token = register_and_login(client, "clue_redact_solver")
        resp = client.get(f"/puzzles/{pid}", headers=auth_header(solver_token))
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # The text array must NOT be exposed; only metadata.
        serialized = json.dumps(body)
        assert "secret hint A" not in serialized
        assert "secret hint B" not in serialized
        assert body.get("has_clues") is True
        assert body.get("clue_count") == 2
        # EASY tier default is 15s.
        assert body.get("clue_penalty_seconds") == 15


class TestClueRequestFlow:
    def test_request_clue_returns_text_and_records_penalty(self, client, conn):
        creator_token = make_creator(client, conn, "clue_request_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="Clue Request", budget=10, time_limit=60, difficulty="EASY",
        )
        _attach_clues(conn, pid, ["alpha clue", "beta clue", "gamma clue"])

        solver_token = register_and_login(client, "clue_request_solver")
        attempt = _start_attempt(client, solver_token, pid)
        attempt_id = attempt["id"]

        resp = _request_clue(client, solver_token, pid, attempt_id)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["clue_index"] == 0
        assert body["clue_text"] == "alpha clue"
        assert body["penalty_seconds"] == 15  # EASY default
        assert body["total_clues"] == 3
        assert body["clues_used_so_far"] == 1
        assert body["total_penalty_so_far"] == 15
        assert body["replayed"] is False

    def test_two_clues_inflate_recorded_time(self, client, conn):
        creator_token = make_creator(client, conn, "clue_inflate_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="Clue Inflate", budget=10, time_limit=300, difficulty="MEDIUM",
        )
        _attach_clues(conn, pid, ["c1", "c2", "c3"])

        solver_token = register_and_login(client, "clue_inflate_solver")
        attempt = _start_attempt(client, solver_token, pid)
        attempt_id = attempt["id"]

        # Two clues: MEDIUM tier defaults to 30s each.
        _request_clue(client, solver_token, pid, attempt_id, "rid-1")
        _request_clue(client, solver_token, pid, attempt_id, "rid-2")

        result = _validate_with_attempt(
            client, solver_token, pid,
            _and_solution(), time_taken_raw=10, attempt_id=attempt_id,
        )
        assert result["solved"] is True
        # Effective recorded time = 10 raw + 2 * 30 = 70
        assert result["time_taken"] == 70

        # Leaderboard reflects the inflated time. The creator self-solves during
        # publish, so look up the solver's row specifically.
        lb = client.get(
            f"/puzzles/{pid}/leaderboard?type=time",
            headers=auth_header(solver_token),
        ).json()
        solver_rows = [e for e in lb["data"] if e["username"] == "clue_inflate_solver"]
        assert len(solver_rows) == 1
        assert solver_rows[0]["best_time"] == 70

    def test_idempotent_request_id_does_not_double_charge(self, client, conn):
        creator_token = make_creator(client, conn, "clue_idem_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="Clue Idempotency", budget=10, time_limit=60, difficulty="EASY",
        )
        _attach_clues(conn, pid, ["one", "two"])

        solver_token = register_and_login(client, "clue_idem_solver")
        attempt = _start_attempt(client, solver_token, pid)
        attempt_id = attempt["id"]

        first = _request_clue(client, solver_token, pid, attempt_id, "rid-shared").json()
        second = _request_clue(client, solver_token, pid, attempt_id, "rid-shared").json()

        assert first["clue_index"] == 0
        assert first["replayed"] is False
        assert second["clue_index"] == 0
        assert second["replayed"] is True
        # Total penalty so far reflects exactly one consumed clue, not two.
        assert second["total_penalty_so_far"] == first["penalty_seconds"]

        rows = conn.execute(
            "SELECT COUNT(*) FROM clue_requests WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()
        assert rows[0] == 1

    def test_distinct_request_ids_consume_distinct_clues(self, client, conn):
        creator_token = make_creator(client, conn, "clue_distinct_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="Clue Distinct", budget=10, time_limit=60, difficulty="EASY",
        )
        _attach_clues(conn, pid, ["one", "two", "three"])

        solver_token = register_and_login(client, "clue_distinct_solver")
        attempt = _start_attempt(client, solver_token, pid)
        attempt_id = attempt["id"]

        a = _request_clue(client, solver_token, pid, attempt_id, "rid-a").json()
        b = _request_clue(client, solver_token, pid, attempt_id, "rid-b").json()

        assert {a["clue_index"], b["clue_index"]} == {0, 1}
        assert a["replayed"] is False and b["replayed"] is False

    def test_exhaustion_returns_410(self, client, conn):
        creator_token = make_creator(client, conn, "clue_exhaust_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="Clue Exhaust", budget=10, time_limit=60, difficulty="EASY",
        )
        _attach_clues(conn, pid, ["only one"])

        solver_token = register_and_login(client, "clue_exhaust_solver")
        attempt = _start_attempt(client, solver_token, pid)
        attempt_id = attempt["id"]

        first = _request_clue(client, solver_token, pid, attempt_id, "first")
        assert first.status_code == 200
        second = _request_clue(client, solver_token, pid, attempt_id, "second")
        assert second.status_code == 410, second.text

    def test_no_clues_returns_404(self, client, conn):
        creator_token = make_creator(client, conn, "clue_none_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="No Clues", budget=10, time_limit=60, difficulty="EASY",
        )

        solver_token = register_and_login(client, "clue_none_solver")
        attempt = _start_attempt(client, solver_token, pid)
        attempt_id = attempt["id"]

        resp = _request_clue(client, solver_token, pid, attempt_id, "x")
        assert resp.status_code == 404, resp.text


class TestStartAttemptHydration:
    def test_idempotent_start_returns_existing_attempt_with_clues(self, client, conn):
        creator_token = make_creator(client, conn, "hydrate_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="Hydrate", budget=10, time_limit=60, difficulty="EASY",
        )
        _attach_clues(conn, pid, ["alpha", "beta", "gamma"])

        solver_token = register_and_login(client, "hydrate_solver")
        first = _start_attempt(client, solver_token, pid)
        attempt_id = first["id"]

        _request_clue(client, solver_token, pid, attempt_id, "rid-1")
        _request_clue(client, solver_token, pid, attempt_id, "rid-2")

        # Refresh: hitting /attempts/start again should not create a new attempt
        # and should hydrate the user's revealed clue text + penalty.
        second = _start_attempt(client, solver_token, pid)
        assert second["id"] == attempt_id
        assert second["started_at"] == first["started_at"]
        assert second["total_clue_penalty_seconds"] == 30  # 2 * 15
        revealed = second["revealed_clues"]
        assert len(revealed) == 2
        assert {c["index"] for c in revealed} == {0, 1}
        assert {c["text"] for c in revealed} == {"alpha", "beta"}


class TestSolveClosesAttempt:
    def test_solve_closes_attempt_and_blocks_clue_requests(self, client, conn):
        creator_token = make_creator(client, conn, "close_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="Close Attempt", budget=10, time_limit=60, difficulty="EASY",
        )
        _attach_clues(conn, pid, ["one", "two"])

        solver_token = register_and_login(client, "close_solver")
        first = _start_attempt(client, solver_token, pid)
        first_attempt_id = first["id"]

        _request_clue(client, solver_token, pid, first_attempt_id, "rid-a")
        _validate_with_attempt(
            client, solver_token, pid,
            _and_solution(), time_taken_raw=5, attempt_id=first_attempt_id,
        )

        # The closed attempt now refuses new clue requests.
        rejected = _request_clue(client, solver_token, pid, first_attempt_id, "rid-b")
        assert rejected.status_code == 403, rejected.text

        # Solve again -> fresh attempt with no revealed clues.
        second = _start_attempt(client, solver_token, pid)
        assert second["id"] != first_attempt_id
        assert second["revealed_clues"] == []
        assert second["total_clue_penalty_seconds"] == 0

        ok = _request_clue(client, solver_token, pid, second["id"], "rid-c")
        assert ok.status_code == 200
        assert ok.json()["clue_index"] == 0


class TestFailedAttemptKeepsClues:
    def test_failed_attempt_row_records_clue_metadata(self, client, conn):
        creator_token = make_creator(client, conn, "fail_meta_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="Failed Row Clue Meta", budget=10, time_limit=60, difficulty="EASY",
        )
        _attach_clues(conn, pid, ["x1", "x2"])

        solver_token = register_and_login(client, "fail_meta_solver")
        attempt = _start_attempt(client, solver_token, pid)
        attempt_id = attempt["id"]

        _request_clue(client, solver_token, pid, attempt_id, "rid-x1")
        _request_clue(client, solver_token, pid, attempt_id, "rid-x2")

        bad_solution = {
            "placedComponents": [
                {"id": "and1", "componentId": "AND"},
                {"id": "not1", "componentId": "NOT"},
            ],
            "wires": [
                {"from": {"componentId": "IO:IN:A", "pinIndex": 0},
                 "to": {"componentId": "and1", "pinIndex": 0}},
                {"from": {"componentId": "IO:IN:B", "pinIndex": 0},
                 "to": {"componentId": "and1", "pinIndex": 1}},
                {"from": {"componentId": "and1", "pinIndex": 2},
                 "to": {"componentId": "not1", "pinIndex": 0}},
                {"from": {"componentId": "not1", "pinIndex": 1},
                 "to": {"componentId": "IO:OUT:out", "pinIndex": 0}},
            ],
            "totalCost": 2,
        }
        result = _validate_with_attempt(
            client, solver_token, pid, bad_solution,
            time_taken_raw=7, attempt_id=attempt_id,
        )
        assert result["solved"] is False

        # The most recent failed-attempt analytics row for this user/puzzle
        # must record both clues_used and clue_penalty_seconds (2 * 15 = 30).
        row = conn.execute(
            """
            SELECT clues_used, clue_penalty_seconds, time_used_seconds, passed
            FROM solve_attempts
            WHERE puzzle_id=? AND passed=0
            ORDER BY id DESC LIMIT 1
            """,
            (int(pid),),
        ).fetchone()
        assert row is not None
        assert int(row["clues_used"]) == 2
        assert int(row["clue_penalty_seconds"]) == 30
        # Effective time on the failed row = raw + persisted penalty.
        assert int(row["time_used_seconds"]) == 7 + 30

    def test_failed_then_successful_solve_carries_clue_penalty(self, client, conn):
        creator_token = make_creator(client, conn, "carry_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="Carry Penalty", budget=10, time_limit=60, difficulty="EASY",
        )
        _attach_clues(conn, pid, ["help-one"])

        solver_token = register_and_login(client, "carry_solver")
        attempt = _start_attempt(client, solver_token, pid)
        attempt_id = attempt["id"]

        _request_clue(client, solver_token, pid, attempt_id, "rid-1")

        # First submit: a wrong solution that swaps the truth table — NOT(A AND B)
        # produces 1 for (0,0) and 0 for (1,1), failing both blackbox cases.
        bad_solution = {
            "placedComponents": [
                {"id": "and1", "componentId": "AND"},
                {"id": "not1", "componentId": "NOT"},
            ],
            "wires": [
                {"from": {"componentId": "IO:IN:A", "pinIndex": 0},
                 "to": {"componentId": "and1", "pinIndex": 0}},
                {"from": {"componentId": "IO:IN:B", "pinIndex": 0},
                 "to": {"componentId": "and1", "pinIndex": 1}},
                {"from": {"componentId": "and1", "pinIndex": 2},
                 "to": {"componentId": "not1", "pinIndex": 0}},
                {"from": {"componentId": "not1", "pinIndex": 1},
                 "to": {"componentId": "IO:OUT:out", "pinIndex": 0}},
            ],
            "totalCost": 2,
        }
        bad = _validate_with_attempt(
            client, solver_token, pid, bad_solution,
            time_taken_raw=5, attempt_id=attempt_id,
        )
        assert bad["solved"] is False

        # Now submit the correct solution. Clue penalty is still applied.
        good = _validate_with_attempt(
            client, solver_token, pid, _and_solution(),
            time_taken_raw=12, attempt_id=attempt_id,
        )
        assert good["solved"] is True
        # 12 raw + 15 penalty = 27
        assert good["time_taken"] == 27


class TestValidateContract:
    def test_legacy_validate_without_attempt_id_works(self, client, conn):
        # This mirrors the behavior covered by test_retry_and_edge_case_regressions:
        # when no attempt_id is sent, validate must not 400 — it falls back to the
        # user's open attempt (or creates one inline) with zero clue penalty.
        creator_token = make_creator(client, conn, "legacy_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="Legacy", budget=10, time_limit=60, difficulty="EASY",
        )

        solver_token = register_and_login(client, "legacy_solver")
        result = validate_solution(
            client, solver_token, pid, _and_solution(), time_taken=10,
        )
        assert result["solved"] is True
        assert result["time_taken"] == 10  # no penalty applied
