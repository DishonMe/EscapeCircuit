"""
================================================================================
ACCEPTANCE TESTS  —  Application Design Document (ADD) Chapter 1.2
================================================================================

Each class below corresponds to ONE Use Case from the ADD ("1.2 Use-Cases -
Acceptance Tests").  Each test method corresponds to ONE row of that Use Case's
"Acceptance Tests" table, and the method name + docstring carry the exact
"Test Name" used in the ADD so a human can line the two up side-by-side.

Naming convention:   test_uc<N>_<add_test_name_in_snake_case>
Docstring format:    "UC<N> · <Test Name> (ADD p.<page>) — <expected result>"

These run against the real wired FastAPI app on an in-memory SQLite database
(see conftest.py).  They are the automated half of the ADD's "Acceptance
Testing" strategy (Chapter 7.1, item 4).

Use-Case index (ADD pp.6-43):
    UC1  Browse and Search Puzzles            UC8  Puzzle Solution Validation
    UC2  Solve a Puzzle                        UC9  Appoint User as Creator
    UC3  Save and Reuse Circuits               UC10 View Personal Profile & Progress
    UC4  Create and Publish Puzzle             UC11 Experiment in Sandbox
    UC5  Rate a Puzzle                         UC12 Manage Personal Arsenal
    UC6  Earn Rewards and Level Up             UC13 Participate in Discussions
    UC7  Manage Puzzles (Creators Only)        UC14 Manage Notifications
================================================================================
"""
import json

from .conftest import (
    auth_header,
    register_and_login,
    make_creator,
    make_admin,
    get_user_info,
    get_user_xp,
    create_puzzle,
    add_blackbox_test_case,
    validate_solution,
    create_and_publish_puzzle,
    _and_solution,
)


# ── Local payload helpers ────────────────────────────────────────────────────

def _arsenal_payload(name: str, basic_gates: str = '["AND"]') -> dict:
    """A minimal, legal arsenal piece (uses only default I/O)."""
    return {
        "name": name,
        "num_inputs": 1,
        "num_outputs": 1,
        "structure_json": json.dumps({"placedComponents": [], "wires": []}),
        "basic_gates": basic_gates,
        "truth_table": {"0": "0", "1": "1"},
    }


def _and_solution_with_extra_gate() -> dict:
    """A correct AND solution that uses an extra (NOT) gate — used to trip the
    gate-count / value limit."""
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


