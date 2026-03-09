"""
System tests: Complete puzzle lifecycle.

Workflow: register creator → create puzzle → add test cases → self-solve →
publish → solver registers → solver solves → XP & medals awarded →
re-solve for improvement → browse shows puzzle.
"""
from .conftest import (
    auth_header, make_creator, register_and_login,
    create_puzzle, add_blackbox_test_case, validate_solution,
    create_and_publish_puzzle, get_user_xp, get_user_info,
    _and_solution,
)


class TestPuzzleCreationToPublish:
    """Creator creates, adds test cases, self-solves, and publishes."""

    def test_full_creation_flow(self, client, conn):
        creator_token = make_creator(client, conn, "creator1")

        # Step 1: Create puzzle
        puzzle = create_puzzle(client, creator_token, name="AND Gate Challenge",
                               budget=5, time_limit=60)
        pid = int(puzzle["id"])
        assert puzzle["name"] == "AND Gate Challenge"
        assert puzzle["status"] == "draft"

        # Step 2: Add test cases
        tc1 = add_blackbox_test_case(client, creator_token, pid,
                                     {"A": 0, "B": 0}, {"out": 0})
        tc2 = add_blackbox_test_case(client, creator_token, pid,
                                     {"A": 1, "B": 1}, {"out": 1})
        assert tc1 is not None
        assert tc2 is not None

        # Verify test cases are listed
        resp = client.get(f"/puzzles/{pid}/testcases",
                          headers=auth_header(creator_token))
        assert resp.status_code == 200
        assert len(resp.json()) == 2

        # Step 3: Cannot publish without self-solving
        resp = client.post(f"/puzzles/{pid}/publish",
                           headers=auth_header(creator_token))
        assert resp.status_code == 403

        # Step 4: Creator self-solves
        solution = _and_solution()
        result = validate_solution(client, creator_token, pid, solution,
                                   time_taken=10)
        assert result["solved"] is True
        assert result["medal"] in ("BRONZE", "SILVER", "GOLD")

        # Step 5: Now publish succeeds
        resp = client.post(f"/puzzles/{pid}/publish",
                           headers=auth_header(creator_token))
        assert resp.status_code == 200

        # Step 6: Verify puzzle is now published
        resp = client.get(f"/puzzles/{pid}",
                          headers=auth_header(creator_token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

    def test_publish_requires_test_cases(self, client, conn):
        creator_token = make_creator(client, conn, "creator2")
        puzzle = create_puzzle(client, creator_token)
        pid = int(puzzle["id"])

        # Try to publish without any test cases
        resp = client.post(f"/puzzles/{pid}/publish",
                           headers=auth_header(creator_token))
        assert resp.status_code == 403


class TestSolverWorkflow:
    """Solver finds a published puzzle, solves it, earns XP and medals."""

    def test_solve_published_puzzle(self, client, conn):
        creator_token = make_creator(client, conn, "pub_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="Published AND",
            budget=5, time_limit=60,
        )

        # Register solver
        solver_token = register_and_login(client, "solver1")
        solver_xp_before = get_user_xp(client, solver_token)

        # Solver submits correct solution within budget and time
        solution = _and_solution()
        result = validate_solution(client, solver_token, pid, solution,
                                   time_taken=10)
        assert result["solved"] is True
        assert result["xp_earned"] > 0
        assert result["medal"] in ("BRONZE", "SILVER", "GOLD")

        # XP actually increased
        solver_xp_after = get_user_xp(client, solver_token)
        assert solver_xp_after > solver_xp_before

    def test_medals_bronze_silver_gold(self, client, conn):
        """Gold = under budget + under time; Silver = one of the two; Bronze = neither."""
        creator_token = make_creator(client, conn, "medal_creator")

        # Puzzle with budget=5 and time_limit=60
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="Medal Test",
            budget=5, time_limit=60,
        )

        # Solver gets GOLD: cost=1 (under budget=5) + time=10 (under 60)
        solver_token = register_and_login(client, "gold_solver")
        solution = _and_solution()  # totalCost=1
        result = validate_solution(client, solver_token, pid, solution,
                                   time_taken=10)
        assert result["solved"] is True
        assert result["medal"] == "GOLD"

    def test_re_solve_no_extra_xp(self, client, conn):
        """Re-solving with same/worse medal should not award extra XP."""
        creator_token = make_creator(client, conn, "resolv_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, budget=5, time_limit=60)

        solver_token = register_and_login(client, "resolv_solver")

        # First solve → earns XP
        solution = _and_solution()
        r1 = validate_solution(client, solver_token, pid, solution,
                               time_taken=10)
        assert r1["solved"] is True
        xp_first = r1["xp_earned"]
        assert xp_first > 0

        # Second solve → same medal → no improvement
        r2 = validate_solution(client, solver_token, pid, solution,
                               time_taken=10)
        assert r2["solved"] is True
        assert r2["xp_earned"] == 0

    def test_creator_gets_xp_when_other_solves(self, client, conn):
        """When someone else solves a creator's puzzle, the creator earns XP."""
        creator_token = make_creator(client, conn, "rew_creator")
        creator_xp_before = get_user_xp(client, creator_token)

        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="Reward Test",
            budget=5, time_limit=60)

        # Another user solves
        solver_token = register_and_login(client, "rew_solver")
        solution = _and_solution()
        result = validate_solution(client, solver_token, pid, solution,
                                   time_taken=10)
        assert result["solved"] is True

        # Creator XP increased
        creator_xp_after = get_user_xp(client, creator_token)
        assert creator_xp_after > creator_xp_before


class TestBrowseAfterPublish:
    """After publishing, puzzles appear in the browse list."""

    def test_published_puzzle_appears_in_browse(self, client, conn):
        creator_token = make_creator(client, conn, "browse_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token,
                                           name="Browsable Puzzle")

        # Any user can browse
        viewer_token = register_and_login(client, "viewer")
        resp = client.get("/puzzles", headers=auth_header(viewer_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        ids = [int(p["id"]) for p in data]
        assert pid in ids

    def test_my_puzzles_lists_own(self, client, conn):
        creator_token = make_creator(client, conn, "my_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token,
                                           name="My Puzzle")

        resp = client.get("/puzzles/my-puzzles/list",
                          headers=auth_header(creator_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        ids = [int(p["id"]) for p in data]
        assert pid in ids
