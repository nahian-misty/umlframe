from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

_POS_SIZE = {"position": {"x": 0, "y": 0}, "size": {"width": 160, "height": 80}}

VALID_ACTIVITY = {
    "nodes": [
        {"id": "n1", "type": "start", **_POS_SIZE},
        {"id": "n2", "type": "decision", "label": "x > 0", **_POS_SIZE},
        {"id": "n3", "type": "action", "label": "do positive", **_POS_SIZE},
        {"id": "n4", "type": "action", "label": "do negative", **_POS_SIZE},
        {"id": "n5", "type": "end", **_POS_SIZE},
    ],
    "edges": [
        {"id": "e1", "source": "n1", "target": "n2"},
        {"id": "e2", "source": "n2", "target": "n3", "label": "yes"},
        {"id": "e3", "source": "n2", "target": "n4", "label": "no"},
        {"id": "e4", "source": "n3", "target": "n5"},
        {"id": "e5", "source": "n4", "target": "n5"},
    ],
}


def test_generate_activity_code_python_success():
    resp = client.post(
        "/api/generate-activity-code",
        json={"document": VALID_ACTIVITY, "language": "python", "function_name": "classify"},
    )
    assert resp.status_code == 200
    files = resp.json()["files"]
    assert "classify.py" in files
    assert "if True:  # x > 0" in files["classify.py"]


def test_generate_activity_code_default_function_name():
    resp = client.post("/api/generate-activity-code", json={"document": VALID_ACTIVITY, "language": "java"})
    assert resp.status_code == 200
    assert "generated_function.java" in resp.json()["files"]


def test_generate_activity_code_unsupported_language_returns_422():
    resp = client.post(
        "/api/generate-activity-code",
        json={"document": VALID_ACTIVITY, "language": "ruby", "function_name": "classify"},
    )
    assert resp.status_code == 422


def test_generate_activity_code_unsupported_shape_returns_422():
    fork_doc = {
        "nodes": [
            {"id": "n1", "type": "start", **_POS_SIZE},
            {"id": "n2", "type": "fork", **_POS_SIZE},
            {"id": "n3", "type": "end", **_POS_SIZE},
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}, {"id": "e2", "source": "n2", "target": "n3"}],
    }
    resp = client.post(
        "/api/generate-activity-code",
        json={"document": fork_doc, "language": "python", "function_name": "bad"},
    )
    assert resp.status_code == 422


def test_generate_activity_code_invalid_document_returns_422():
    bad_doc = {**VALID_ACTIVITY, "nodes": [n for n in VALID_ACTIVITY["nodes"] if n["type"] != "start"]}
    resp = client.post(
        "/api/generate-activity-code",
        json={"document": bad_doc, "language": "python", "function_name": "bad"},
    )
    assert resp.status_code == 422
