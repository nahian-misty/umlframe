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
