"""Integration tests for the User API (/users endpoints)."""
from Backend import settings

from .conftest import register_user, auth_header, register_and_login


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/users/register", json={
            "username": "alice", "password": "pw123", "email": "alice@test.com"
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body
        assert body["user"]["username"] == "alice"

    def test_register_duplicate_username(self, client):
        register_user(client, "alice")
        resp = client.post("/users/register", json={
            "username": "alice", "password": "pw456", "email": "alice2@test.com"
        })
        assert resp.status_code == 400

    def test_register_empty_username(self, client):
        resp = client.post("/users/register", json={
            "username": "", "password": "pw", "email": "e@test.com"
        })
        assert resp.status_code == 400

    def test_register_empty_password(self, client):
        resp = client.post("/users/register", json={
            "username": "bob", "password": "", "email": "bob@test.com"
        })
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self, client):
        register_user(client, "alice", "pw123")
        resp = client.post("/users/login", json={
            "username": "alice", "password": "pw123"
        })
        assert resp.status_code == 200
        assert "token" in resp.json()

    def test_login_wrong_password(self, client):
        register_user(client, "alice", "pw123")
        resp = client.post("/users/login", json={
            "username": "alice", "password": "wrong"
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/users/login", json={
            "username": "nobody", "password": "pw"
        })
        assert resp.status_code == 401


class TestMe:
    def test_me_success(self, client):
        token = register_and_login(client, "alice")
        resp = client.get("/users/me", headers=auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "alice"

    def test_me_no_token(self, client):
        resp = client.get("/users/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        resp = client.get("/users/me", headers=auth_header("bad-token"))
        assert resp.status_code == 401


class TestLogout:
    def test_logout_success(self, client):
        token = register_and_login(client, "alice")
        resp = client.post("/users/logout", headers=auth_header(token))
        assert resp.status_code == 200

        # Token should now be invalid
        resp = client.get("/users/me", headers=auth_header(token))
        assert resp.status_code == 401

    def test_logout_no_token(self, client):
        resp = client.post("/users/logout")
        assert resp.status_code == 401


class TestListUsers:
    def test_list_users(self, client):
        token = register_and_login(client, "alice")
        register_user(client, "bob")
        resp = client.get("/users", headers=auth_header(token))
        assert resp.status_code == 200
        users = resp.json()["data"]
        usernames = {u["username"] for u in users}
        assert "alice" in usernames
        assert "bob" in usernames

    def test_list_users_no_token(self, client):
        resp = client.get("/users")
        assert resp.status_code == 401

    def test_list_users_experience_level_experienced(self, client, conn):
        token = register_and_login(client, "alice")
        register_user(client, "bob")

        exp_xp_min = ((settings.EXPERIENCED_LEVEL_MIN - 1) ** 2) * settings.LEVEL_XP_DIVISOR
        conn.execute("UPDATE users SET xp=? WHERE username=?", (exp_xp_min, "alice"))
        conn.execute("UPDATE users SET xp=? WHERE username=?", (exp_xp_min - 1, "bob"))

        resp = client.get(
            "/users",
            headers=auth_header(token),
            params={"experience_level": "experienced"},
        )
        assert resp.status_code == 200
        usernames = {u["username"] for u in resp.json()["data"]}
        assert "alice" in usernames
        assert "bob" not in usernames

    def test_list_users_experience_level_inexperienced(self, client, conn):
        token = register_and_login(client, "alice")
        register_user(client, "bob")

        exp_xp_min = ((settings.EXPERIENCED_LEVEL_MIN - 1) ** 2) * settings.LEVEL_XP_DIVISOR
        conn.execute("UPDATE users SET xp=? WHERE username=?", (exp_xp_min, "alice"))
        conn.execute("UPDATE users SET xp=? WHERE username=?", (exp_xp_min - 1, "bob"))

        resp = client.get(
            "/users",
            headers=auth_header(token),
            params={"experience_level": "inexperienced"},
        )
        assert resp.status_code == 200
        usernames = {u["username"] for u in resp.json()["data"]}
        assert "bob" in usernames
        assert "alice" not in usernames

    def test_list_users_order_by_experienced_desc(self, client, conn):
        token = register_and_login(client, "alice")
        register_user(client, "bob")

        exp_xp_min = ((settings.EXPERIENCED_LEVEL_MIN - 1) ** 2) * settings.LEVEL_XP_DIVISOR
        conn.execute("UPDATE users SET xp=? WHERE username=?", (exp_xp_min, "alice"))
        conn.execute("UPDATE users SET xp=? WHERE username=?", (exp_xp_min - 1, "bob"))

        resp = client.get(
            "/users",
            headers=auth_header(token),
            params={"order_by": "experienced", "order_direction": "DESC"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        usernames = [u["username"] for u in data]
        assert usernames.index("alice") < usernames.index("bob")


class TestNotifications:
    def test_get_notifications_empty(self, client):
        token = register_and_login(client, "alice")
        resp = client.get("/users/me/notifications", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_mark_notifications_read(self, client):
        token = register_and_login(client, "alice")
        resp = client.patch("/users/me/notifications/read", headers=auth_header(token))
        assert resp.status_code == 200

    def test_notification_history(self, client):
        token = register_and_login(client, "alice")
        resp = client.get("/users/me/notifications/history", headers=auth_header(token))
        assert resp.status_code == 200


class TestFullAuthFlow:
    def test_register_login_me_logout(self, client):
        """End-to-end auth flow."""
        # Register
        reg = client.post("/users/register", json={
            "username": "alice", "password": "pw123", "email": "alice@test.com"
        })
        assert reg.status_code == 200
        token = reg.json()["token"]

        # Me with register token
        me = client.get("/users/me", headers=auth_header(token))
        assert me.status_code == 200
        assert me.json()["username"] == "alice"

        # Logout
        out = client.post("/users/logout", headers=auth_header(token))
        assert out.status_code == 200

        # Me fails after logout
        me2 = client.get("/users/me", headers=auth_header(token))
        assert me2.status_code == 401

        # Login again
        login = client.post("/users/login", json={
            "username": "alice", "password": "pw123"
        })
        assert login.status_code == 200
        token2 = login.json()["token"]
        assert token2 != token  # new session

        # Me works with new token
        me3 = client.get("/users/me", headers=auth_header(token2))
        assert me3.status_code == 200
