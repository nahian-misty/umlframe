"""End-to-end forward activity pipeline: activity-diagram image -> CV/OCR ->
ActivityDocument -> structured control-flow codegen.

Gated on tesseract (the OCR stage is real here, not synthetic).
"""
from __future__ import annotations

import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from backend.services.activity_codegen_service import generate_activity_code
from backend.services.activity_image_service import activity_image_to_document

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract-ocr binary not found"
)

_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def _font(size: int):
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _if_else_activity_png() -> bytes:
    img = Image.new("RGB", (640, 760), "white")
    d = ImageDraw.Draw(img)

    d.ellipse([304, 24, 336, 56], fill="black")  # start
    d.polygon(  # decision
        [(320, 110), (415, 170), (320, 230), (225, 170)], outline="black", width=3
    )
    d.text((286, 160), "x > 0", fill="black", font=_font(18))
    d.rounded_rectangle([80, 330, 300, 400], radius=8, outline="black", width=3)
    d.text((94, 344), "pos", fill="black", font=_font(20))
    d.rounded_rectangle([360, 330, 580, 400], radius=8, outline="black", width=3)
    d.text((374, 344), "neg", fill="black", font=_font(20))
    d.ellipse([300, 520, 340, 560], outline="black", width=3)  # end

    d.line([320, 60, 320, 106], fill="black", width=2)
    d.line([250, 205, 195, 322], fill="black", width=2)
    d.line([390, 205, 445, 322], fill="black", width=2)
    d.line([195, 406, 300, 522], fill="black", width=2)
    d.line([445, 406, 340, 522], fill="black", width=2)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_activity_image_to_structured_python_code():
    document = activity_image_to_document(_if_else_activity_png())

    # The structuring-critical shape survived CV + orientation.
    assert sum(1 for n in document.nodes if n.type.value == "decision") == 1
    assert sum(1 for n in document.nodes if n.type.value == "start") == 1
    assert sum(1 for n in document.nodes if n.type.value == "end") == 1

    files = generate_activity_code(document, "python", "classify")
    code = files["classify.py"]

    compile(code, "classify.py", "exec")  # generated code is syntactically valid
    assert "def classify():" in code
    # The branching *shape* is reconstructed; the condition is never fabricated
    # from the (OCR-noisy) label -- it stays a literal placeholder + comment.
    assert "if True:  #" in code
    assert "else:" in code
    assert "# TODO:" in code  # action bodies stay stubs


def test_activity_image_to_structured_code_all_languages():
    document = activity_image_to_document(_if_else_activity_png())
    for language in ("python", "java", "javascript"):
        files = generate_activity_code(document, language, "classify")
        assert len(files) == 1
        assert any(marker in next(iter(files.values())) for marker in ("if True", "if (true)"))
