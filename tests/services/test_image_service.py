"""
Integration tests for the image → UmlDocument pipeline.
Requires tesseract-ocr to be installed; skipped otherwise.
"""
from __future__ import annotations

import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from backend.services.image_service import image_to_document

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="tesseract-ocr binary not found",
)

# ---------------------------------------------------------------------------
# Fixture image helpers
# ---------------------------------------------------------------------------

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def _font(size: int):
    for p in FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_single_class_png(
    class_name: str = "User",
    attr_line: str = "- email : String",
    method_line: str = "+ login() : void",
) -> bytes:
    font_title = _font(20)
    font_body = _font(15)
    pad = 10
    box_w = 220
    row_h = 26
    name_h = row_h + pad * 2
    attr_h = row_h + pad * 2
    meth_h = row_h + pad * 2
    box_h = name_h + attr_h + meth_h
    margin = 40

    img = Image.new("RGB", (box_w + margin * 2, box_h + margin * 2), "white")
    draw = ImageDraw.Draw(img)
    bx, by = margin, margin

    draw.rectangle([bx, by, bx + box_w, by + box_h], outline="black", width=2)
    d1, d2 = by + name_h, by + name_h + attr_h
    draw.line([bx, d1, bx + box_w, d1], fill="black", width=2)
    draw.line([bx, d2, bx + box_w, d2], fill="black", width=2)

    draw.text((bx + pad, by + pad), class_name, fill="black", font=font_title)
    draw.text((bx + pad, d1 + pad), attr_line, fill="black", font=font_body)
    draw.text((bx + pad, d2 + pad), method_line, fill="black", font=font_body)

    return _png_bytes(img)


def _make_two_class_png(marker: str | None, dashed: bool = False) -> bytes:
    """Two undivided (name-only) class boxes connected by a relationship line,
    with an optional marker glyph (matching
    frontend/src/components/uml/relationshipStyles.ts) at the box2
    (destination-side) end: "triangle-hollow", "diamond-hollow",
    "diamond-filled", or None for a plain (possibly dashed) chevron-style
    line. Boxes are tall and undivided so the marker glyph's search radius
    never reaches a compartment divider.
    """
    font_title = _font(16)
    box_w = 180
    box_h = 160
    margin = 40
    gap = 140
    mid_y = margin + box_h // 2

    img = Image.new(
        "RGB", (margin * 2 + box_w * 2 + gap, margin * 2 + box_h), "white"
    )
    draw = ImageDraw.Draw(img)

    def draw_box(bx: int, name: str) -> None:
        by = margin
        draw.rectangle([bx, by, bx + box_w, by + box_h], outline="black", width=2)
        draw.text((bx + 8, by + 8), name, fill="black", font=font_title)

    box1_x = margin
    box2_x = margin + box_w + gap
    draw_box(box1_x, "Dog")
    draw_box(box2_x, "Animal")

    line_x1, line_x2 = box1_x + box_w, box2_x
    if dashed:
        x = line_x1
        while x < line_x2:
            draw.line([x, mid_y, min(x + 6, line_x2), mid_y], fill="black", width=2)
            x += 10
    else:
        draw.line([line_x1, mid_y, line_x2, mid_y], fill="black", width=2)

    if marker == "triangle-hollow":
        draw.polygon(
            [(line_x2, mid_y), (line_x2 - 16, mid_y - 12), (line_x2 - 16, mid_y + 12)],
            outline="black",
            fill="white",
        )
    elif marker in ("diamond-hollow", "diamond-filled"):
        fill = "white" if marker == "diamond-hollow" else "black"
        draw.polygon(
            [
                (line_x1, mid_y),
                (line_x1 + 16, mid_y - 12),
                (line_x1 + 32, mid_y),
                (line_x1 + 16, mid_y + 12),
            ],
            outline="black",
            fill=fill,
        )

    return _png_bytes(img)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_single_class_detected():
    doc = image_to_document(_make_single_class_png())
    assert len(doc.classes) == 1


def test_class_name_extracted():
    doc = image_to_document(_make_single_class_png(class_name="User"))
    assert doc.classes[0].name == "User"


def test_attribute_extracted():
    doc = image_to_document(_make_single_class_png(attr_line="- email : String"))
    cls = doc.classes[0]
    assert len(cls.attributes) >= 1
    attr = cls.attributes[0]
    assert attr.name == "email"
    assert "String" in attr.datatype or "str" in attr.datatype
    assert attr.visibility.value == "private"


def test_method_extracted():
    doc = image_to_document(_make_single_class_png(method_line="+ login() : void"))
    cls = doc.classes[0]
    assert len(cls.methods) >= 1
    method = cls.methods[0]
    assert method.name == "login"
    assert method.visibility.value == "public"


def test_document_is_valid_pydantic():
    from backend.schemas.uml import UmlDocument

    doc = image_to_document(_make_single_class_png())
    assert isinstance(doc, UmlDocument)


def test_empty_white_image_returns_empty_document():
    img = Image.new("RGB", (400, 300), "white")
    doc = image_to_document(_png_bytes(img))
    assert doc.classes == []
    assert doc.relationships == []


# ---------------------------------------------------------------------------
# Relationship type classification (end-to-end)
# ---------------------------------------------------------------------------


def _dog(doc):
    return next(c for c in doc.classes if c.name == "Dog")


def _animal(doc):
    return next(c for c in doc.classes if c.name == "Animal")


def test_plain_line_is_association():
    doc = image_to_document(_make_two_class_png(marker=None))
    assert len(doc.relationships) == 1
    assert doc.relationships[0].type.value == "association"


def test_dashed_line_is_dependency():
    doc = image_to_document(_make_two_class_png(marker=None, dashed=True))
    assert len(doc.relationships) == 1
    assert doc.relationships[0].type.value == "dependency"


def test_hollow_triangle_is_inheritance_with_child_as_source():
    doc = image_to_document(_make_two_class_png(marker="triangle-hollow"))
    assert len(doc.relationships) == 1
    rel = doc.relationships[0]
    assert rel.type.value == "inheritance"
    assert rel.source == _dog(doc).id
    assert rel.destination == _animal(doc).id


def test_hollow_diamond_is_aggregation_with_whole_as_source():
    doc = image_to_document(_make_two_class_png(marker="diamond-hollow"))
    assert len(doc.relationships) == 1
    rel = doc.relationships[0]
    assert rel.type.value == "aggregation"
    assert rel.source == _dog(doc).id
    assert rel.destination == _animal(doc).id


def test_filled_diamond_is_composition_with_whole_as_source():
    doc = image_to_document(_make_two_class_png(marker="diamond-filled"))
    assert len(doc.relationships) == 1
    rel = doc.relationships[0]
    assert rel.type.value == "composition"
    assert rel.source == _dog(doc).id
    assert rel.destination == _animal(doc).id
