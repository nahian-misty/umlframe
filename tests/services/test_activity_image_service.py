"""Integration tests for the activity-image -> ActivityDocument pipeline.

Graph-structure and error-path assertions run without tesseract; label/guard
assertions need the OCR binary and are skipped when it is missing.
"""
from __future__ import annotations

import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from backend.schemas.activity import ActivityNodeType
from backend.services.activity_image_service import activity_image_to_document

_NEEDS_TESSERACT = pytest.mark.skipif(
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


def _png(draw_fn, size=(640, 760)) -> bytes:
    img = Image.new("RGB", size, "white")
    draw_fn(ImageDraw.Draw(img))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _start(d, cx, cy):
    d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill="black")


def _end(d, cx, cy):
    d.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], outline="black", width=3)


def _action(d, box, text=""):
    d.rounded_rectangle(box, radius=8, outline="black", width=3)
    if text:
        d.text((box[0] + 14, box[1] + 14), text, fill="black", font=_font(20))


def _decision(d, cx, cy, text=""):
    d.polygon(
        [(cx, cy - 60), (cx + 95, cy), (cx, cy + 60), (cx - 95, cy)],
        outline="black",
        width=3,
    )
    if text:
        d.text((cx - 40, cy - 10), text, fill="black", font=_font(18))


# ---------------------------------------------------------------------------
# Error paths -- must raise, never emit a wrong graph (no OCR involved)
# ---------------------------------------------------------------------------


def test_two_start_nodes_raises():
    def draw(d):
        _start(d, 200, 40)
        _start(d, 440, 40)
        _end(d, 320, 300)
        d.line([200, 60, 315, 276], fill="black", width=3)
        d.line([440, 60, 325, 276], fill="black", width=3)

    with pytest.raises(ValueError, match="exactly one start"):
        activity_image_to_document(_png(draw))


def test_node_unreachable_from_start_raises():
    def draw(d):
        _start(d, 200, 40)
        _end(d, 200, 300)
        _end(d, 460, 300)  # isolated -- no path from start
        d.line([200, 60, 200, 276], fill="black", width=3)

    with pytest.raises(ValueError, match="not reachable from the start"):
        activity_image_to_document(_png(draw))


def test_no_shapes_raises():
    with pytest.raises(ValueError, match="No activity-diagram shapes"):
        activity_image_to_document(_png(lambda d: None))


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


@_NEEDS_TESSERACT
def test_straight_sequence():
    def draw(d):
        _start(d, 300, 40)
        _action(d, [180, 150, 420, 220], "load data")
        _end(d, 300, 340)
        d.line([300, 60, 300, 146], fill="black", width=2)
        d.line([300, 224, 300, 316], fill="black", width=2)

    doc = activity_image_to_document(_png(draw))

    types = [n.type for n in doc.nodes]
    assert types == [ActivityNodeType.START, ActivityNodeType.ACTION, ActivityNodeType.END]
    assert [(e.source, e.target) for e in doc.edges] == [("n1", "n2"), ("n2", "n3")]


@_NEEDS_TESSERACT
def test_if_else_decision_has_two_outgoing_edges():
    def draw(d):
        _start(d, 320, 40)
        _decision(d, 320, 170, "x > 0")
        _action(d, [80, 330, 300, 400], "pos")
        _action(d, [360, 330, 580, 400], "neg")
        _end(d, 320, 540)
        d.line([320, 60, 320, 106], fill="black", width=2)          # start -> decision
        d.line([250, 205, 195, 322], fill="black", width=2)         # decision -> left
        d.line([390, 205, 445, 322], fill="black", width=2)         # decision -> right
        d.line([195, 406, 300, 522], fill="black", width=2)         # left -> end
        d.line([445, 406, 340, 522], fill="black", width=2)         # right -> end

    doc = activity_image_to_document(_png(draw))

    decision = next(n for n in doc.nodes if n.type == ActivityNodeType.DECISION)
    out = [e for e in doc.edges if e.source == decision.id]
    assert len(out) == 2
    assert sum(1 for n in doc.nodes if n.type == ActivityNodeType.START) == 1
    assert sum(1 for n in doc.nodes if n.type == ActivityNodeType.END) == 1


@_NEEDS_TESSERACT
def test_while_loop_back_edge_is_structurable():
    from backend.services.activity_structuring import IRWhile, structure_activity

    def draw(d):
        _start(d, 340, 40)
        _decision(d, 340, 170, "n > 0")
        _action(d, [250, 330, 470, 400], "n -= 1")
        _end(d, 560, 170)
        d.line([340, 60, 340, 106], fill="black", width=2)          # start -> decision
        d.line([340, 236, 340, 326], fill="black", width=2)         # decision -> body (yes)
        d.line([233, 340, 236, 185], fill="black", width=2)         # body -> decision (back edge)
        d.line([443, 170, 534, 170], fill="black", width=2)         # decision -> end (no)

    doc = activity_image_to_document(_png(draw))

    decision = next(n for n in doc.nodes if n.type == ActivityNodeType.DECISION)
    action = next(n for n in doc.nodes if n.type == ActivityNodeType.ACTION)
    assert len([e for e in doc.edges if e.source == decision.id]) == 2
    assert [(e.source, e.target) for e in doc.edges if e.source == action.id] == [
        (action.id, decision.id)
    ]

    ir = structure_activity(doc)
    assert len(ir) == 1 and isinstance(ir[0], IRWhile)
