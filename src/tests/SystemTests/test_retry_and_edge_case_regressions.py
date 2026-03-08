from .conftest import (
    auth_header,
    create_and_publish_puzzle,
    create_puzzle,
    add_blackbox_test_case,
    get_user_xp,
    make_creator,
    register_and_login,
    validate_solution,
    _and_solution,
)


class TestMedalAcquisitionEdgeCases:
    def test_exact_time_limit_and_exact_budget_grants_gold(self, client, conn):
        creator_token = make_creator(client, conn, "edge_medal_gold_creator")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="Edge Medal Gold",
            budget=1,
            time_limit=60,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "edge_medal_gold_solver")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=60)

        assert result["solved"] is True
        assert result["medal"] == "GOLD"

    def test_exact_time_limit_with_no_budget_bonus_grants_silver(self, client, conn):
        creator_token = make_creator(client, conn, "edge_medal_timer_creator")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="Edge Medal Timer",
            budget=0,
            time_limit=60,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "edge_medal_timer_solver")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=60)

        assert result["solved"] is True
        assert result["medal"] == "SILVER"

    def test_exact_budget_with_expired_timer_grants_silver(self, client, conn):
        creator_token = make_creator(client, conn, "edge_medal_budget_creator")
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="Edge Medal Budget",
            budget=1,
            time_limit=59,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "edge_medal_budget_solver")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=60)

        assert result["solved"] is True
        assert result["medal"] == "SILVER"


class TestPublishedPuzzleNameUniqueness:
    def test_cannot_rename_to_name_of_another_published_puzzle(self, client, conn):
        creator_a = make_creator(client, conn, "published_name_creator_a")
        pid_a, _ = create_and_publish_puzzle(
            client, conn, creator_a, name="Published Unique Name"
        )

        creator_b = make_creator(client, conn, "published_name_creator_b")
        pid_b, _ = create_and_publish_puzzle(
            client, conn, creator_b, name="Other Published Name"
        )

        resp = client.patch(
            f"/puzzles/{pid_b}",
            json={"name": "Published Unique Name"},
            headers=auth_header(creator_b),
        )

        assert resp.status_code == 403
        assert "already exists" in resp.json()["detail"]

        check_a = client.get(f"/puzzles/{pid_a}", headers=auth_header(creator_a))
        check_b = client.get(f"/puzzles/{pid_b}", headers=auth_header(creator_b))
        assert check_a.status_code == 200
        assert check_b.status_code == 200
        assert check_a.json()["name"] == "Published Unique Name"
        assert check_b.json()["name"] == "Other Published Name"


class TestRatingOverlapSafety:
    def test_multiple_rating_submissions_update_single_rating_without_extra_xp(self, client, conn):
        creator_token = make_creator(client, conn, "rating_overlap_creator")
        creator_xp_before = get_user_xp(client, creator_token)
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="Rating Overlap Puzzle"
        )

        solver_token = register_and_login(client, "rating_overlap_solver")
        solver_xp_before = get_user_xp(client, solver_token)

        first = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 2, "fun": 3, "clearness": 4, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert first.status_code == 200, first.text

        solver_xp_after_first = get_user_xp(client, solver_token)
        creator_xp_after_first = get_user_xp(client, creator_token)
        assert solver_xp_after_first > solver_xp_before
        assert creator_xp_after_first > creator_xp_before

        second = client.put(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 5, "fun": 5, "clearness": 5, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert second.status_code == 200, second.text

        ratings = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(solver_token))
        assert ratings.status_code == 200
        body = ratings.json()
        assert body["metrics"]["count"] == 1
        assert body["my_rating"]["difficulty"] == 5
        assert get_user_xp(client, solver_token) == solver_xp_after_first
        assert get_user_xp(client, creator_token) == creator_xp_after_first


class TestRetrySafety:
    def test_retrying_successful_solve_does_not_double_award_solver_or_creator_xp(self, client, conn):
        creator_token = make_creator(client, conn, "retry_solve_creator")
        creator_xp_before = get_user_xp(client, creator_token)
        pid, _ = create_and_publish_puzzle(
            client,
            conn,
            creator_token,
            name="Retry Solve Puzzle",
            budget=1,
            time_limit=60,
            difficulty="EASY",
        )

        solver_token = register_and_login(client, "retry_solve_solver")
        solver_xp_before = get_user_xp(client, solver_token)

        first = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)
        assert first["solved"] is True
        assert first["xp_earned"] > 0

        solver_xp_after_first = get_user_xp(client, solver_token)
        creator_xp_after_first = get_user_xp(client, creator_token)

        second = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)
        assert second["solved"] is True
        assert second["xp_earned"] == 0

        assert get_user_xp(client, solver_token) == solver_xp_after_first
        assert get_user_xp(client, creator_token) == creator_xp_after_first
        assert solver_xp_after_first > solver_xp_before
        assert creator_xp_after_first > creator_xp_before

    def test_retrying_rating_submission_is_safe(self, client, conn):
        creator_token = make_creator(client, conn, "retry_rating_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="Retry Rating Puzzle"
        )
        solver_token = register_and_login(client, "retry_rating_solver")

        first = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 4, "fun": 4, "clearness": 4, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert first.status_code == 200, first.text
        xp_after_first = get_user_xp(client, solver_token)

        second = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 4, "fun": 4, "clearness": 4, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        )
        assert second.status_code == 400

        ratings = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(solver_token))
        assert ratings.status_code == 200
        assert ratings.json()["metrics"]["count"] == 1
        assert get_user_xp(client, solver_token) == xp_after_first
