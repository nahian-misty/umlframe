import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

VALID_DOCUMENT = {
    "classes": [
        {
            "id": "class_1",
            "name": "User",
            "attributes": [
                {
                    "name": "email",
                    "datatype": "String",
                    "visibility": "private",
                    "default_value": None,
                    "static": False,
                    "final": False,
                }
            ],
            "methods": [
                {
                    "name": "login",
                    "visibility": "public",
                    "parameters": [],
                    "return_type": "void",
                    "static": False,
                    "abstract": False,
                }
            ],
            "position": {"x": 0, "y": 0},
            "size": {"width": 160, "height": 120},
        }
    ],
    "relationships": [],
}


# ---------------------------------------------------------------------------
# POST /api/generate-code
# ---------------------------------------------------------------------------


def test_generate_code_python_success():
    resp = client.post(
        "/api/generate-code",
        json={"document": VALID_DOCUMENT, "language": "python"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "files" in body
    assert "User.py" in body["files"]


def test_generate_code_java_success():
    resp = client.post(
        "/api/generate-code",
        json={"document": VALID_DOCUMENT, "language": "java"},
    )
    assert resp.status_code == 200
    assert "User.java" in resp.json()["files"]


def test_generate_code_javascript_success():
    resp = client.post(
        "/api/generate-code",
        json={"document": VALID_DOCUMENT, "language": "javascript"},
    )
    assert resp.status_code == 200
    assert "User.js" in resp.json()["files"]


def test_generate_code_unknown_language_returns_422():
    resp = client.post(
        "/api/generate-code",
        json={"document": VALID_DOCUMENT, "language": "cobol"},
    )
    assert resp.status_code == 422


def test_generate_code_invalid_document_returns_422():
    resp = client.post(
        "/api/generate-code",
        json={"document": {"classes": "not-a-list"}, "language": "python"},
    )
    assert resp.status_code == 422


def test_generate_code_relationship_unknown_source_returns_422():
    bad_doc = {
        "classes": [{"id": "class_1", "name": "A", "attributes": [], "methods": [],
                     "position": {"x": 0, "y": 0}, "size": {"width": 100, "height": 80}}],
        "relationships": [
            {
                "id": "rel_1", "source": "class_99", "destination": "class_1",
                "type": "association",
                "multiplicity": {"source": "1", "destination": "*"},
                "label": "",
            }
        ],
    }
    resp = client.post("/api/generate-code", json={"document": bad_doc, "language": "python"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/languages
# ---------------------------------------------------------------------------


def test_list_languages_returns_supported():
    resp = client.get("/api/languages")
    assert resp.status_code == 200
    langs = resp.json()["languages"]
    assert "python" in langs
    assert "java" in langs
    assert "javascript" in langs


# ---------------------------------------------------------------------------
# GET /api/templates
# ---------------------------------------------------------------------------


def test_list_templates_returns_dict():
    resp = client.get("/api/templates")
    assert resp.status_code == 200
    templates = resp.json()["templates"]
    assert isinstance(templates, dict)
    for lang in ("python", "java", "javascript"):
        assert lang in templates
        assert "class.j2" in templates[lang]
