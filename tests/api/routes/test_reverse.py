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


# ---------------------------------------------------------------------------
# Control-flow extraction (Milestone 6): opted into by also passing
# class_name/method_name, and returned alongside the class structure.
# ---------------------------------------------------------------------------

_CONTROL_FLOW_SOURCE = (
    "class User:\n"
    "    def classify(self, x: int) -> str:\n"
    "        if x > 0:\n"
    "            return 'positive'\n"
    "        return 'non-positive'\n"
)


def test_reverse_without_class_or_method_name_omits_control_flow():
    resp = client.post("/api/reverse", json={"source": VALID_SOURCE, "language": "python"})
    assert resp.status_code == 200
    assert resp.json()["control_flow"] is None


def test_reverse_with_class_and_method_name_includes_control_flow():
    resp = client.post(
        "/api/reverse",
        json={
            "source": _CONTROL_FLOW_SOURCE,
            "language": "python",
            "class_name": "User",
            "method_name": "classify",
        },
    )
    assert resp.status_code == 200
    control_flow = resp.json()["control_flow"]
    assert control_flow is not None
    node_types = {n["type"] for n in control_flow["nodes"]}
    assert node_types == {"start", "end", "decision", "action"}


def test_reverse_unknown_class_name_returns_422():
    resp = client.post(
        "/api/reverse",
        json={
            "source": _CONTROL_FLOW_SOURCE,
            "language": "python",
            "class_name": "Nope",
            "method_name": "classify",
        },
    )
    assert resp.status_code == 422


def test_reverse_unknown_method_name_returns_422():
    resp = client.post(
        "/api/reverse",
        json={
            "source": _CONTROL_FLOW_SOURCE,
            "language": "python",
            "class_name": "User",
            "method_name": "nope",
        },
    )
    assert resp.status_code == 422
