"""
System tests: Discussion forum workflow.

Workflow: user creates discussion → others reply → nested replies →
votes (up/down) → accept answer → XP awarded for each action →
report content.
"""
from .conftest import (
    auth_header, register_and_login, get_user_xp,
)


def _create_discussion(client, token, title="Test Discussion",
                       body="Discussion body", category="general"):
    resp = client.post("/discussions", json={
        "title": title,
        "body": body,
        "category": category,
    }, headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_reply(client, token, discussion_id, body="Reply body",
                  parent_reply_id=None):
    payload = {"body": body}
    if parent_reply_id is not None:
        payload["parent_reply_id"] = parent_reply_id
    resp = client.post(f"/discussions/{discussion_id}/replies", json=payload,
                       headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestDiscussionLifecycle:
    """Full lifecycle: create → reply → nested reply → view."""

    def test_create_reply_and_nested(self, client):
        # Author creates discussion
        author_token = register_and_login(client, "disc_author")
        disc = _create_discussion(client, author_token, title="Help needed")
        did = int(disc["id"])

        # Replier answers
        replier_token = register_and_login(client, "replier")
        reply = _create_reply(client, replier_token, did,
                              body="Try using AND gates")
        rid = int(reply["id"])

        # Author adds nested reply
        nested = _create_reply(client, author_token, did,
                               body="Thanks, that worked!", parent_reply_id=rid)
        assert nested["parent_reply_id"] == rid

        # View discussion → reply_count should be 2
        resp = client.get(f"/discussions/{did}",
                          headers=auth_header(author_token))
        assert resp.status_code == 200
        assert resp.json()["reply_count"] >= 2

        # List replies
        resp = client.get(f"/discussions/{did}/replies",
                          headers=auth_header(author_token))
        assert resp.status_code == 200
        replies = resp.json()["replies"]
        assert len(replies) >= 2


class TestVotingWorkflow:
    """Vote on discussions and replies."""

    def test_upvote_discussion(self, client):
        author_token = register_and_login(client, "vote_author")
        disc = _create_discussion(client, author_token, title="Upvote me")
        did = int(disc["id"])

        voter_token = register_and_login(client, "voter1")
        resp = client.post(f"/discussions/{did}/vote", json={"value": 1},
                           headers=auth_header(voter_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_vote"] == 1
        assert body["upvotes"] >= 1

    def test_upvote_reply(self, client):
        author_token = register_and_login(client, "reply_vote_auth")
        disc = _create_discussion(client, author_token)
        did = int(disc["id"])

        replier_token = register_and_login(client, "rv_replier")
        reply = _create_reply(client, replier_token, did, body="Good answer")
        rid = int(reply["id"])

        voter_token = register_and_login(client, "rv_voter")
        resp = client.post(f"/replies/{rid}/vote", json={"value": 1},
                           headers=auth_header(voter_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_vote"] == 1

    def test_downvote_reply(self, client):
        author_token = register_and_login(client, "dv_author")
        disc = _create_discussion(client, author_token)
        did = int(disc["id"])

        replier_token = register_and_login(client, "dv_replier")
        reply = _create_reply(client, replier_token, did, body="Bad answer")
        rid = int(reply["id"])

        voter_token = register_and_login(client, "dv_voter")
        resp = client.post(f"/replies/{rid}/vote", json={"value": -1},
                           headers=auth_header(voter_token))
        assert resp.status_code == 200
        assert resp.json()["user_vote"] == -1


class TestAcceptAnswer:
    """Discussion author accepts a reply → XP awarded."""

    def test_accept_reply(self, client):
        author_token = register_and_login(client, "accept_author")
        disc = _create_discussion(client, author_token, title="Accept test")
        did = int(disc["id"])

        replier_token = register_and_login(client, "accept_replier")
        replier_xp_before = get_user_xp(client, replier_token)

        reply = _create_reply(client, replier_token, did, body="The solution")
        rid = int(reply["id"])

        # Author accepts the reply
        resp = client.post(f"/replies/{rid}/accept",
                           headers=auth_header(author_token))
        assert resp.status_code == 200
        assert resp.json()["is_accepted"] is True

        # Discussion now has accepted_reply_id
        resp = client.get(f"/discussions/{did}",
                          headers=auth_header(author_token))
        assert resp.json()["accepted_reply_id"] == rid

        # Replier earned XP for accepted answer
        replier_xp_after = get_user_xp(client, replier_token)
        assert replier_xp_after > replier_xp_before

    def test_accept_replaces_previous(self, client):
        """Accepting a new reply un-accepts the previous one."""
        author_token = register_and_login(client, "replace_author")
        disc = _create_discussion(client, author_token)
        did = int(disc["id"])

        r1_token = register_and_login(client, "r1_replier")
        reply1 = _create_reply(client, r1_token, did, body="Answer 1")
        rid1 = int(reply1["id"])

        r2_token = register_and_login(client, "r2_replier")
        reply2 = _create_reply(client, r2_token, did, body="Better answer")
        rid2 = int(reply2["id"])

        # Accept first
        client.post(f"/replies/{rid1}/accept",
                    headers=auth_header(author_token))

        # Accept second → replaces first
        resp = client.post(f"/replies/{rid2}/accept",
                           headers=auth_header(author_token))
        assert resp.status_code == 200

        # Discussion points to second
        resp = client.get(f"/discussions/{did}",
                          headers=auth_header(author_token))
        assert resp.json()["accepted_reply_id"] == rid2


class TestForumXP:
    """XP is awarded for creating discussions and replies."""

    def test_xp_for_discussion_create(self, client):
        token = register_and_login(client, "xp_disc_user")
        xp_before = get_user_xp(client, token)

        _create_discussion(client, token, title="XP test discussion")

        xp_after = get_user_xp(client, token)
        assert xp_after > xp_before

    def test_xp_for_reply_create(self, client):
        author_token = register_and_login(client, "xp_reply_author")
        disc = _create_discussion(client, author_token)
        did = int(disc["id"])

        replier_token = register_and_login(client, "xp_replier")
        xp_before = get_user_xp(client, replier_token)

        _create_reply(client, replier_token, did, body="Earning XP")

        xp_after = get_user_xp(client, replier_token)
        assert xp_after > xp_before


class TestReportContent:
    """Users can report discussions."""

    def test_report_and_prevent_duplicate(self, client):
        author_token = register_and_login(client, "report_author")
        disc = _create_discussion(client, author_token, title="Bad content")
        did = int(disc["id"])

        reporter_token = register_and_login(client, "reporter")

        # First report succeeds
        resp = client.post(f"/discussions/{did}/report", json={
            "reason": "spam",
        }, headers=auth_header(reporter_token))
        assert resp.status_code == 200

        # Duplicate report blocked
        resp = client.post(f"/discussions/{did}/report", json={
            "reason": "spam",
        }, headers=auth_header(reporter_token))
        assert resp.status_code == 409
