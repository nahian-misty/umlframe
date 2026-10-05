"""Integration tests for activity-diagram OCR. Requires tesseract; skipped otherwise."""
from __future__ import annotations

import shutil

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from backend.cv.activity_shape_detector import ActivityConnector, ActivityShape
from backend.ocr.activity_extractor import extract_activity_labels, extract_edge_guard_candidates

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract-ocr binary not found"
)

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def _font(size: int):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gray(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(img.convert("RGB"), dtype=np.uint8), cv2.COLOR_RGB2GRAY)


def test_reads_action_label():
    img = Image.new("RGB", (300, 160), "white")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([30, 40, 270, 120], radius=16, outline="black", width=2)
    draw.text((50, 65), "load data", fill="black", font=_font(22))

    shapes = [ActivityShape(x=30, y=40, w=240, h=80, kind="action")]
    labels = extract_activity_labels(_gray(img), shapes)

    assert "load" in labels[0].lower()


def test_reads_decision_label():
    # A diamond's own diagonal outline strokes cut through the middle of its
    # bounding box, unlike a rounded-rect's outline, which hugs the
    # perimeter -- regression coverage for the diamond-aware crop in
    # _label_region (a flat border inset alone left the diagonal strokes in
    # the OCR crop and corrupted the read).
    img = Image.new("RGB", (300, 220), "white")
    draw = ImageDraw.Draw(img)
    cx, cy, hw, hh = 150, 110, 140, 100
    draw.polygon(
        [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)],
        outline="black",
        width=2,
    )
    draw.text((cx - 55, cy - 12), "amount > 100", fill="black", font=_font(20))

    shapes = [ActivityShape(x=cx - hw, y=cy - hh, w=hw * 2, h=hh * 2, kind="decision")]
    labels = extract_activity_labels(_gray(img), shapes)

    assert "amount" in labels[0].lower()


def test_start_and_bar_shapes_get_empty_label():
    img = Image.new("RGB", (200, 200), "white")
    shapes = [
        ActivityShape(x=10, y=10, w=40, h=40, kind="start"),
        ActivityShape(x=10, y=80, w=120, h=12, kind="bar"),
    ]
    assert extract_activity_labels(_gray(img), shapes) == ["", ""]


def _guard_candidates(label_xy: tuple[int, int]) -> list[str]:
    """A vertical edge from a decision down to an action, with `label_xy` text beside it."""
    img = Image.new("RGB", (300, 300), "white")
    draw = ImageDraw.Draw(img)
    draw.line([(150, 60), (150, 200)], fill=(107, 107, 118), width=3)  # the edge's own line
    draw.text(label_xy, "yes", fill=(29, 29, 35), font=_font(20))
    connector = ActivityConnector(x1=150, y1=70, x2=150, y2=190)
    action = ActivityShape(x=80, y=220, w=140, h=50, kind="action")
    return extract_edge_guard_candidates(_gray(img), [action], connector, action)


def test_reads_guard_label_beside_the_edge():
    candidates = _guard_candidates((165, 110))

    assert any("yes" in c.lower() for c in candidates)


def test_guard_label_found_wherever_it_sits_along_the_edge():
    assert any("yes" in c.lower() for c in _guard_candidates((165, 75)))
    assert any("yes" in c.lower() for c in _guard_candidates((95, 160)))


def test_no_guard_text_gives_no_candidates():
    img = Image.new("RGB", (300, 300), "white")
    ImageDraw.Draw(img).line([(150, 60), (150, 200)], fill=(107, 107, 118), width=3)
    connector = ActivityConnector(x1=150, y1=70, x2=150, y2=190)
    action = ActivityShape(x=80, y=220, w=140, h=50, kind="action")

    assert extract_edge_guard_candidates(_gray(img), [action], connector, action) == []
