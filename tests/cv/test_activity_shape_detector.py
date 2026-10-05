"""Activity-diagram CV tests using programmatically generated images."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw

from backend.cv.activity_shape_detector import (
    detect_activity_connectors,
    detect_activity_shapes,
)
from backend.cv.preprocessor import preprocess


def _img_bytes(draw_fn, size=(400, 500)) -> bytes:
    img = Image.new("RGB", size, "white")
    draw_fn(ImageDraw.Draw(img))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _binary(draw_fn, size=(400, 500)):
    _, _, binary = preprocess(_img_bytes(draw_fn, size))
    return binary


def _kinds(draw_fn) -> list[str]:
    return [s.kind for s in detect_activity_shapes(_binary(draw_fn))]


# ---------------------------------------------------------------------------
# Shape classification
# ---------------------------------------------------------------------------


def test_filled_circle_is_start():
    assert "start" in _kinds(lambda d: d.ellipse([40, 40, 90, 90], fill="black"))


def test_outlined_circle_is_end():
    assert "end" in _kinds(lambda d: d.ellipse([40, 40, 110, 110], outline="black", width=3))


def test_rounded_rectangle_is_action():
    def draw(d):
        d.rounded_rectangle([50, 70, 330, 150], radius=10, outline="black", width=3)

    assert _kinds(draw) == ["action"]


def test_diamond_is_decision():
    def draw(d):
        d.polygon([(200, 60), (320, 150), (200, 240), (80, 150)], outline="black", width=3)

    assert _kinds(draw) == ["decision"]


def test_wide_bar_is_bar():
    assert _kinds(lambda d: d.rectangle([60, 100, 340, 116], fill="black")) == ["bar"]


# ---------------------------------------------------------------------------
# Connector detection
# ---------------------------------------------------------------------------


def _straight_pipeline(d) -> None:
    # A few px of clearance between each line and the shapes it joins, as a
    # clean render has -- keeps every shape and line its own contour/component.
    d.ellipse([180, 30, 220, 70], fill="black")  # start
    d.rounded_rectangle([90, 155, 310, 225], radius=10, outline="black", width=3)  # action
    d.ellipse([180, 325, 224, 369], outline="black", width=3)  # end
    d.line([200, 74, 200, 151], fill="black", width=3)  # start -> action
    d.line([200, 229, 200, 321], fill="black", width=3)  # action -> end


def test_detects_all_pipeline_shapes():
    assert sorted(_kinds(_straight_pipeline)) == ["action", "end", "start"]


def test_detects_two_connectors_between_three_shapes():
    binary = _binary(_straight_pipeline)
    shapes = detect_activity_shapes(binary)
    connectors = detect_activity_connectors(binary, shapes)
    assert len(connectors) == 2


def test_no_connectors_when_no_lines():
    def draw(d):
        d.ellipse([180, 30, 220, 70], fill="black")
        d.ellipse([180, 320, 224, 364], outline="black", width=3)

    binary = _binary(draw)
    shapes = detect_activity_shapes(binary)
    assert detect_activity_connectors(binary, shapes) == []


# ---------------------------------------------------------------------------
# Real diagrams: lines touch their shapes (no clean-render gap)
# ---------------------------------------------------------------------------


def _touching_pipeline(d) -> None:
    d.ellipse([180, 30, 220, 70], fill="black")  # start
    d.rounded_rectangle([90, 155, 310, 225], radius=10, outline="black", width=3)  # action
    d.ellipse([180, 325, 224, 369], outline="black", width=3)  # end
    d.line([200, 70, 200, 155], fill="black", width=3)  # start -> action, touching both
    d.line([200, 225, 200, 325], fill="black", width=3)  # action -> end, touching both


def test_shapes_are_found_even_when_lines_touch_them():
    assert sorted(_kinds(_touching_pipeline)) == ["action", "end", "start"]


def test_a_start_marker_fused_with_its_line_is_still_a_start():
    def draw(d):
        d.ellipse([180, 30, 220, 70], fill="black")
        d.line([200, 70, 200, 200], fill="black", width=3)

    assert _kinds(draw) == ["start"]


def test_arrowhead_is_not_mistaken_for_a_shape():
    def draw(d):
        d.line([200, 30, 200, 150], fill="black", width=3)
        d.polygon([(200, 170), (190, 140), (210, 140)], fill="black")  # arrowhead

    assert _kinds(draw) == []


def test_edge_text_is_not_mistaken_for_a_shape():
    def draw(d):
        d.text((100, 100), "yes", fill="black")

    assert _kinds(draw) == []


def test_curved_connector_endpoints_are_its_real_ends():
    def draw(d):
        # a C-shaped back edge: the leftmost pixels are the bulge, not the ends
        d.arc([20, 100, 220, 300], start=90, end=270, fill="black", width=3)

    connectors = detect_activity_connectors(_binary(draw), [])

    assert len(connectors) == 1
    ends = {(connectors[0].x1, connectors[0].y1), (connectors[0].x2, connectors[0].y2)}
    assert all(abs(y - 100) < 6 or abs(y - 300) < 6 for _, y in ends)
