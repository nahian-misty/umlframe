import io

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from backend.main import app

client = TestClient(app)


def _png(draw_fn, size=(400, 500)) -> bytes:
    img = Image.new("RGB", size, "white")
    draw_fn(ImageDraw.Draw(img))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _start_end_png() -> bytes:
    def draw(d):
        d.ellipse([184, 30, 216, 62], fill="black")  # start
        d.ellipse([180, 320, 220, 360], outline="black", width=3)  # end
        d.line([200, 66, 200, 316], fill="black", width=2)

    return _png(draw)


def _two_end_no_start_png() -> bytes:
    def draw(d):
        d.ellipse([80, 60, 120, 100], outline="black", width=3)
        d.ellipse([260, 60, 300, 100], outline="black", width=3)
        d.line([120, 80, 260, 80], fill="black", width=2)

    return _png(draw)


def test_activity_image_to_json_success():
    resp = client.post(
        "/api/activity-image-to-json",
        files={"file": ("diagram.png", _start_end_png(), "image/png")},
    )
    assert resp.status_code == 200
    document = resp.json()["document"]
    types = sorted(n["type"] for n in document["nodes"])
    assert types == ["end", "start"]
    assert len(document["edges"]) == 1


def test_activity_image_to_json_rejects_non_image():
    resp = client.post(
        "/api/activity-image-to-json",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 422


def test_activity_image_to_json_rejects_empty_file():
    resp = client.post(
        "/api/activity-image-to-json",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert resp.status_code == 422


def test_activity_image_to_json_invalid_graph_returns_422():
    resp = client.post(
        "/api/activity-image-to-json",
        files={"file": ("diagram.png", _two_end_no_start_png(), "image/png")},
    )
    assert resp.status_code == 422
