import pytest


def test_register_success(client):
    resp = client.post(
        "/api/auth/register", json={"email": "alice@example.com", "password": "password123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "alice@example.com"
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_register_duplicate_email_returns_409(client):
    client.post("/api/auth/register", json={"email": "alice@example.com", "password": "password123"})
    resp = client.post(
        "/api/auth/register", json={"email": "alice@example.com", "password": "password456"}
    )
    assert resp.status_code == 409


def test_register_weak_password_returns_422(client):
    resp = client.post("/api/auth/register", json={"email": "alice@example.com", "password": "short"})
    assert resp.status_code == 422


def test_register_invalid_email_returns_422(client):
    resp = client.post("/api/auth/register", json={"email": "not-an-email", "password": "password123"})
    assert resp.status_code == 422


def test_login_success(client):
    client.post("/api/auth/register", json={"email": "bob@example.com", "password": "password123"})
    resp = client.post("/api/auth/login", json={"email": "bob@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_wrong_password_returns_401(client):
    client.post("/api/auth/register", json={"email": "bob@example.com", "password": "password123"})
    resp = client.post("/api/auth/login", json={"email": "bob@example.com", "password": "wrong-pw"})
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client):
    resp = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert resp.status_code == 401


def test_me_without_token_returns_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_valid_token_returns_user(client):
    register_resp = client.post(
        "/api/auth/register", json={"email": "carol@example.com", "password": "password123"}
    )
    token = register_resp.json()["access_token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "carol@example.com"


def test_me_with_invalid_token_returns_401(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_logout_returns_200(client):
    register_resp = client.post(
        "/api/auth/register", json={"email": "dave@example.com", "password": "password123"}
    )
    token = register_resp.json()["access_token"]
    resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def _register(client, email="alice@example.com", password="old-password-1") -> dict[str, str]:
    body = client.post("/api/auth/register", json={"email": email, "password": password}).json()
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_change_password_returns_a_working_token_and_switches_the_login_password(client):
    headers = _register(client)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "old-password-1", "new_password": "new-password-2"},
        headers=headers,
    )
    assert resp.status_code == 200
    new_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=new_headers).status_code == 200

    old_login = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "old-password-1"}
    )
    new_login = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "new-password-2"}
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_change_password_wrong_current_password_returns_400(client):
    headers = _register(client)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "nope-nope-nope", "new_password": "new-password-2"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()


def test_change_password_validation_errors_return_422(client):
    headers = _register(client)
    short = client.post(
        "/api/auth/change-password",
        json={"current_password": "old-password-1", "new_password": "short"},
        headers=headers,
    )
    same = client.post(
        "/api/auth/change-password",
        json={"current_password": "old-password-1", "new_password": "old-password-1"},
        headers=headers,
    )
    assert short.status_code == 422
    assert same.status_code == 422


def test_change_password_requires_authentication(client):
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "old-password-1", "new_password": "new-password-2"},
    )
    assert resp.status_code in (401, 403)


def _register_with_username(client, email, username=None):
    body = {"email": email, "password": "password123"}
    if username is not None:
        body["username"] = username
    return client.post("/api/auth/register", json=body)


def test_register_with_username_returns_it_in_token_and_me(client):
    body = _register_with_username(client, "alice@example.com", "alice_w").json()
    assert body["user"]["username"] == "alice_w"
    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    ).json()
    assert me["username"] == "alice_w"


def test_register_without_username_derives_one_from_email(client):
    assert _register_with_username(client, "bob.smith@example.com").json()["user"]["username"] == "bob.smith"
    assert _register_with_username(client, "bob.smith@other.org").json()["user"]["username"] == "bob.smith2"


def test_register_duplicate_username_is_case_insensitive_409(client):
    _register_with_username(client, "a@example.com", "Alice")
    assert _register_with_username(client, "b@example.com", "alice").status_code == 409


@pytest.mark.parametrize("username", ["ab", "x" * 31, "has space", "bad@char"])
def test_register_invalid_username_returns_422(client, username):
    assert _register_with_username(client, "a@example.com", username).status_code == 422

