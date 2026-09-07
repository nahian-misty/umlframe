"""CV shape detection tests using programmatically generated images."""
from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image, ImageDraw

from backend.cv.preprocessor import preprocess
from backend.cv.shape_detector import detect_shapes


def _make_image_bytes(draw_fn) -> bytes:
    img = Image.new("RGB", (500, 400), "white")
    draw = ImageDraw.Draw(img)
    draw_fn(img, draw)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _single_box_image() -> bytes:
    def draw(img, d):
        d.rectangle([50, 50, 250, 200], outline="black", width=2)
        d.line([50, 90, 250, 90], fill="black", width=2)
        d.line([50, 130, 250, 130], fill="black", width=2)

    return _make_image_bytes(draw)


def _two_box_image() -> bytes:
    def draw(img, d):
        # Box 1
        d.rectangle([30, 50, 200, 200], outline="black", width=2)
        d.line([30, 90, 200, 90], fill="black", width=2)
        d.line([30, 140, 200, 140], fill="black", width=2)
        # Box 2
        d.rectangle([260, 50, 430, 200], outline="black", width=2)
        d.line([260, 90, 430, 90], fill="black", width=2)
        d.line([260, 140, 430, 140], fill="black", width=2)
        # Line connecting them
        d.line([200, 125, 260, 125], fill="black", width=2)

    return _make_image_bytes(draw)


def _empty_image() -> bytes:
    return _make_image_bytes(lambda img, d: None)


def _draw_two_boxes(d) -> None:
    d.rectangle([30, 50, 200, 200], outline="black", width=2)
    d.line([30, 90, 200, 90], fill="black", width=2)
    d.line([30, 140, 200, 140], fill="black", width=2)
    d.rectangle([260, 50, 430, 200], outline="black", width=2)
    d.line([260, 90, 430, 90], fill="black", width=2)
    d.line([260, 140, 430, 140], fill="black", width=2)


def _draw_dashed_hline(d, x1: int, x2: int, y: int, dash: int = 6, gap: int = 4) -> None:
    x = x1
    while x < x2:
        d.line([x, y, min(x + dash, x2), y], fill="black", width=2)
        x += dash + gap


def _two_box_dashed_line_image() -> bytes:
    def draw(img, d):
        _draw_two_boxes(d)
        _draw_dashed_hline(d, 200, 260, 125)

    return _make_image_bytes(draw)


def _two_box_triangle_marker_image() -> bytes:
    """Solid line from box1 into box2, with a hollow triangle at the box2 end
    (inheritance: destination = box2, the parent)."""

    def draw(img, d):
        _draw_two_boxes(d)
        d.line([200, 125, 244, 125], fill="black", width=2)
        d.polygon([(260, 125), (244, 112), (244, 138)], outline="black", fill="white")

    return _make_image_bytes(draw)


def _draw_two_boxes_wide(d) -> None:
    """Like _draw_two_boxes but with more horizontal clearance between the
    boxes, leaving enough straight line length for Hough to detect once a
    marker glyph eats into part of the gap near one box."""
    d.rectangle([30, 50, 200, 200], outline="black", width=2)
    d.line([30, 90, 200, 90], fill="black", width=2)
    d.line([30, 140, 200, 140], fill="black", width=2)
    d.rectangle([320, 50, 490, 200], outline="black", width=2)
    d.line([320, 90, 490, 90], fill="black", width=2)
    d.line([320, 140, 490, 140], fill="black", width=2)


def _two_box_hollow_diamond_marker_image() -> bytes:
    """Solid line from box1 into box2, with a hollow diamond near the box1 end
    (aggregation: source = box1, the whole). A few px of clearance from the
    box border avoids conflating the diamond's own outline with the box's —
    a tolerance real anti-aliased renders have naturally."""

    def draw(img, d):
        _draw_two_boxes_wide(d)
        d.line([204, 125, 320, 125], fill="black", width=2)
        d.polygon([(204, 125), (220, 113), (236, 125), (220, 137)], outline="black", fill="white")

    return _make_image_bytes(draw)


