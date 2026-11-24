from app.tests.conftest import auth


def test_register_login_refresh_and_me(client, register):
    created = register(client)
    me = client.get("/api/auth/me", headers=auth(created["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"
    assert me.json()["role"] == "customer"

    refreshed = client.post("/api/auth/refresh", json={"refresh_token": created["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"] != created["access_token"]
    old = client.post("/api/auth/refresh", json={"refresh_token": created["refresh_token"]})
    assert old.status_code == 401


def test_demo_test_domain_can_register(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "guest@atelier.test", "password": "password123", "full_name": "Guest Shopper"},
    )
    assert response.status_code == 201, response.text
    login = client.post("/api/auth/login", json={"email": "guest@atelier.test", "password": "password123"})
    assert login.status_code == 200


def test_login_rejects_bad_password(client, register):
    register(client)
    response = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_forgot_and_reset_password(client, register):
    register(client)
    forgot = client.post("/api/auth/forgot-password", json={"email": "ada@example.com"})
    assert forgot.status_code == 200
    token = forgot.json()["reset_token"]
    reset = client.post("/api/auth/reset-password", json={"token": token, "password": "newpassword123"})
    assert reset.status_code == 200
    login = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "newpassword123"})
    assert login.status_code == 200


def test_customer_cannot_open_admin(client, register):
    created = register(client)
    response = client.get("/api/admin/stats", headers=auth(created["access_token"]))
    assert response.status_code == 403


def test_admin_stats_require_auth(client):
    assert client.get("/api/admin/stats").status_code == 401
