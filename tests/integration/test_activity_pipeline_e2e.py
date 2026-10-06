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


def test_coloured_diagram_with_short_arrows_and_captions_is_fully_connected():
    """Pastel and red node fills, an arrow only ~30px long between a box and a decision,
    and "Yes"/"No" captions sitting beside lines used to give 'nodes are not reachable from
    the start node' (a lost short arrow, a red box read as solid ink, caption twins)."""
    from pathlib import Path

    from backend.schemas.activity import ActivityNodeType

    data = (Path(__file__).parent.parent / "fixtures" / "activity_pin_login.png").read_bytes()
    doc = activity_image_to_document(data)

    types = [n.type for n in doc.nodes]
    assert types.count(ActivityNodeType.START) == 1
    assert types.count(ActivityNodeType.END) == 2
    assert types.count(ActivityNodeType.DECISION) == 2
    assert types.count(ActivityNodeType.ACTION) == 6

    by_id = {n.id: n for n in doc.nodes}

    def reads(node_id: str, text: str) -> bool:
        return text.lower() in by_id[node_id].label.lower()

    assert len(doc.edges) == 11
    guards = sorted(e.label for e in doc.edges if e.label)
    assert guards == ["no", "no", "yes", "yes"]
    start = next(n for n in doc.nodes if n.type == ActivityNodeType.START)
    first = next(e.target for e in doc.edges if e.source == start.id)
    assert reads(first, "initialize")
    locked = next(n for n in doc.nodes if "locked" in n.label.lower())
    assert any(e.target == locked.id and e.label == "no" for e in doc.edges)
    assert not any(reads(e.source, "enter pin") and by_id[e.target].type == ActivityNodeType.DECISION
                   and reads(e.target, "attempts") for e in doc.edges)


def _fixture(name: str) -> bytes:
    from pathlib import Path

    return (Path(__file__).parent.parent / "fixtures" / "activity" / name).read_bytes()


def test_dark_filled_nodes_ring_end_and_uml_notes_give_a_structured_login_flow():
    """Purple fills, an end marker whose ring is separated from its dot, UML notes joined by a
    dashed line, and a loop line enclosing blank space: none may become a node."""
    from backend.schemas.activity import ActivityNodeType

    doc = activity_image_to_document(_fixture("activity5.png"))
    types = [n.type for n in doc.nodes]
    assert types.count(ActivityNodeType.START) == 1
    assert types.count(ActivityNodeType.END) == 1
    assert types.count(ActivityNodeType.DECISION) == 1
    assert types.count(ActivityNodeType.ACTION) == 4
    assert len(doc.edges) == 7
    assert any("login" in n.label.lower() for n in doc.nodes)
    files = generate_activity_code(doc, "python")
    assert "while False" in next(iter(files.values()))


def test_a_line_that_splits_into_two_is_read_as_two_edges_from_one_node():
    """"Check account" fans out to two branches through a T-junction. The fork is not
    supported by the structuring step, but it must be reported as that, not as a missing node."""
    from backend.schemas.activity import ActivityNodeType

    doc = activity_image_to_document(_fixture("activity6.png"))
    check = next(n for n in doc.nodes if "check" in n.label.lower())
    assert len([e for e in doc.edges if e.source == check.id]) == 2
    assert sum(n.type == ActivityNodeType.DECISION for n in doc.nodes) == 1
    with pytest.raises(ValueError, match="exactly one outgoing edge"):
        generate_activity_code(doc, "python")


def test_ellipse_actions_and_a_solid_diamond_are_found_and_fork_join_is_reported():
    from backend.schemas.activity import ActivityNodeType

    doc = activity_image_to_document(_fixture("activity2.png"))
    types = [n.type for n in doc.nodes]
    assert types.count(ActivityNodeType.START) == 1
    assert types.count(ActivityNodeType.DECISION) == 1
    assert types.count(ActivityNodeType.ACTION) >= 7
    with pytest.raises(ValueError, match="fork/join"):
        generate_activity_code(doc, "python")
