import base64

from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size

client = TestClient(app)

_POS, _SIZE = Position(x=0, y=0), Size(width=160, height=80)


def test_activity_json_to_image_success():
    doc = ActivityDocument(
        nodes=[
            ActivityNode(id="n1", type=ActivityNodeType.START, position=_POS, size=_SIZE),
            ActivityNode(id="n2", type=ActivityNodeType.END, position=_POS, size=_SIZE),
        ],
        edges=[ActivityEdge(id="e1", source="n1", target="n2")],
    )
    resp = client.post("/api/activity-json-to-image", json={"activity": doc.model_dump(mode="json")})
    assert resp.status_code == 200
    png_bytes = base64.b64decode(resp.json()["image_base64"])
    assert png_bytes.startswith(b"\x89PNG")


def test_activity_json_to_image_rejects_unsupported_shape():
    # A fork node: structuring explicitly rejects fork/join (Milestone 9
    # scope), so this must surface as a 422, not a 500 or silently-wrong image.
    doc = ActivityDocument(
        nodes=[
            ActivityNode(id="n1", type=ActivityNodeType.START, position=_POS, size=_SIZE),
            ActivityNode(id="n2", type=ActivityNodeType.FORK, position=_POS, size=_SIZE),
            ActivityNode(id="n3", type=ActivityNodeType.END, position=_POS, size=_SIZE),
        ],
        edges=[
            ActivityEdge(id="e1", source="n1", target="n2"),
            ActivityEdge(id="e2", source="n2", target="n3"),
        ],
    )
    resp = client.post("/api/activity-json-to-image", json={"activity": doc.model_dump(mode="json")})
    assert resp.status_code == 422


def test_activity_json_to_image_requires_activity_field():
    resp = client.post("/api/activity-json-to-image", json={})
    assert resp.status_code == 422
