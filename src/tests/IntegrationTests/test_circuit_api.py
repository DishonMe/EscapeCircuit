"""Integration tests for the Circuit API (/circuits endpoints)."""
import json
from .conftest import register_and_login, auth_header


def _circuit_json():
    return json.dumps({"placedComponents": [], "wires": []})


class TestCircuitCRUD:
    def test_save_circuit(self, client):
        token = register_and_login(client)
        resp = client.post("/circuits", json={
            "name": "My Circuit",
            "cost": 5,
            "structure_json": _circuit_json(),
        }, headers=auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "My Circuit"
        assert "id" in body

    def test_list_circuits_empty(self, client):
        token = register_and_login(client)
        resp = client.get("/circuits", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_circuits(self, client):
        token = register_and_login(client)
        client.post("/circuits", json={
            "name": "C1", "structure_json": _circuit_json(),
        }, headers=auth_header(token))
        client.post("/circuits", json={
            "name": "C2", "structure_json": _circuit_json(),
        }, headers=auth_header(token))

        resp = client.get("/circuits", headers=auth_header(token))
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_circuit(self, client):
        token = register_and_login(client)
        created = client.post("/circuits", json={
            "name": "My Circuit", "structure_json": _circuit_json(),
        }, headers=auth_header(token)).json()

        resp = client.get(f"/circuits/{created['id']}", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["name"] == "My Circuit"

    def test_delete_circuit(self, client):
        token = register_and_login(client)
        created = client.post("/circuits", json={
            "name": "ToDelete", "structure_json": _circuit_json(),
        }, headers=auth_header(token)).json()

        resp = client.delete(f"/circuits/{created['id']}", headers=auth_header(token))
        assert resp.status_code == 200

        # Should be gone
        resp = client.get("/circuits", headers=auth_header(token))
        assert len(resp.json()) == 0


class TestCircuitAuth:
    def test_no_token(self, client):
        resp = client.get("/circuits")
        assert resp.status_code == 401

    def test_invalid_token(self, client):
        resp = client.get("/circuits", headers=auth_header("bad"))
        assert resp.status_code == 401

    def test_user_isolation(self, client):
        """Users cannot see each other's circuits."""
        token_a = register_and_login(client, "alice")
        token_b = register_and_login(client, "bob")

        client.post("/circuits", json={
            "name": "Alice's Circuit", "structure_json": _circuit_json(),
        }, headers=auth_header(token_a))

        # Bob should see no circuits
        resp = client.get("/circuits", headers=auth_header(token_b))
        assert resp.status_code == 200
        assert len(resp.json()) == 0
