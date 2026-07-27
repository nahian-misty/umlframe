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
