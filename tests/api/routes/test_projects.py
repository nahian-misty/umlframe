VALID_DOCUMENT = {
    "classes": [
        {
            "id": "class_1",
            "name": "User",
            "attributes": [],
            "methods": [],
            "position": {"x": 0, "y": 0},
            "size": {"width": 160, "height": 120},
        }
    ],
    "relationships": [],
}


def _auth_headers(client, email: str) -> dict[str, str]:
    resp = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_get_project(client):
    headers = _auth_headers(client, "alice@example.com")
    create_resp = client.post("/api/projects", json={"name": "My Project"}, headers=headers)
    assert create_resp.status_code == 200
    project_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/projects/{project_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "My Project"


def test_create_project_with_document(client):
    headers = _auth_headers(client, "alice@example.com")
    resp = client.post(
        "/api/projects",
        json={"name": "My Project", "document": VALID_DOCUMENT},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["document"]["classes"][0]["name"] == "User"


def test_list_projects_scoped_to_owner(client):
    alice_headers = _auth_headers(client, "alice@example.com")
    bob_headers = _auth_headers(client, "bob@example.com")
    client.post("/api/projects", json={"name": "Alice Project"}, headers=alice_headers)
    client.post("/api/projects", json={"name": "Bob Project"}, headers=bob_headers)

    resp = client.get("/api/projects", headers=alice_headers)
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()["projects"]]
    assert names == ["Alice Project"]


def test_list_projects_includes_class_geometry_summary(client):
    headers = _auth_headers(client, "alice@example.com")
    client.post(
        "/api/projects",
        json={"name": "Geometry Project", "document": VALID_DOCUMENT},
        headers=headers,
    )

    resp = client.get("/api/projects", headers=headers)
    assert resp.status_code == 200
    summary = resp.json()["projects"][0]
    assert summary["class_count"] == 1
    assert summary["relationship_count"] == 0
    assert summary["class_boxes"] == [{"x": 0, "y": 0, "width": 160, "height": 120}]


def test_list_projects_empty_document_has_zero_geometry(client):
    headers = _auth_headers(client, "alice@example.com")
    client.post("/api/projects", json={"name": "Empty Project"}, headers=headers)

    resp = client.get("/api/projects", headers=headers)
    assert resp.status_code == 200
    summary = resp.json()["projects"][0]
    assert summary["class_count"] == 0
    assert summary["relationship_count"] == 0
    assert summary["class_boxes"] == []


def test_get_project_unauthenticated_returns_401(client):
    resp = client.get("/api/projects/1")
    assert resp.status_code == 401


def test_get_nonexistent_project_returns_404(client):
    headers = _auth_headers(client, "alice@example.com")
    resp = client.get("/api/projects/999999", headers=headers)
    assert resp.status_code == 404


def test_get_other_users_project_returns_404(client):
    alice_headers = _auth_headers(client, "alice@example.com")
    bob_headers = _auth_headers(client, "bob@example.com")
    create_resp = client.post("/api/projects", json={"name": "Alice Project"}, headers=alice_headers)
    project_id = create_resp.json()["id"]

    resp = client.get(f"/api/projects/{project_id}", headers=bob_headers)
    assert resp.status_code == 404


def test_update_project(client):
    headers = _auth_headers(client, "alice@example.com")
    create_resp = client.post("/api/projects", json={"name": "Old Name"}, headers=headers)
    project_id = create_resp.json()["id"]

    resp = client.put(f"/api/projects/{project_id}", json={"name": "New Name"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


def test_update_other_users_project_returns_404(client):
    alice_headers = _auth_headers(client, "alice@example.com")
    bob_headers = _auth_headers(client, "bob@example.com")
    create_resp = client.post("/api/projects", json={"name": "Alice Project"}, headers=alice_headers)
    project_id = create_resp.json()["id"]

    resp = client.put(f"/api/projects/{project_id}", json={"name": "Hacked"}, headers=bob_headers)
    assert resp.status_code == 404


def test_delete_project(client):
    headers = _auth_headers(client, "alice@example.com")
    create_resp = client.post("/api/projects", json={"name": "To Delete"}, headers=headers)
    project_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/projects/{project_id}", headers=headers)
    assert delete_resp.status_code == 200

    get_resp = client.get(f"/api/projects/{project_id}", headers=headers)
    assert get_resp.status_code == 404


def test_delete_other_users_project_returns_404(client):
    alice_headers = _auth_headers(client, "alice@example.com")
    bob_headers = _auth_headers(client, "bob@example.com")
    create_resp = client.post("/api/projects", json={"name": "Alice Project"}, headers=alice_headers)
    project_id = create_resp.json()["id"]

    resp = client.delete(f"/api/projects/{project_id}", headers=bob_headers)
    assert resp.status_code == 404