def _two_box_filled_diamond_marker_image() -> bytes:
    """Solid line from box1 into box2, with a filled diamond near the box1 end
    (composition: source = box1, the whole). See _two_box_hollow_diamond_marker_image
    for why a few px of clearance from the box border is used."""

    def draw(img, d):
        _draw_two_boxes_wide(d)
        d.line([204, 125, 320, 125], fill="black", width=2)
        d.polygon([(204, 125), (220, 113), (236, 125), (220, 137)], outline="black", fill="black")

    return _make_image_bytes(draw)


def _undivided_box_image() -> bytes:
    """A class box drawn with no attribute/method divider lines at all."""

    def draw(img, d):
        d.rectangle([50, 50, 250, 150], outline="black", width=2)

    return _make_image_bytes(draw)


def _stacked_unrelated_boxes_image() -> bytes:
    """Two vertically stacked, unrelated boxes sharing the same x-alignment but
    separated by a large gap — must not be merged into one class box."""

    def draw(img, d):
        d.rectangle([50, 30, 250, 120], outline="black", width=2)
        d.line([50, 70, 250, 70], fill="black", width=2)
        d.rectangle([50, 250, 250, 340], outline="black", width=2)
        d.line([50, 290, 250, 290], fill="black", width=2)

    return _make_image_bytes(draw)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_detects_single_class_box():
    _, _, binary = preprocess(_single_box_image())
    shapes = detect_shapes(binary)
    assert len(shapes.class_boxes) == 1


def test_single_box_has_two_dividers():
    # Box has 3 compartments → 2 inter-compartment dividers
    _, _, binary = preprocess(_single_box_image())
    shapes = detect_shapes(binary)
    # hole-based detection: dividers = boundaries between adjacent compartments
    assert len(shapes.class_boxes[0].dividers_y) == 2


def test_single_box_position():
    _, _, binary = preprocess(_single_box_image())
    shapes = detect_shapes(binary)
    box = shapes.class_boxes[0]
    assert abs(box.x - 50) <= 3
    assert abs(box.y - 50) <= 3


def test_detects_two_class_boxes():
    _, _, binary = preprocess(_two_box_image())
    shapes = detect_shapes(binary)
    assert len(shapes.class_boxes) == 2


def test_empty_image_no_boxes():
    _, _, binary = preprocess(_empty_image())
    shapes = detect_shapes(binary)
    assert shapes.class_boxes == []
    assert shapes.lines == []


def test_two_box_image_has_relationship_line():
    _, _, binary = preprocess(_two_box_image())
    shapes = detect_shapes(binary)
    assert len(shapes.lines) >= 1


def test_plain_line_has_no_marker_and_is_not_dashed():
    _, _, binary = preprocess(_two_box_image())
    shapes = detect_shapes(binary)
    line = shapes.lines[0]
    assert line.dashed is False
    assert line.marker_p1 is None
    assert line.marker_p2 is None


def test_dashed_line_detected():
    _, _, binary = preprocess(_two_box_dashed_line_image())
    shapes = detect_shapes(binary)
    assert len(shapes.lines) >= 1
    assert any(line.dashed for line in shapes.lines)


def test_triangle_marker_detected():
    _, _, binary = preprocess(_two_box_triangle_marker_image())
    shapes = detect_shapes(binary)
    assert any(
        line.marker_p1 == "triangle-hollow" or line.marker_p2 == "triangle-hollow"
        for line in shapes.lines
    )


def test_hollow_diamond_marker_detected():
    _, _, binary = preprocess(_two_box_hollow_diamond_marker_image())
    shapes = detect_shapes(binary)
    assert any(
        line.marker_p1 == "diamond-hollow" or line.marker_p2 == "diamond-hollow"
        for line in shapes.lines
    )


def test_filled_diamond_marker_detected():
    _, _, binary = preprocess(_two_box_filled_diamond_marker_image())
    shapes = detect_shapes(binary)
    assert any(
        line.marker_p1 == "diamond-filled" or line.marker_p2 == "diamond-filled"
        for line in shapes.lines
    )


def test_undivided_box_is_still_detected():
    _, _, binary = preprocess(_undivided_box_image())
    shapes = detect_shapes(binary)
    assert len(shapes.class_boxes) == 1
    assert shapes.class_boxes[0].dividers_y == []


def test_stacked_unrelated_boxes_are_not_merged():
    _, _, binary = preprocess(_stacked_unrelated_boxes_image())
    shapes = detect_shapes(binary)
    assert len(shapes.class_boxes) == 2
