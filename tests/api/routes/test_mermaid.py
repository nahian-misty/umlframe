from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

VALID_DOCUMENT = {
    "classes": [
        {
            "id": "class_1",
            "name": "User",
            "attributes": [{"name": "email", "datatype": "String", "visibility": "private"}],
            "methods": [],
            "position": {"x": 0, "y": 0},
            "size": {"width": 200, "height": 140},
        }
    ],
    "relationships": [],
}


def test_json_to_mermaid_success():
    resp = client.post("/api/json-to-mermaid", json={"document": VALID_DOCUMENT})
    assert resp.status_code == 200
    diagram = resp.json()["diagram"]
    assert diagram.startswith("classDiagram")
    assert "class User" in diagram
    assert "-String email" in diagram


def test_json_to_mermaid_invalid_document_returns_422():
    bad_document = {**VALID_DOCUMENT, "relationships": [{"id": "rel_1", "source": "class_1", "destination": "class_missing", "type": "association", "multiplicity": {"source": "1", "destination": "1"}}]}
    resp = client.post("/api/json-to-mermaid", json={"document": bad_document})
    assert resp.status_code == 422