def _create_discussion(client, token, title="Discussion", body="body", category="general"):
    resp = client.post(
        "/discussions",
        json={"title": title, "body": body, "category": category},
        headers=auth_header(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_reply(client, token, discussion_id, body="reply", parent_reply_id=None):
    payload = {"body": body}
    if parent_reply_id is not None:
        payload["parent_reply_id"] = parent_reply_id
    return client.post(
        f"/discussions/{discussion_id}/replies",
        json=payload,
        headers=auth_header(token),
    )


# ══════════════════════════════════════════════════════════════════════════════
# UC1 — Browse and Search Puzzles                                      ADD p.6-7
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc1_successful_search : Logged-in user searches with filters and gets back the matching puzzles.
#   test_uc1_unsuccessful_search_no_matches : A search that matches nothing returns an empty list.
#   test_uc1_unsuccessful_unauthorized_access : Searching without logging in is blocked (401).
# ══════════════════════════════════════════════════════════════════════════════
class TestUC1BrowseAndSearchPuzzles:

    def test_uc1_successful_search(self, client, conn):
        """UC1 · Successful Search (ADD p.7) — logged-in user searching with
        filters gets the matching published puzzles back."""
        creator_token = make_creator(client, conn, "acc_uc1_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token,
            name="ACC UC1 Search Target", budget=5, time_limit=60, difficulty="HARD",
        )

        solver_token = register_and_login(client, "acc_uc1_solver")
        resp = client.get(
            "/puzzles",
            params={"search": "Search Target"},
            headers=auth_header(solver_token),
        )
        assert resp.status_code == 200
        assert pid in [int(p["id"]) for p in resp.json()["data"]]

    def test_uc1_unsuccessful_search_no_matches(self, client):
        """UC1 · Unsuccessful Search: No Matches (ADD p.7) — empty list when no
        puzzle matches the filters."""
        solver_token = register_and_login(client, "acc_uc1_nomatch")
        resp = client.get(
            "/puzzles",
            params={"search": "definitely-no-such-puzzle"},
            headers=auth_header(solver_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_uc1_unsuccessful_unauthorized_access(self, client):
        """UC1 · Unsuccessful unauthorized Access (ADD p.7) — anonymous request
        is rejected (appropriate message / 401)."""
        resp = client.get("/puzzles", params={"search": "anything"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# UC2 — Solve a Puzzle                                                ADD p.8-12
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc2_successful_solve_within_limits : Correct circuit, in time and budget -> solved, with XP and a medal.
#   test_uc2_unsuccessful_wrong_solution : A wrong circuit is not accepted and earns no XP.
#   test_uc2_unsuccessful_exceeded_the_value_limit : A circuit that uses too many gates is rejected.
#   test_uc2_unsuccessful_time_expired : Correct but late -> still solved, but only a bronze medal.
#   test_uc2_successful_leaderboard_ranking : Solvers are listed on the puzzle leaderboard, fastest first.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC2SolveAPuzzle:

    def test_uc2_successful_solve_within_limits(self, client, conn):
        """UC2 · Successful solve within limits (ADD p.10) — valid solution
        within limits & time remaining → solved, XP & Timer Medal."""
        creator_token = make_creator(client, conn, "acc_uc2_ok_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ACC UC2 Solve OK", budget=5, time_limit=60
        )
        solver_token = register_and_login(client, "acc_uc2_ok_solver")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)
        assert result["solved"] is True
        assert result["xp_earned"] > 0
        assert result["medal"] == "SILVER"

    def test_uc2_unsuccessful_wrong_solution(self, client, conn):
        """UC2 · Unsuccessful wrong solution (ADD p.10) — incorrect circuit →
        Not Solved, no XP."""
        creator_token = make_creator(client, conn, "acc_uc2_wrong_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ACC UC2 Wrong", budget=5, time_limit=60
        )
        solver_token = register_and_login(client, "acc_uc2_wrong_solver")
        result = validate_solution(
            client, solver_token, pid,
            {"placedComponents": [], "wires": [], "totalCost": 0}, time_taken=10,
        )
        assert result["solved"] is False

    def test_uc2_unsuccessful_exceeded_the_value_limit(self, client, conn):
        """UC2 · Unsuccessful exceeded the value limit (ADD p.10) — a submission
        that exceeds the puzzle's allowed value is blocked (not solved)."""
        creator_token = make_creator(client, conn, "acc_uc2_limit_creator")
        puzzle = create_puzzle(client, creator_token, name="ACC UC2 Limit", budget=5, time_limit=60)
        pid = int(puzzle["id"])
        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        assert validate_solution(client, creator_token, pid, _and_solution(), time_taken=10)["solved"] is True
        assert client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token)).status_code == 200

        # Lock the puzzle to a 1-gate budget, then submit a 2-gate solution.
        conn.execute("UPDATE puzzles SET total_gate_count = 1 WHERE id = ?", (pid,))
        client.post(
            f"/puzzles/{pid}/testcases",
            json={"kind": "gate_count_limit", "inputs": {}, "expected_outputs": {}},
            headers=auth_header(creator_token),
        )
        solver_token = register_and_login(client, "acc_uc2_limit_solver")
        result = validate_solution(client, solver_token, pid, _and_solution_with_extra_gate(), time_taken=10)
        assert result["solved"] is False

    def test_uc2_unsuccessful_time_expired(self, client, conn):
        """UC2 · Unsuccessful time expired (ADD p.11) — correct solution after
        the timer expires → solved but no Timer Medal (BRONZE)."""
        creator_token = make_creator(client, conn, "acc_uc2_time_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ACC UC2 Time", budget=5, time_limit=60
        )
        solver_token = register_and_login(client, "acc_uc2_time_solver")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=120)
        assert result["solved"] is True
        assert result["medal"] == "BRONZE"

    def test_uc2_successful_leaderboard_ranking(self, client, conn):
        """UC2 · Successful leaderboard ranking (ADD p.11) — solvers appear on
        the per-puzzle leaderboard ranked by fastest time (top of the podium)."""
        creator_token = make_creator(client, conn, "acc_uc2_lb_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ACC UC2 Leaderboard", budget=5, time_limit=60
        )
        slow = register_and_login(client, "acc_uc2_lb_slow")
        fast = register_and_login(client, "acc_uc2_lb_fast")
        mid = register_and_login(client, "acc_uc2_lb_mid")
        validate_solution(client, slow, pid, _and_solution(), time_taken=30)
        validate_solution(client, fast, pid, _and_solution(), time_taken=15)
        validate_solution(client, mid, pid, _and_solution(), time_taken=20)

        lb = client.get(f"/puzzles/{pid}/leaderboard", headers=auth_header(fast))
        assert lb.status_code == 200, lb.text
        entries = lb.json()["data"]
        assert [e["rank"] for e in entries[:4]] == [1, 2, 3, 4]
        assert [e["best_time"] for e in entries[:4]] == [10, 15, 20, 30]  # creator self-solved at 10


# ══════════════════════════════════════════════════════════════════════════════
# UC3 — Save and Reuse Circuits                                      ADD p.13-15
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc3_successful_save_to_arsenal : Saving a valid circuit makes it show up in your arsenal.
#   test_uc3_successful_reuse_compatibility : A saved circuit shows up only for puzzles that allow its gates.
#   test_uc3_unsuccessful_name_collision : You can't save two circuits with the same name.
#   test_uc3_unsuccessful_arsenal_full : Once your arsenal is full, saving is blocked.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC3SaveAndReuseCircuits:

    def test_uc3_successful_save_to_arsenal(self, client):
        """UC3 · Successful save to arsenal (ADD p.15) — a legal circuit is saved
        and appears in the user's arsenal."""
        token = register_and_login(client, "acc_uc3_save")
        resp = client.post("/arsenal", json=_arsenal_payload("acc-uc3-piece"), headers=auth_header(token))
        assert resp.status_code == 200, resp.text
        names = [p["name"] for p in client.get("/arsenal", headers=auth_header(token)).json()]
        assert "acc-uc3-piece" in names

    def test_uc3_successful_reuse_compatibility(self, client, conn):
        """UC3 · Successful reuse compatibility (ADD p.15) — a saved circuit is
        offered for a puzzle that allows its gates, and hidden when a required
        default is missing."""
        creator_token = make_creator(client, conn, "acc_uc3_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC3 Reuse")
        token = register_and_login(client, "acc_uc3_reuse")
        assert client.post(
            "/arsenal", json=_arsenal_payload("acc-uc3-compat", basic_gates='["AND"]'),
            headers=auth_header(token),
        ).status_code == 200

        available = client.get(
            f"/arsenal/puzzle/{pid}/available", params={"allowed_gates": "AND,OR,NOT"},
            headers=auth_header(token),
        )
        assert "acc-uc3-compat" in [p["type"] for p in available.json()]

        missing = client.get(
            f"/arsenal/puzzle/{pid}/available", params={"allowed_gates": "OR,NOT"},
            headers=auth_header(token),
        )
        assert "acc-uc3-compat" not in [p["type"] for p in missing.json()]

    def test_uc3_unsuccessful_name_collision(self, client):
        """UC3 · Unsuccessful name collision (ADD p.15) — save rejected when the
        arsenal already has a circuit with that name."""
        token = register_and_login(client, "acc_uc3_collide")
        assert client.post("/arsenal", json=_arsenal_payload("dup"), headers=auth_header(token)).status_code == 200
        second = client.post("/arsenal", json=_arsenal_payload("dup"), headers=auth_header(token))
        assert second.status_code == 400
        assert "already exists" in second.json()["detail"]

    def test_uc3_unsuccessful_arsenal_full(self, client):
        """UC3 · Unsuccessful arsenal full (ADD p.15) — save denied once the
        level-based arsenal capacity (5 at low level) is reached."""
        token = register_and_login(client, "acc_uc3_full")
        for idx in range(5):
            assert client.post("/arsenal", json=_arsenal_payload(f"p{idx}"), headers=auth_header(token)).status_code == 200
        overflow = client.post("/arsenal", json=_arsenal_payload("p-overflow"), headers=auth_header(token))
        assert overflow.status_code == 400
        assert "capacity reached" in overflow.json()["detail"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# UC4 — Create and Publish Puzzle                                    ADD p.16-20
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc4_successful_valid_publish : Valid puzzle + creator solves it -> it gets published.
#   test_uc4_unsuccessful_self_solve_fails : If the creator can't solve their own puzzle, it can't be published.
#   test_uc4_unsuccessful_duplicate_name : A puzzle name that already exists is rejected.
#   test_uc4_unsuccessful_invalid_limits : Bad settings (like a negative budget) block creation.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC4CreateAndPublishPuzzle:

    def test_uc4_successful_valid_publish(self, client, conn):
        """UC4 · Successful valid publish (ADD p.18) — all data valid + creator
        self-solves → puzzle published with an upload datetime set."""
        creator_token = make_creator(client, conn, "acc_uc4_pub")
        puzzle = create_puzzle(client, creator_token, name="ACC UC4 Publish", budget=5, time_limit=60, difficulty="HARD")
        pid = int(puzzle["id"])
        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        assert validate_solution(client, creator_token, pid, _and_solution(), time_taken=10)["solved"] is True
        publish = client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token))
        assert publish.status_code == 200, publish.text
        assert publish.json()["status"] == "published"
        assert publish.json()["created_at"]

    def test_uc4_unsuccessful_self_solve_fails(self, client, conn):
        """UC4 · Unsuccessful self-solve fails (ADD p.18) — creator cannot solve
        within the greater limits → upload blocked (publish forbidden)."""
        creator_token = make_creator(client, conn, "acc_uc4_selffail")
        puzzle = create_puzzle(client, creator_token, name="ACC UC4 SelfFail", budget=5, time_limit=60)
        pid = int(puzzle["id"])
        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        assert validate_solution(
            client, creator_token, pid,
            {"placedComponents": [], "wires": [], "totalCost": 0}, time_taken=10,
        )["solved"] is False
        assert client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token)).status_code == 403

    def test_uc4_unsuccessful_duplicate_name(self, client, conn):
        """UC4 · Unsuccessful duplicate name (ADD p.18) — a puzzle name that
        collides with an existing one is rejected."""
        creator_token = make_creator(client, conn, "acc_uc4_dup")
        body = {"name": "ACC UC4 Dup", "description": "x", "budget": 5,
                "default_gate_set": ["AND", "OR", "NOT"], "difficulty": "EASY"}
        assert client.post("/puzzles", json=body, headers=auth_header(creator_token)).status_code == 200
        second = client.post("/puzzles", json={**body, "description": "y"}, headers=auth_header(creator_token))
        assert second.status_code == 400
        assert "already exists" in second.json()["detail"].lower()

    def test_uc4_unsuccessful_invalid_limits(self, client, conn):
        """UC4 · Unsuccessful invalid limits (ADD p.18-19) — invalid limits
        (negative budget) → validation error, upload prevented."""
        creator_token = make_creator(client, conn, "acc_uc4_invalid")
        resp = client.post(
            "/puzzles",
            json={"name": "ACC UC4 Invalid", "description": "x", "budget": -1,
                  "default_gate_set": ["AND"], "difficulty": "EASY"},
            headers=auth_header(creator_token),
        )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# UC5 — Rate a Puzzle                                                ADD p.21-23
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc5_successful_valid_rating_pre_10 : With few ratings, difficulty follows mostly the creator's rating.
#   test_uc5_successful_experienced_weighting : An experienced player's rating counts in both the overall and experienced-only scores.
#   test_uc5_successful_post_10_shift : After 10 ratings, players' ratings outweigh the creator's.
#   test_uc5_successful_edit_rating : Changing your rating updates the score but gives no extra XP.
#   test_uc5_unsuccessful_ineligible_rating : You can't rate a puzzle you haven't solved or spent enough time on.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC5RateAPuzzle:

    def test_uc5_successful_valid_rating_pre_10(self, client, conn):
        """UC5 · Successful valid rating (Pre-10) (ADD p.22) — with <10 ratings
        difficulty blends 80% creator + 20% user average."""
        creator_token = make_creator(client, conn, "acc_uc5_pre10_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ACC UC5 Pre10", budget=5, time_limit=60, difficulty="HARD"
        )
        solver_token = register_and_login(client, "acc_uc5_pre10_solver")
        assert client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 1, "fun": 4, "clearness": 4, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        ).status_code == 200
        metrics = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(solver_token)).json()["metrics"]
        # creator HARD=5, user diff=1 → 0.8*5 + 0.2*1 = 4.2
        assert metrics["weighted_difficulty"] == 4.2

    def test_uc5_successful_experienced_weighting(self, client, conn):
        """UC5 · Successful experienced weighting (ADD p.22) — an experienced
        (level >= 5) rater is counted in both the general and experienced-only
        averages."""
        creator_token = make_creator(client, conn, "acc_uc5_exp_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC5 Exp")
        solver_token = register_and_login(client, "acc_uc5_exp_solver")
        me = get_user_info(client, solver_token)
        conn.execute("UPDATE users SET xp = 2500 WHERE id = ?", (me["id"],))  # level 6 → experienced
        assert client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 3, "fun": 4, "clearness": 5, "elapsed_seconds": 300},
            headers=auth_header(solver_token),
        ).status_code == 200
        metrics = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(solver_token)).json()["metrics"]
        assert metrics["count"] == 1
        assert metrics["experienced"]["count"] == 1

    def test_uc5_successful_post_10_shift(self, client, conn):
        """UC5 · Successful post-10 shift (ADD p.22) — once a puzzle reaches >=10
        ratings the weighting shifts to 40% creator / 60% user."""
        creator_token = make_creator(client, conn, "acc_uc5_post10_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC5 Post10", difficulty="HARD")
        for idx in range(10):
            token = register_and_login(client, f"acc_uc5_post10_{idx}")
            assert client.post(
                f"/ratings/puzzle/{pid}",
                json={"difficulty": 1, "fun": 3, "clearness": 3, "elapsed_seconds": 300},
                headers=auth_header(token),
            ).status_code == 200
        reader = register_and_login(client, "acc_uc5_post10_reader")
        metrics = client.get(f"/ratings/puzzle/{pid}", headers=auth_header(reader)).json()["metrics"]
        assert metrics["count"] == 10
        # creator HARD=5, user diff=1 → 0.4*5 + 0.6*1 = 2.6
        assert metrics["weighted_difficulty"] == 2.6

    def test_uc5_successful_edit_rating(self, client, conn):
        """UC5 · Successful edit rating (ADD p.22) — editing an existing rating
        recalculates aggregates and grants NO additional XP."""
        creator_token = make_creator(client, conn, "acc_uc5_edit_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC5 Edit")
        token = register_and_login(client, "acc_uc5_edit_solver")
        assert client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 2, "fun": 2, "clearness": 2, "elapsed_seconds": 300},
            headers=auth_header(token),
        ).status_code == 200
        xp_after_first = get_user_xp(client, token)
        assert client.put(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 5, "fun": 5, "clearness": 4, "elapsed_seconds": 300},
            headers=auth_header(token),
        ).status_code == 200
        assert get_user_xp(client, token) == xp_after_first  # no extra XP
        assert client.get(f"/ratings/puzzle/{pid}", headers=auth_header(token)).json()["my_rating"]["difficulty"] == 5

    def test_uc5_unsuccessful_ineligible_rating(self, client, conn):
        """UC5 · Unsuccessful ineligible rating (ADD p.22) — attempted <5 minutes
        and not solved → rating rejected."""
        creator_token = make_creator(client, conn, "acc_uc5_inelig_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC5 Ineligible")
        token = register_and_login(client, "acc_uc5_inelig_solver")
        resp = client.post(
            f"/ratings/puzzle/{pid}",
            json={"difficulty": 3, "fun": 3, "clearness": 3, "elapsed_seconds": 120},
            headers=auth_header(token),
        )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# UC6 — Earn Rewards and Level Up                                    ADD p.24-26
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc6_successful_standard_xp : Solving gives XP based on the puzzle's difficulty.
#   test_uc6_successful_medal_upgrade : Solving better (faster / cheaper) upgrades your medal.
#   test_uc6_successful_level_up : Earning enough XP moves you up a level.
#   test_uc6_unsuccessful_repeat_timer : Solving the same puzzle again gives no extra reward.
#   test_uc6_successful_leaderboard_after_reward : After solving, you appear on the puzzle's leaderboard.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC6EarnRewardsAndLevelUp:

    def test_uc6_successful_standard_xp(self, client, conn):
        """UC6 · Successful standard XP (ADD p.25) — XP awarded per difficulty
        tier (HARD = 200 base)."""
        creator_token = make_creator(client, conn, "acc_uc6_xp_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ACC UC6 XP", budget=0, time_limit=5, difficulty="HARD"
        )
        solver_token = register_and_login(client, "acc_uc6_xp_solver")
        result = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)
        assert result["solved"] is True
        assert result["medal"] == "BRONZE"  # time expired & budget 0
        assert result["xp_earned"] == 200

    def test_uc6_successful_medal_upgrade(self, client, conn):
        """UC6 · Successful medal upgrade (ADD p.25) — solving within the greater
        (value/time) limits upgrades the medal (bronze → silver)."""
        creator_token = make_creator(client, conn, "acc_uc6_upg_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ACC UC6 Upgrade", budget=1, time_limit=60, difficulty="EASY"
        )
        solver_token = register_and_login(client, "acc_uc6_upg_solver")
        first = validate_solution(client, solver_token, pid, _and_solution(), time_taken=120)
        second = validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)
        assert first["medal"] == "BRONZE"
        assert second["medal"] == "SILVER"

    def test_uc6_successful_level_up(self, client, conn):
        """UC6 · Successful level up (ADD p.25) — when XP crosses the next level
        threshold the user's level increases."""
        creator_token = make_creator(client, conn, "acc_uc6_lvl_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ACC UC6 Level", budget=0, time_limit=None, difficulty="EASY"
        )
        token = register_and_login(client, "acc_uc6_lvl_solver")
        me = get_user_info(client, token)
        conn.execute("UPDATE users SET xp = 399 WHERE id = ?", (me["id"],))
        before = get_user_info(client, token)
        validate_solution(client, token, pid, _and_solution(), time_taken=10)
        after = get_user_info(client, token)
        assert after["level"] == before["level"] + 1

    def test_uc6_unsuccessful_repeat_timer(self, client, conn):
        """UC6 · Unsuccessful repeat timer (ADD p.25) — a second/subsequent win on
        the same puzzle grants no extra Timer Medal or alt-solution bonus."""
        creator_token = make_creator(client, conn, "acc_uc6_rep_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ACC UC6 Repeat", budget=5, time_limit=60, difficulty="EASY"
        )
        token = register_and_login(client, "acc_uc6_rep_solver")
        first = validate_solution(client, token, pid, _and_solution(), time_taken=10)
        second = validate_solution(client, token, pid, _and_solution(), time_taken=10)
        assert first["solved"] is True
        assert second["xp_earned"] == 0

    def test_uc6_successful_leaderboard_after_reward(self, client, conn):
        """UC6 · Successful leaderboard after reward (ADD p.26) — after solving &
        earning a medal the user appears on the puzzle leaderboard."""
        creator_token = make_creator(client, conn, "acc_uc6_lb_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ACC UC6 LB", budget=5, time_limit=60, difficulty="EASY"
        )
        token = register_and_login(client, "acc_uc6_lb_solver")
        info = get_user_info(client, token)
        validate_solution(client, token, pid, _and_solution(), time_taken=10)
        lb = client.get(f"/puzzles/{pid}/leaderboard", headers=auth_header(token))
        assert lb.status_code == 200
        assert int(info["id"]) in [e["user_id"] for e in lb.json()["data"]]


