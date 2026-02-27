"""Integration tests for the Discussion API (/discussions, /replies endpoints)."""
from .conftest import register_and_login, auth_header


def _create_discussion(client, token, title="Test Discussion", body="Body text"):
    resp = client.post("/discussions", json={
        "title": title,
        "body": body,
        "category": "general",
    }, headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestDiscussionCRUD:
    def test_create_discussion(self, client):
        token = register_and_login(client)
        body = _create_discussion(client, token)
        assert "id" in body
        assert body["title"] == "Test Discussion"

    def test_list_discussions(self, client):
        token = register_and_login(client)
        _create_discussion(client, token, "D1")
        _create_discussion(client, token, "D2")

        resp = client.get("/discussions", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()["discussions"]
        assert len(data) == 2

    def test_get_discussion(self, client):
        token = register_and_login(client)
        created = _create_discussion(client, token)
        did = created["id"]

        resp = client.get(f"/discussions/{did}", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test Discussion"

    def test_get_nonexistent_discussion(self, client):
        token = register_and_login(client)
        resp = client.get("/discussions/999", headers=auth_header(token))
        assert resp.status_code == 404

    def test_update_discussion(self, client):
        token = register_and_login(client)
        created = _create_discussion(client, token)
        did = created["id"]

        resp = client.patch(f"/discussions/{did}", json={
            "title": "Updated Title",
        }, headers=auth_header(token))
        assert resp.status_code == 200

        got = client.get(f"/discussions/{did}", headers=auth_header(token))
        assert got.json()["title"] == "Updated Title"

    def test_delete_discussion(self, client):
        token = register_and_login(client)
        created = _create_discussion(client, token)
        did = created["id"]

        resp = client.delete(f"/discussions/{did}", headers=auth_header(token))
        assert resp.status_code == 200

        resp = client.get(f"/discussions/{did}", headers=auth_header(token))
        assert resp.status_code == 404

    def test_view_discussion(self, client):
        token = register_and_login(client)
        created = _create_discussion(client, token)
        did = created["id"]

        resp = client.post(f"/discussions/{did}/view", headers=auth_header(token))
        assert resp.status_code == 200


class TestDiscussionAuth:
    def test_create_no_token(self, client):
        resp = client.post("/discussions", json={
            "title": "T", "body": "B",
        })
        assert resp.status_code == 401

    def test_list_no_token(self, client):
        resp = client.get("/discussions")
        assert resp.status_code == 401

    def test_other_user_cannot_update(self, client):
        token_a = register_and_login(client, "alice")
        token_b = register_and_login(client, "bob")
        created = _create_discussion(client, token_a)
        did = created["id"]

        resp = client.patch(f"/discussions/{did}", json={
            "title": "Hacked",
        }, headers=auth_header(token_b))
        assert resp.status_code == 403

    def test_other_user_cannot_delete(self, client):
        token_a = register_and_login(client, "alice")
        token_b = register_and_login(client, "bob")
        created = _create_discussion(client, token_a)
        did = created["id"]

        resp = client.delete(f"/discussions/{did}", headers=auth_header(token_b))
        assert resp.status_code == 403


class TestReplyCRUD:
    def test_create_reply(self, client):
        token = register_and_login(client)
        disc = _create_discussion(client, token)
        did = disc["id"]

        resp = client.post(f"/discussions/{did}/replies", json={
            "body": "Great post!",
        }, headers=auth_header(token))
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_get_replies(self, client):
        token = register_and_login(client)
        disc = _create_discussion(client, token)
        did = disc["id"]

        client.post(f"/discussions/{did}/replies", json={
            "body": "Reply 1",
        }, headers=auth_header(token))
        client.post(f"/discussions/{did}/replies", json={
            "body": "Reply 2",
        }, headers=auth_header(token))

        resp = client.get(f"/discussions/{did}/replies", headers=auth_header(token))
        assert resp.status_code == 200
        assert len(resp.json()["replies"]) == 2

    def test_nested_reply(self, client):
        token = register_and_login(client)
        disc = _create_discussion(client, token)
        did = disc["id"]

        parent = client.post(f"/discussions/{did}/replies", json={
            "body": "Parent",
        }, headers=auth_header(token)).json()

        child = client.post(f"/discussions/{did}/replies", json={
            "body": "Child reply",
            "parent_reply_id": int(parent["id"]),
        }, headers=auth_header(token))
        assert child.status_code == 200

    def test_update_reply(self, client):
        token = register_and_login(client)
        disc = _create_discussion(client, token)
        did = disc["id"]

        reply = client.post(f"/discussions/{did}/replies", json={
            "body": "Original",
        }, headers=auth_header(token)).json()

        resp = client.patch(f"/replies/{reply['id']}", json={
            "body": "Edited",
        }, headers=auth_header(token))
        assert resp.status_code == 200

    def test_delete_reply(self, client):
        token = register_and_login(client)
        disc = _create_discussion(client, token)
        did = disc["id"]

        reply = client.post(f"/discussions/{did}/replies", json={
            "body": "To delete",
        }, headers=auth_header(token)).json()

        resp = client.delete(f"/replies/{reply['id']}", headers=auth_header(token))
        assert resp.status_code == 200


class TestDiscussionEngagement:
    def test_vote_discussion(self, client):
        token_a = register_and_login(client, "alice")
        token_b = register_and_login(client, "bob")
        disc = _create_discussion(client, token_a)
        did = disc["id"]

        resp = client.post(f"/discussions/{did}/vote", json={
            "value": 1,
        }, headers=auth_header(token_b))
        assert resp.status_code == 200

    def test_vote_reply(self, client):
        token_a = register_and_login(client, "alice")
        token_b = register_and_login(client, "bob")
        disc = _create_discussion(client, token_a)
        did = disc["id"]

        reply = client.post(f"/discussions/{did}/replies", json={
            "body": "Good point",
        }, headers=auth_header(token_a)).json()

        resp = client.post(f"/replies/{reply['id']}/vote", json={
            "value": 1,
        }, headers=auth_header(token_b))
        assert resp.status_code == 200

    def test_bookmark_discussion(self, client):
        token = register_and_login(client)
        disc = _create_discussion(client, token)
        did = disc["id"]

        resp = client.post(f"/discussions/{did}/bookmark", headers=auth_header(token))
        assert resp.status_code == 200

    def test_follow_discussion(self, client):
        token = register_and_login(client)
        disc = _create_discussion(client, token)
        did = disc["id"]

        resp = client.post(f"/discussions/{did}/follow", headers=auth_header(token))
        assert resp.status_code == 200


class TestDiscussionReport:
    def test_report_discussion(self, client):
        token_a = register_and_login(client, "alice")
        token_b = register_and_login(client, "bob")
        disc = _create_discussion(client, token_a)
        did = disc["id"]

        resp = client.post(f"/discussions/{did}/report", json={
            "reason": "spam",
            "details": "Spam content",
        }, headers=auth_header(token_b))
        assert resp.status_code == 200

    def test_report_duplicate_blocked(self, client):
        token_a = register_and_login(client, "alice")
        token_b = register_and_login(client, "bob")
        disc = _create_discussion(client, token_a)
        did = disc["id"]

        client.post(f"/discussions/{did}/report", json={
            "reason": "spam",
        }, headers=auth_header(token_b))

        # Duplicate report
        resp = client.post(f"/discussions/{did}/report", json={
            "reason": "spam",
        }, headers=auth_header(token_b))
        assert resp.status_code == 409
