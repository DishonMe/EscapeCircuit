"""
System tests: Multi-user interaction scenarios.

Tests complete workflows involving multiple users interacting with the same
puzzle: creator publishes → multiple solvers solve → solvers rate → solvers
discuss → creator receives notifications and XP.
"""
from .conftest import (
    auth_header, make_creator, register_and_login, get_user_xp,
    create_and_publish_puzzle, validate_solution, _and_solution,
    get_user_info,
)


class TestMultiSolverWorkflow:
    """Multiple solvers solve the same puzzle."""

    def test_two_solvers_both_get_xp(self, client, conn):
        creator_token = make_creator(client, conn, "ms_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token,
                                           name="Multi-Solver")

        # Solver A
        sa_token = register_and_login(client, "solverA")
        sa_xp_before = get_user_xp(client, sa_token)
        r1 = validate_solution(client, sa_token, pid, _and_solution(),
                               time_taken=10)
        assert r1["solved"] is True
        assert r1["xp_earned"] > 0
        assert get_user_xp(client, sa_token) > sa_xp_before

        # Solver B
        sb_token = register_and_login(client, "solverB")
        sb_xp_before = get_user_xp(client, sb_token)
        r2 = validate_solution(client, sb_token, pid, _and_solution(),
                               time_taken=15)
        assert r2["solved"] is True
        assert r2["xp_earned"] > 0
        assert get_user_xp(client, sb_token) > sb_xp_before

    def test_creator_accumulates_xp_from_multiple_solvers(self, client, conn):
        creator_token = make_creator(client, conn, "cumul_creator")
        creator_xp_before = get_user_xp(client, creator_token)
        pid, _ = create_and_publish_puzzle(client, conn, creator_token,
                                           name="Cumul XP")

        # Three solvers solve
        for i in range(3):
            s_token = register_and_login(client, f"cumul_solver{i}")
            validate_solution(client, s_token, pid, _and_solution(),
                              time_taken=10)

        # Creator XP increased from all three solves
        creator_xp_after = get_user_xp(client, creator_token)
        assert creator_xp_after > creator_xp_before


class TestSolveAndRate:
    """Solver solves a puzzle and then rates it."""

    def test_rate_after_solving(self, client, conn):
        creator_token = make_creator(client, conn, "rate_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token,
                                           name="Rate Me")

        solver_token = register_and_login(client, "rater_solver")

        # Solve first
        validate_solution(client, solver_token, pid, _and_solution(),
                          time_taken=10)

        # Now rate (values must be 1-5)
        resp = client.post(f"/ratings/puzzle/{pid}", json={
            "difficulty": 3, "fun": 4, "clearness": 5,
        }, headers=auth_header(solver_token))
        assert resp.status_code == 200

        # Check metrics
        resp = client.get(f"/ratings/puzzle/{pid}",
                          headers=auth_header(solver_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["my_rating"] is not None
        assert body["my_rating"]["fun"] == 4

    def test_multiple_ratings_update_metrics(self, client, conn):
        creator_token = make_creator(client, conn, "metrics_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token,
                                           name="Metrics Test")

        # Two solvers solve and rate
        for i, (diff, fun, clear) in enumerate([(3, 4, 5), (5, 3, 4)]):
            s_token = register_and_login(client, f"metrics_solver{i}")
            validate_solution(client, s_token, pid, _and_solution(),
                              time_taken=10)
            client.post(f"/ratings/puzzle/{pid}", json={
                "difficulty": diff, "fun": fun, "clearness": clear,
            }, headers=auth_header(s_token))

        # Check aggregate metrics
        check_token = register_and_login(client, "metrics_checker")
        resp = client.get(f"/ratings/puzzle/{pid}",
                          headers=auth_header(check_token))
        assert resp.status_code == 200
        metrics = resp.json()["metrics"]
        assert metrics["count"] == 2


class TestSolveAndDiscuss:
    """After solving, user discusses the puzzle in the forum."""

    def test_solve_then_discuss_puzzle(self, client, conn):
        creator_token = make_creator(client, conn, "disc_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token,
                                           name="Discuss Puzzle")

        solver_token = register_and_login(client, "disc_solver")
        validate_solution(client, solver_token, pid, _and_solution(),
                          time_taken=10)

        # Create a puzzle-specific discussion
        resp = client.post("/discussions", json={
            "title": "My approach to Discuss Puzzle",
            "body": "I used an AND gate approach",
            "category": "solutions",
            "puzzle_id": pid,
        }, headers=auth_header(solver_token))
        assert resp.status_code == 200
        disc = resp.json()
        assert disc["puzzle_id"] == pid

        # Another solver replies
        other_token = register_and_login(client, "other_solver")
        resp = client.post(f"/discussions/{disc['id']}/replies", json={
            "body": "Nice approach! I did something similar.",
        }, headers=auth_header(other_token))
        assert resp.status_code == 200


class TestCreatorNotifications:
    """Creator receives notifications when their puzzle is solved."""

    def test_creator_gets_solve_notification(self, client, conn):
        creator_token = make_creator(client, conn, "notif_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token,
                                           name="Notify Puzzle")

        # Clear any existing notifications
        client.patch("/users/me/notifications/read",
                     headers=auth_header(creator_token))

        # Solver solves
        solver_token = register_and_login(client, "notif_solver")
        validate_solution(client, solver_token, pid, _and_solution(),
                          time_taken=10)

        # Creator should have a notification
        resp = client.get("/users/me/notifications",
                          headers=auth_header(creator_token))
        assert resp.status_code == 200
        notifs = resp.json()
        # At least one notification exists (may include earlier ones)
        assert len(notifs) >= 1


class TestUserIsolation:
    """Users only see their own data where appropriate."""

    def test_circuits_isolated(self, client):
        """User A's saved circuits are not visible to User B."""
        user_a = register_and_login(client, "iso_userA")
        user_b = register_and_login(client, "iso_userB")

        # User A saves a circuit
        resp = client.post("/circuits", json={
            "name": "A's Circuit",
            "structure_json": '{"gates": []}',
        }, headers=auth_header(user_a))
        assert resp.status_code == 200

        # User B sees no circuits
        resp = client.get("/circuits", headers=auth_header(user_b))
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_drafts_isolated(self, client, conn):
        """User A's draft is not visible to User B."""
        creator_token = make_creator(client, conn, "iso_creator")
        from .conftest import create_puzzle
        puzzle = create_puzzle(client, creator_token)
        pid = int(puzzle["id"])

        # Creator saves a draft
        client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"wip": true}',
        }, headers=auth_header(creator_token))

        # Another user sees no draft for same puzzle
        other_token = register_and_login(client, "iso_other")
        resp = client.get(f"/puzzles/{pid}/draft",
                          headers=auth_header(other_token))
        assert resp.status_code == 200
        assert resp.json()["state_json"] is None
