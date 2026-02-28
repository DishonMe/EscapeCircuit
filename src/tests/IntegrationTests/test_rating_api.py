"""Integration tests for the Rating API (/ratings endpoints)."""
from .conftest import register_and_login, auth_header


class TestRatingGet:
    def test_get_ratings_no_puzzle(self, client):
        token = register_and_login(client)
        resp = client.get("/ratings/puzzle/999", headers=auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "metrics" in body
        assert "my_rating" in body
        assert body["my_rating"] is None

    def test_get_ratings_no_auth(self, client):
        resp = client.get("/ratings/puzzle/1")
        assert resp.status_code == 401


class TestRatingSubmit:
    def test_submit_rating_no_auth(self, client):
        resp = client.post("/ratings/puzzle/1", json={
            "difficulty": 3, "fun": 4, "clearness": 5,
        })
        assert resp.status_code == 401


class TestRatingDelete:
    def test_delete_nonexistent_rating(self, client):
        token = register_and_login(client)
        resp = client.delete("/ratings/puzzle/999", headers=auth_header(token))
        assert resp.status_code == 404
