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


ACTIVITY_DOCUMENT = {
    "nodes": [
        {
            "id": "node_1",
            "type": "start",
            "label": "",
            "position": {"x": 0, "y": 0},
            "size": {"width": 40, "height": 40},
        },
        {
            "id": "node_2",
            "type": "end",
            "label": "",
            "position": {"x": 0, "y": 100},
            "size": {"width": 40, "height": 40},
        },
    ],
    "edges": [{"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""}],
}


def test_project_activity_document_defaults_to_null(client):
    headers = _auth_headers(client, "alice@example.com")
    project_id = client.post("/api/projects", json={"name": "P"}, headers=headers).json()["id"]
    resp = client.get(f"/api/projects/{project_id}", headers=headers)
    assert resp.json()["activity_document"] is None


def test_project_activity_document_saved_and_loaded(client):
    headers = _auth_headers(client, "alice@example.com")
    project_id = client.post("/api/projects", json={"name": "P"}, headers=headers).json()["id"]
    put_resp = client.put(
        f"/api/projects/{project_id}",
        json={"activity_document": ACTIVITY_DOCUMENT},
        headers=headers,
    )
    assert put_resp.status_code == 200
    resp = client.get(f"/api/projects/{project_id}", headers=headers)
    assert resp.json()["activity_document"] == ACTIVITY_DOCUMENT


def test_project_invalid_activity_document_returns_422(client):
    headers = _auth_headers(client, "alice@example.com")
    project_id = client.post("/api/projects", json={"name": "P"}, headers=headers).json()["id"]
    bad = {"nodes": [], "edges": []}
    resp = client.put(
        f"/api/projects/{project_id}", json={"activity_document": bad}, headers=headers
    )
    assert resp.status_code == 422


def _create(client, headers, name: str) -> None:
    assert client.post("/api/projects", json={"name": name}, headers=headers).status_code == 200


def test_list_projects_search_and_pagination(client):
    headers = _auth_headers(client, "alice@example.com")
    for name in ["Alpha", "Beta", "Gamma", "alphabet"]:
        _create(client, headers, name)

    searched = client.get("/api/projects?search=alpha&sort=name", headers=headers).json()
    assert [p["name"] for p in searched["projects"]] == ["Alpha", "alphabet"]
    assert searched["total"] == 2

    page = client.get("/api/projects?sort=name&limit=3&offset=3", headers=headers).json()
    assert [p["name"] for p in page["projects"]] == ["Gamma"]
    assert (page["total"], page["limit"], page["offset"]) == (4, 3, 3)


def test_list_projects_rejects_bad_paging_params(client):
    headers = _auth_headers(client, "alice@example.com")
    assert client.get("/api/projects?limit=0", headers=headers).status_code == 422
    assert client.get("/api/projects?offset=-1", headers=headers).status_code == 422
    assert client.get("/api/projects?sort=bogus", headers=headers).status_code == 422


def test_rename_project_persists_and_trims(client):
    headers = _auth_headers(client, "alice@example.com")
    project_id = client.post("/api/projects", json={"name": "Old"}, headers=headers).json()["id"]
    resp = client.put(f"/api/projects/{project_id}", json={"name": "  New  "}, headers=headers)
    assert resp.status_code == 200
    assert client.get(f"/api/projects/{project_id}", headers=headers).json()["name"] == "New"


def test_blank_project_name_returns_422(client):
    headers = _auth_headers(client, "alice@example.com")
    project_id = client.post("/api/projects", json={"name": "Old"}, headers=headers).json()["id"]
    assert client.put(f"/api/projects/{project_id}", json={"name": "  "}, headers=headers).status_code == 422
    assert client.post("/api/projects", json={"name": ""}, headers=headers).status_code == 422


def test_project_code_inputs_default_saved_and_kept_across_renames(client):
    headers = _auth_headers(client, "alice@example.com")
    project_id = client.post("/api/projects", json={"name": "P"}, headers=headers).json()["id"]
    default = client.get(f"/api/projects/{project_id}", headers=headers).json()["code_inputs"]
    assert default["code_to_uml"] == {"language": "python", "source": ""}

    inputs = {
        "code_to_uml": {"language": "java", "source": "class A {}"},
        "code_to_activity": {
            "language": "python",
            "class_name": "A",
            "method_name": "run",
            "source": "class A:\n    def run(self): pass",
        },
    }
    client.put(f"/api/projects/{project_id}", json={"code_inputs": inputs}, headers=headers)
    client.put(f"/api/projects/{project_id}", json={"name": "Renamed"}, headers=headers)
    loaded = client.get(f"/api/projects/{project_id}", headers=headers).json()
    assert loaded["code_inputs"] == inputs


def test_project_type_defaults_to_uml_and_is_returned(client):
    headers = _auth_headers(client, "alice@example.com")
    created = client.post("/api/projects", json={"name": "P"}, headers=headers).json()
    assert created["project_type"] == "uml"


def test_list_projects_filters_by_project_type(client):
    headers = _auth_headers(client, "alice@example.com")
    _create(client, headers, "Classes")
    client.post("/api/projects", json={"name": "Flow", "project_type": "activity"}, headers=headers)

    activity = client.get("/api/projects?project_type=activity", headers=headers).json()
    assert [(p["name"], p["project_type"]) for p in activity["projects"]] == [("Flow", "activity")]
    assert activity["total"] == 1
    uml = client.get("/api/projects?project_type=uml", headers=headers).json()
    assert [p["name"] for p in uml["projects"]] == ["Classes"]


def test_invalid_project_type_returns_422(client):
    headers = _auth_headers(client, "alice@example.com")
    bad = client.post("/api/projects", json={"name": "P", "project_type": "bogus"}, headers=headers)
    assert bad.status_code == 422
    assert client.get("/api/projects?project_type=bogus", headers=headers).status_code == 422


def test_activity_project_thumbnail_uses_activity_nodes(client):
    headers = _auth_headers(client, "alice@example.com")
    activity = {
        "nodes": [
            {"id": "n1", "type": "start", "label": "", "position": {"x": 5, "y": 6}, "size": {"width": 30, "height": 30}},
            {"id": "n2", "type": "end", "label": "", "position": {"x": 5, "y": 90}, "size": {"width": 30, "height": 30}},
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2", "label": ""}],
    }
    client.post(
        "/api/projects",
        json={"name": "Flow", "project_type": "activity", "activity_document": activity},
        headers=headers,
    )
    summary = client.get("/api/projects", headers=headers).json()["projects"][0]
    assert summary["node_count"] == 2
    assert summary["class_boxes"][0] == {"x": 5, "y": 6, "width": 30, "height": 30}
