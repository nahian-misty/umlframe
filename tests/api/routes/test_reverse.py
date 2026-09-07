from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

VALID_SOURCE = "class User:\n    def __init__(self, email: str) -> None:\n        self.email: str = email\n"
VALID_JAVA_SOURCE = "public class User {\n    private String email;\n}\n"
VALID_JS_SOURCE = "class User {\n    constructor(email) {\n        this.email = email;\n    }\n}\n"


def test_reverse_python_success():
    resp = client.post("/api/reverse", json={"source": VALID_SOURCE, "language": "python"})
    assert resp.status_code == 200
    body = resp.json()
    classes = body["document"]["classes"]
    assert len(classes) == 1
    assert classes[0]["name"] == "User"


def test_reverse_java_success():
    resp = client.post("/api/reverse", json={"source": VALID_JAVA_SOURCE, "language": "java"})
    assert resp.status_code == 200
    classes = resp.json()["document"]["classes"]
    assert len(classes) == 1
    assert classes[0]["name"] == "User"


def test_reverse_javascript_success():
    resp = client.post("/api/reverse", json={"source": VALID_JS_SOURCE, "language": "javascript"})
    assert resp.status_code == 200
    classes = resp.json()["document"]["classes"]
    assert len(classes) == 1
    assert classes[0]["name"] == "User"


def test_reverse_unknown_language_returns_422():
    resp = client.post("/api/reverse", json={"source": VALID_SOURCE, "language": "ruby"})
    assert resp.status_code == 422


def test_reverse_invalid_python_syntax_returns_422():
    resp = client.post("/api/reverse", json={"source": "def foo(:\n    pass\n", "language": "python"})
    assert resp.status_code == 422


def test_reverse_empty_source_returns_422():
    resp = client.post("/api/reverse", json={"source": "   ", "language": "python"})
    assert resp.status_code == 422
