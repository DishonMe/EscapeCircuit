"""
System tests: Draft save/resume workflow.

Workflow: creator saves draft → leaves → comes back → resumes draft →
overwrites → optimistic concurrency conflict detected → delete draft.
"""
from .conftest import (
    auth_header, make_creator, create_puzzle,
)


class TestDraftSaveResume:
    """Creator saves work-in-progress and resumes later."""

    def test_save_and_resume_draft(self, client, conn):
        creator_token = make_creator(client, conn, "draft_creator")
        puzzle = create_puzzle(client, creator_token, name="Draft Puzzle")
        pid = int(puzzle["id"])

        # Save draft
        resp = client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"step": 1, "gates_placed": 3}',
        }, headers=auth_header(creator_token))
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        ts1 = resp.json()["updated_at"]

        # "Leave" and come back — get draft
        resp = client.get(f"/puzzles/{pid}/draft",
                          headers=auth_header(creator_token))
        assert resp.status_code == 200
        assert '"step": 1' in resp.json()["state_json"]

        # Continue working — overwrite draft
        resp = client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"step": 2, "gates_placed": 7}',
        }, headers=auth_header(creator_token))
        assert resp.status_code == 200
        ts2 = resp.json()["updated_at"]
        assert ts2 != ts1  # timestamp updated

        # Get latest draft
        resp = client.get(f"/puzzles/{pid}/draft",
                          headers=auth_header(creator_token))
        assert resp.json()["state_json"] == '{"step": 2, "gates_placed": 7}'


class TestDraftOptimisticConcurrency:
    """Optimistic concurrency prevents stale overwrites."""

    def test_stale_write_detected(self, client, conn):
        creator_token = make_creator(client, conn, "occ_creator")
        puzzle = create_puzzle(client, creator_token)
        pid = int(puzzle["id"])

        # Initial save
        r1 = client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"v": 1}',
        }, headers=auth_header(creator_token)).json()
        ts1 = r1["updated_at"]

        # Second save with correct timestamp → succeeds
        r2 = client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"v": 2}',
            "expected_updated_at": ts1,
        }, headers=auth_header(creator_token))
        assert r2.status_code == 200
        ts2 = r2.json()["updated_at"]

        # Third save with STALE timestamp → conflict
        r3 = client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"v": 3}',
            "expected_updated_at": ts1,  # stale
        }, headers=auth_header(creator_token))
        assert r3.status_code == 409

        # Latest data is still v2
        resp = client.get(f"/puzzles/{pid}/draft",
                          headers=auth_header(creator_token))
        assert resp.json()["state_json"] == '{"v": 2}'


class TestDraftCleanup:
    """Creator can delete a draft when done."""

    def test_delete_draft_after_done(self, client, conn):
        creator_token = make_creator(client, conn, "cleanup_creator")
        puzzle = create_puzzle(client, creator_token)
        pid = int(puzzle["id"])

        # Save draft
        client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"wip": true}',
        }, headers=auth_header(creator_token))

        # Delete draft
        resp = client.delete(f"/puzzles/{pid}/draft",
                             headers=auth_header(creator_token))
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Draft is gone
        resp = client.get(f"/puzzles/{pid}/draft",
                          headers=auth_header(creator_token))
        assert resp.json()["state_json"] is None

    def test_draft_survives_puzzle_update(self, client, conn):
        """Draft persists even when puzzle metadata is updated."""
        creator_token = make_creator(client, conn, "persist_creator")
        puzzle = create_puzzle(client, creator_token, name="Draft Persist")
        pid = int(puzzle["id"])

        # Save draft
        client.put(f"/puzzles/{pid}/draft", json={
            "state_json": '{"work": "in_progress"}',
        }, headers=auth_header(creator_token))

        # Update puzzle metadata
        client.patch(f"/puzzles/{pid}", json={
            "description": "Updated description",
        }, headers=auth_header(creator_token))

        # Draft still intact
        resp = client.get(f"/puzzles/{pid}/draft",
                          headers=auth_header(creator_token))
        assert resp.json()["state_json"] == '{"work": "in_progress"}'
