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