# ══════════════════════════════════════════════════════════════════════════════
# UC7 — Manage Puzzles (Creators Only)                               ADD p.27-29
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc7_successful_comment_addition : A creator can add a comment to their puzzle.
#   test_uc7_successful_edit_comment : A creator can change their puzzle's comment.
#   test_uc7_successful_delete_comment : A creator can clear their puzzle's comment.
#   test_uc7_successful_delete_puzzle : A creator can delete their puzzle.
#   test_uc7_unsuccessful_unauthorized : You can't edit or delete someone else's puzzle.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC7ManagePuzzlesCreatorsOnly:

    def test_uc7_successful_comment_addition(self, client, conn):
        """UC7 · Successful comment addition (ADD p.28) — creator adds a comment
        (description) to their puzzle; it is stored and visible."""
        creator_token = make_creator(client, conn, "acc_uc7_add")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC7 Add")
        assert client.patch(
            f"/puzzles/{pid}", json={"description": "new comment"}, headers=auth_header(creator_token)
        ).status_code == 200
        assert client.get(f"/puzzles/{pid}", headers=auth_header(creator_token)).json()["description"] == "new comment"

    def test_uc7_successful_edit_comment(self, client, conn):
        """UC7 · Successful edit comment (ADD p.28) — creator edits the comment;
        it is replaced."""
        creator_token = make_creator(client, conn, "acc_uc7_edit")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC7 Edit")
        client.patch(f"/puzzles/{pid}", json={"description": "old"}, headers=auth_header(creator_token))
        client.patch(f"/puzzles/{pid}", json={"description": "updated"}, headers=auth_header(creator_token))
        assert client.get(f"/puzzles/{pid}", headers=auth_header(creator_token)).json()["description"] == "updated"

    def test_uc7_successful_delete_comment(self, client, conn):
        """UC7 · Successful delete comment (ADD p.28) — creator clears the comment
        (removed from the puzzle page)."""
        creator_token = make_creator(client, conn, "acc_uc7_delc")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC7 DelComment")
        client.patch(f"/puzzles/{pid}", json={"description": "delete me"}, headers=auth_header(creator_token))
        client.patch(f"/puzzles/{pid}", json={"description": ""}, headers=auth_header(creator_token))
        assert client.get(f"/puzzles/{pid}", headers=auth_header(creator_token)).json()["description"] == ""

    def test_uc7_successful_delete_puzzle(self, client, conn):
        """UC7 · Successful delete puzzle (ADD p.28) — creator deletes the puzzle;
        it is removed from public listings."""
        creator_token = make_creator(client, conn, "acc_uc7_delp")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC7 DelPuzzle")
        assert client.delete(f"/puzzles/{pid}", headers=auth_header(creator_token)).status_code == 200
        assert client.get(f"/puzzles/{pid}", headers=auth_header(creator_token)).status_code == 404

    def test_uc7_unsuccessful_unauthorized(self, client, conn):
        """UC7 · Unsuccessful unauthorized (ADD p.29) — a different creator cannot
        edit/delete a puzzle they don't own (permission denied)."""
        owner_token = make_creator(client, conn, "acc_uc7_owner")
        pid, _ = create_and_publish_puzzle(client, conn, owner_token, name="ACC UC7 Forbidden")
        other = make_creator(client, conn, "acc_uc7_other")
        assert client.patch(f"/puzzles/{pid}", json={"description": "x"}, headers=auth_header(other)).status_code == 403
        assert client.delete(f"/puzzles/{pid}", headers=auth_header(other)).status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# UC8 — Puzzle Solution Validation                                   ADD p.30-31
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc8_successful_correct_solution : A correct circuit passes validation.
#   test_uc8_unsuccessful_incorrect_solution : A wrong circuit fails validation.
#   test_uc8_unsuccessful_limits_were_broken : A circuit that breaks the limits fails, even if it's logically correct.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC8PuzzleSolutionValidation:

    def test_uc8_successful_correct_solution(self, client, conn):
        """UC8 · Successful correct solution (ADD p.31) — system checks the test
        cases and returns true for a correct solution."""
        creator_token = make_creator(client, conn, "acc_uc8_ok_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC8 Correct")
        token = register_and_login(client, "acc_uc8_ok_solver")
        assert validate_solution(client, token, pid, _and_solution(), time_taken=10)["solved"] is True

    def test_uc8_unsuccessful_incorrect_solution(self, client, conn):
        """UC8 · Unsuccessful incorrect solution (ADD p.31) — system returns false
        for a solution that fails the test cases."""
        creator_token = make_creator(client, conn, "acc_uc8_bad_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC8 Incorrect")
        token = register_and_login(client, "acc_uc8_bad_solver")
        result = validate_solution(
            client, token, pid, {"placedComponents": [], "wires": [], "totalCost": 0}, time_taken=10
        )
        assert result["solved"] is False

    def test_uc8_unsuccessful_limits_were_broken(self, client, conn):
        """UC8 · Unsuccessful limits were broken (ADD p.31) — a circuit that
        breaks the puzzle limits is rejected (returns false)."""
        creator_token = make_creator(client, conn, "acc_uc8_lim_creator")
        puzzle = create_puzzle(client, creator_token, name="ACC UC8 Limits", budget=5, time_limit=60)
        pid = int(puzzle["id"])
        add_blackbox_test_case(client, creator_token, pid, {"A": 0, "B": 0}, {"out": 0})
        add_blackbox_test_case(client, creator_token, pid, {"A": 1, "B": 1}, {"out": 1})
        validate_solution(client, creator_token, pid, _and_solution(), time_taken=10)
        assert client.post(f"/puzzles/{pid}/publish", headers=auth_header(creator_token)).status_code == 200
        conn.execute("UPDATE puzzles SET total_gate_count = 1 WHERE id = ?", (pid,))
        client.post(
            f"/puzzles/{pid}/testcases",
            json={"kind": "gate_count_limit", "inputs": {}, "expected_outputs": {}},
            headers=auth_header(creator_token),
        )
        token = register_and_login(client, "acc_uc8_lim_solver")
        result = validate_solution(client, token, pid, _and_solution_with_extra_gate(), time_taken=10)
        assert result["solved"] is False


