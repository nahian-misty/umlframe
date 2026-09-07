"""Integration tests for activity-diagram OCR. Requires tesseract; skipped otherwise."""
from __future__ import annotations

import shutil

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from backend.cv.activity_shape_detector import ActivityShape
from backend.ocr.activity_extractor import extract_activity_labels, extract_guard_label

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


def test_start_and_bar_shapes_get_empty_label():
    img = Image.new("RGB", (200, 200), "white")
    shapes = [
        ActivityShape(x=10, y=10, w=40, h=40, kind="start"),
        ActivityShape(x=10, y=80, w=120, h=12, kind="bar"),
    ]
    assert extract_activity_labels(_gray(img), shapes) == ["", ""]


def test_reads_guard_label_near_edge_midpoint():
    img = Image.new("RGB", (300, 200), "white")
    draw = ImageDraw.Draw(img)
    draw.text((132, 88), "yes", fill="black", font=_font(20))

    text = extract_guard_label(_gray(img), x1=100, y1=100, x2=200, y2=100)

    assert "yes" in text.lower()
