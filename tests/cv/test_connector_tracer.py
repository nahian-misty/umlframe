"""Elbow connectors that cross come out of the binary image as one blob touching every
box; the tracer walks each line from its box, straight on through a crossing."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw

from backend.cv.preprocessor import preprocess_class_ink
from backend.cv.shape_detector import DetectedShapes, detect_shapes

OUTLINE = (40, 40, 40)
WIDTH = 3


def _detect(img: Image.Image) -> DetectedShapes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    _, gray, binary = preprocess_class_ink(buf.getvalue())
    return detect_shapes(binary, gray)


def _box(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.rectangle([x, y, x + 160, y + 120], outline=OUTLINE, width=WIDTH)
    draw.line([x, y + 40, x + 160, y + 40], fill=OUTLINE, width=WIDTH)
    draw.line([x, y + 80, x + 160, y + 80], fill=OUTLINE, width=WIDTH)


def _arrow_right(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.line([x - 16, y - 8, x, y, x - 16, y + 8], fill=OUTLINE, width=WIDTH)


def _arrow_down(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.line([x - 8, y - 16, x, y, x + 8, y - 16], fill=OUTLINE, width=WIDTH)


def _two_crossing_lines() -> Image.Image:
    """Left -> right and top -> bottom, crossing in the middle, each with an open head."""
    img = Image.new("RGB", (860, 760), "white")
    draw = ImageDraw.Draw(img)
    for x, y in ((40, 300), (660, 300), (350, 40), (350, 600)):
        _box(draw, x, y)
    draw.line([200, 360, 660, 360], fill=OUTLINE, width=WIDTH)
    _arrow_right(draw, 660, 360)
    draw.line([430, 160, 430, 600], fill=OUTLINE, width=WIDTH)
    _arrow_down(draw, 430, 600)
    return img


def test_two_crossing_lines_are_two_relationships_not_a_hub():
    shapes = _detect(_two_crossing_lines())
    by_x = sorted(range(len(shapes.class_boxes)), key=lambda i: shapes.class_boxes[i].x)
    left, right = by_x[0], by_x[-1]
    top = min(range(len(shapes.class_boxes)), key=lambda i: shapes.class_boxes[i].y)
    bottom = max(range(len(shapes.class_boxes)), key=lambda i: shapes.class_boxes[i].y)

    ends = {frozenset((line.box_p1, line.box_p2)) for line in shapes.lines}

    assert len(shapes.lines) == 2
    assert ends == {frozenset((left, right)), frozenset((top, bottom))}
    assert all({line.marker_p1, line.marker_p2} == {None, "arrow-open"} for line in shapes.lines)
    assert not any(line.dashed for line in shapes.lines)


def test_an_elbow_line_crossed_by_a_straight_one_keeps_its_corners():
    img = Image.new("RGB", (860, 760), "white")
    draw = ImageDraw.Draw(img)
    for x, y in ((40, 300), (660, 40), (350, 40), (350, 600)):
        _box(draw, x, y)
    draw.line([200, 360, 560, 360, 560, 100, 660, 100], fill=OUTLINE, width=WIDTH)
    _arrow_right(draw, 660, 100)
    draw.line([430, 160, 430, 600], fill=OUTLINE, width=WIDTH)
    _arrow_down(draw, 430, 600)
    shapes = _detect(img)

    assert len(shapes.lines) == 2
    ends = sorted(sorted((line.box_p1, line.box_p2)) for line in shapes.lines)
    assert len(ends) == 2 and ends[0] != ends[1]