# ══════════════════════════════════════════════════════════════════════════════
# UC9 — Appoint User as Creator                                      ADD p.32-33
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc9_successful_appointment : An admin can promote a player toward becoming a creator.
#   test_uc9_successful_already_appointed : Promoting someone who's already a creator is reported as such.
#   test_uc9_unsuccessful_unauthorized : A non-admin can't promote anyone.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC9AppointUserAsCreator:

    def test_uc9_successful_appointment(self, client, conn):
        """UC9 · Successful Appointment (ADD p.33) — admin appoints a solver; the
        system records the appointment (target becomes pending_creator)."""
        admin_token = make_admin(client, conn, "acc_uc9_admin")
        target = register_and_login(client, "acc_uc9_target")
        target_info = get_user_info(client, target)
        resp = client.post(
            "/admin/assign-creator",
            json={"target_user_id": target_info["id"]},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200, resp.text
        assert get_user_info(client, target)["role"] == "pending_creator"

    def test_uc9_successful_already_appointed(self, client, conn):
        """UC9 · Successful already appointed (ADD p.33) — appointing an existing
        creator notifies that the user is already a creator."""
        admin_token = make_admin(client, conn, "acc_uc9_admin2")
        creator_token = make_creator(client, conn, "acc_uc9_existing")
        creator_info = get_user_info(client, creator_token)
        resp = client.post(
            "/admin/assign-creator",
            json={"target_user_id": creator_info["id"]},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 400
        assert "already" in resp.json()["detail"].lower()

    def test_uc9_unsuccessful_unauthorized(self, client):
        """UC9 · Unsuccessful - Unauthorized (ADD p.33) — a non-admin attempting
        the appointment is denied."""
        solver = register_and_login(client, "acc_uc9_nonadmin")
        target = register_and_login(client, "acc_uc9_target2")
        resp = client.post(
            "/admin/assign-creator",
            json={"target_user_id": get_user_info(client, target)["id"]},
            headers=auth_header(solver),
        )
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# UC10 — View Personal Profile & Progress                            ADD p.34-35
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc10_successful_profile_load : The profile shows your XP, level and medals.
#   test_uc10_successful_puzzle_access : The profile lists the puzzles you saved for later.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC10ViewPersonalProfile:

    def test_uc10_successful_profile_load(self, client, conn):
        """UC10 · Successful Profile Load (ADD p.35) — profile shows the user's
        level, XP and medal counts."""
        creator_token = make_creator(client, conn, "acc_uc10_creator")
        pid, _ = create_and_publish_puzzle(
            client, conn, creator_token, name="ACC UC10 Medal", budget=1, time_limit=60
        )
        token = register_and_login(client, "acc_uc10_solver")
        before = get_user_info(client, token)
        conn.execute("UPDATE users SET xp = 500 WHERE id = ?", (before["id"],))
        validate_solution(client, token, pid, _and_solution(), time_taken=10)
        body = client.get("/users/me", headers=auth_header(token)).json()
        assert body["xp"] >= 500
        assert body["level"] >= before["level"]
        assert body["medals"]["silver"] >= 1

    def test_uc10_successful_puzzle_access(self, client, conn):
        """UC10 · Successful Puzzle Access (ADD p.35) — profile exposes the user's
        clickable list of saved-for-later puzzles."""
        creator_token = make_creator(client, conn, "acc_uc10_saved_creator")
        token = register_and_login(client, "acc_uc10_saved_solver")
        info = get_user_info(client, token)
        saved_ids = []
        for idx in range(3):
            pid, _ = create_and_publish_puzzle(client, conn, creator_token, name=f"ACC UC10 Saved {idx}")
            saved_ids.append(pid)
            conn.execute(
                "INSERT INTO saved_puzzles(user_id, puzzle_id, created_at) VALUES (?, ?, datetime('now'))",
                (int(info["id"]), int(pid)),
            )
        body = client.get("/users/me", headers=auth_header(token)).json()
        assert {int(p["id"]) for p in body["saved_puzzles"]} == set(saved_ids)


# ══════════════════════════════════════════════════════════════════════════════
# UC11 — Experiment in Sandbox                                       ADD p.36-37
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc11_successful_sandbox_save : A circuit built in the sandbox can be saved to your arsenal.
#   test_uc11_unsuccessful_arsenal_full : Saving from the sandbox is blocked when the arsenal is full.
#   test_uc11_unsuccessful_name_collision : Saving from the sandbox is blocked when the name is taken.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC11ExperimentInSandbox:

    def test_uc11_successful_sandbox_save(self, client):
        """UC11 · Successful Sandbox Save (ADD p.37) — a valid sandbox circuit is
        saved to the arsenal for future puzzles."""
        token = register_and_login(client, "acc_uc11_save")
        assert client.post("/arsenal", json=_arsenal_payload("MyAdder"), headers=auth_header(token)).status_code == 200
        assert "MyAdder" in [p["name"] for p in client.get("/arsenal", headers=auth_header(token)).json()]

    def test_uc11_unsuccessful_arsenal_full(self, client):
        """UC11 · Unsuccessful - Arsenal Full (ADD p.37) — save rejected with a
        capacity error once the level-based arsenal capacity is reached."""
        token = register_and_login(client, "acc_uc11_full")
        for idx in range(5):
            assert client.post("/arsenal", json=_arsenal_payload(f"acc-uc11-{idx}"), headers=auth_header(token)).status_code == 200
        overflow = client.post("/arsenal", json=_arsenal_payload("acc-uc11-overflow"), headers=auth_header(token))
        assert overflow.status_code == 400
        assert "capacity reached" in overflow.json()["detail"].lower()

    def test_uc11_unsuccessful_name_collision(self, client):
        """UC11 · Unsuccessful - Name collision (ADD p.37) — save rejected with a
        naming error when the name already exists."""
        token = register_and_login(client, "acc_uc11_collide")
        assert client.post("/arsenal", json=_arsenal_payload("A"), headers=auth_header(token)).status_code == 200
        second = client.post("/arsenal", json=_arsenal_payload("A"), headers=auth_header(token))
        assert second.status_code == 400
        assert "already exists" in second.json()["detail"]


# ══════════════════════════════════════════════════════════════════════════════
# UC12 — Manage Personal Arsenal                                     ADD p.38-39
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc12_successful_deletion : You can delete a saved circuit from your arsenal.
#   test_uc12_successful_rename : You can rename a saved circuit.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC12ManagePersonalArsenal:

    def test_uc12_successful_deletion(self, client):
        """UC12 · Successful Deletion (ADD p.39) — deleting a saved circuit removes
        it and updates the count."""
        token = register_and_login(client, "acc_uc12_delete")
        created = client.post("/arsenal", json=_arsenal_payload("Old_Circuit"), headers=auth_header(token))
        assert created.status_code == 200, created.text
        assert client.delete(f"/arsenal/{created.json()['id']}", headers=auth_header(token)).status_code == 200
        assert "Old_Circuit" not in [p["name"] for p in client.get("/arsenal", headers=auth_header(token)).json()]

    def test_uc12_successful_rename(self, client):
        """UC12 · Successful Rename (ADD p.39) — renaming a saved circuit updates
        its name in the list."""
        token = register_and_login(client, "acc_uc12_rename")
        created = client.post("/arsenal", json=_arsenal_payload("Circuit_A"), headers=auth_header(token))
        assert created.status_code == 200, created.text
        assert client.put(
            f"/arsenal/{created.json()['id']}", json={"new_name": "Circuit_B"}, headers=auth_header(token)
        ).status_code == 200
        names = [p["name"] for p in client.get("/arsenal", headers=auth_header(token)).json()]
        assert "Circuit_B" in names and "Circuit_A" not in names


# ══════════════════════════════════════════════════════════════════════════════
# UC13 — Participate in Discussions                                  ADD p.40-41
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc13_successful_discussion_creation : A new discussion shows up and is visible to others.
#   test_uc13_successful_reply_with_voting : You can reply to a discussion and upvote a reply.
#   test_uc13_successful_discussion_locking_by_admin : Once an admin locks a discussion, no one can reply.
#   test_uc13_unsuccessful_user_is_discussion_banned : A banned user can't post discussions or replies.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC13ParticipateInDiscussions:

    def test_uc13_successful_discussion_creation(self, client):
        """UC13 · Successful discussion creation (ADD p.41) — a discussion is
        created, appears in the list and is visible to others."""
        author = register_and_login(client, "acc_uc13_author")
        disc = _create_discussion(client, author, title="ACC UC13 Topic", body="how do I wire an adder?")
        did = int(disc["id"])
        other = register_and_login(client, "acc_uc13_reader")
        listed = client.get("/discussions", headers=auth_header(other))
        assert listed.status_code == 200
        assert did in [int(d["id"]) for d in listed.json()["discussions"]]

    def test_uc13_successful_reply_with_voting(self, client):
        """UC13 · Successful reply with voting (ADD p.41) — a reply is posted and
        upvoted; the vote count updates (one vote per user per reply)."""
        author = register_and_login(client, "acc_uc13_v_author")
        did = int(_create_discussion(client, author, title="ACC UC13 Voting")["id"])
        replier = register_and_login(client, "acc_uc13_v_replier")
        reply = _create_reply(client, replier, did, body="try AND gates")
        assert reply.status_code == 200, reply.text
        rid = int(reply.json()["id"])

        voter = register_and_login(client, "acc_uc13_v_voter")
        vote = client.post(f"/replies/{rid}/vote", json={"value": 1}, headers=auth_header(voter))
        assert vote.status_code == 200, vote.text
        assert vote.json()["user_vote"] == 1

    def test_uc13_successful_discussion_locking_by_admin(self, client, conn):
        """UC13 · Successful discussion locking by admin (ADD p.41) — after an
        admin locks a discussion, new replies are blocked (existing stay)."""
        author = register_and_login(client, "acc_uc13_lock_author")
        did = int(_create_discussion(client, author, title="ACC UC13 Lock")["id"])
        admin_token = make_admin(client, conn, "acc_uc13_admin")
        lock = client.post(f"/discussions/{did}/lock", headers=auth_header(admin_token))
        assert lock.status_code == 200, lock.text
        other = register_and_login(client, "acc_uc13_lock_replier")
        blocked = _create_reply(client, other, did, body="too late")
        assert blocked.status_code == 403
        assert "locked" in blocked.json()["detail"].lower()

    def test_uc13_unsuccessful_user_is_discussion_banned(self, client, conn):
        """UC13 · Unsuccessful user is discussion-banned (ADD p.41) — a banned
        user's create/reply action is rejected; nothing is created."""
        banned = register_and_login(client, "acc_uc13_banned")
        info = get_user_info(client, banned)
        conn.execute("UPDATE users SET is_discussion_banned = 1 WHERE id = ?", (int(info["id"]),))
        resp = client.post(
            "/discussions",
            json={"title": "should fail", "body": "x", "category": "general"},
            headers=auth_header(banned),
        )
        assert resp.status_code == 400
        assert "banned" in resp.json()["detail"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# UC14 — Manage Notifications                                        ADD p.42
# (ADD has no dedicated acceptance table for UC14; these mirror the Functional
#  & Integration "Notification Integration" row, ADD p.103.)
# ──────────────────────────────────────────────────────────────────────────────
# What each test checks:
#   test_uc14_notification_generated_on_solve : When someone solves your puzzle, you get a notification.
#   test_uc14_filter_notifications_by_type : Notifications can be filtered by type.
#   test_uc14_mark_notifications_read : Marking notifications as read empties the unread list.
# ══════════════════════════════════════════════════════════════════════════════
class TestUC14ManageNotifications:

    def test_uc14_notification_generated_on_solve(self, client, conn):
        """UC14 · Notification on solve (ADD p.42 / Integration p.103) — when a
        solver solves a creator's puzzle, a 'solve' notification is generated for
        the creator with the correct type and metadata (actor + puzzle)."""
        creator_token = make_creator(client, conn, "acc_uc14_creator")
        pid, puzzle = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC14 Notify")
        solver_token = register_and_login(client, "acc_uc14_solver")
        assert validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)["solved"] is True

        notes = client.get("/users/me/notifications", headers=auth_header(creator_token))
        assert notes.status_code == 200, notes.text
        solve_notes = [n for n in notes.json() if n["type"] == "solve"]
        assert len(solve_notes) >= 1
        assert solve_notes[0]["actor_username"] == "acc_uc14_solver"
        assert solve_notes[0]["puzzle_name"] == "ACC UC14 Notify"

    def test_uc14_filter_notifications_by_type(self, client, conn):
        """UC14 · Filter by type (ADD p.42) — notifications can be filtered by
        type; an unrelated type returns nothing."""
        creator_token = make_creator(client, conn, "acc_uc14_filter_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC14 Filter")
        solver_token = register_and_login(client, "acc_uc14_filter_solver")
        validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        solve_only = client.get(
            "/users/me/notifications", params={"notif_type": "solve"}, headers=auth_header(creator_token)
        )
        assert solve_only.status_code == 200
        assert all(n["type"] == "solve" for n in solve_only.json())
        assert len(solve_only.json()) >= 1

        none = client.get(
            "/users/me/notifications", params={"notif_type": "role_change"}, headers=auth_header(creator_token)
        )
        assert none.status_code == 200
        assert none.json() == []

    def test_uc14_mark_notifications_read(self, client, conn):
        """UC14 · Mark as read (ADD p.42) — marking notifications read clears the
        unread list."""
        creator_token = make_creator(client, conn, "acc_uc14_read_creator")
        pid, _ = create_and_publish_puzzle(client, conn, creator_token, name="ACC UC14 Read")
        solver_token = register_and_login(client, "acc_uc14_read_solver")
        validate_solution(client, solver_token, pid, _and_solution(), time_taken=10)

        assert len(client.get("/users/me/notifications", headers=auth_header(creator_token)).json()) >= 1
        marked = client.patch("/users/me/notifications/read", headers=auth_header(creator_token))
        assert marked.status_code == 200
        assert marked.json()["marked_read"] >= 1
        assert client.get("/users/me/notifications", headers=auth_header(creator_token)).json() == []
