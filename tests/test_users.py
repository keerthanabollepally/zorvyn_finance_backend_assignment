def test_signup_login_me(client):
    r = client.post(
        "/users/signup",
        json={"email": "u1@example.com", "password": "password123", "name": "One"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "u1@example.com"
    assert body["role"] == "viewer"

    r = client.post("/users/login", json={"email": "u1@example.com", "password": "password123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["name"] == "One"


def test_signup_rejects_elevated_role(client):
    r = client.post(
        "/users/signup",
        json={
            "email": "bad@example.com",
            "password": "password123",
            "name": "Bad",
            "role": "admin",
        },
    )
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_role_signup"


def test_admin_list_users(client, admin_headers):
    client.post(
        "/users/signup",
        json={"email": "v@example.com", "password": "password123", "name": "V"},
    )
    r = client.get("/users", headers=admin_headers)
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert "admin@test.com" in emails


def test_viewer_cannot_list_users(client, viewer_headers):
    r = client.get("/users", headers=viewer_headers)
    assert r.status_code == 403
