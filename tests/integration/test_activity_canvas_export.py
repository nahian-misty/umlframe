"""The activity canvas's own Export PNG must survive the Activity -> Code image pipeline.

The fixture is a real export from the app (a dark-mode session, so it also guards the
export forcing the light palette): lines touch every node, outlines are light grey, the
loop's back edge is a curve, and two decisions carry yes/no guard text.
"""
from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

import pytest

from backend.schemas.activity import ActivityDocument, ActivityNodeType
from backend.services.activity_codegen_service import generate_activity_code
from backend.services.activity_image_service import activity_image_to_document

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract-ocr binary not found"
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "activity_canvas_export.png"


@pytest.fixture(scope="module")
def document() -> ActivityDocument:
    return activity_image_to_document(FIXTURE.read_bytes())


def test_every_node_is_found_with_the_right_type(document):
    counts = Counter(node.type for node in document.nodes)

    assert counts == {
        ActivityNodeType.START: 1,
        ActivityNodeType.END: 1,
        ActivityNodeType.ACTION: 6,
        ActivityNodeType.DECISION: 2,
    }


def test_every_edge_is_recovered_including_the_loop_back_edge(document):
    edges = {(e.source, e.target) for e in document.edges}

    assert len(document.edges) == 11
    # the loop: header -> body, and the curved back edge body -> header
    assert ("n7", "n8") in edges
    assert ("n8", "n7") in edges


def test_guard_labels_are_read_on_both_decisions(document):
    guards = {(e.source, e.target): e.label for e in document.edges if e.label}

    assert guards == {
        ("n3", "n4"): "yes",
        ("n3", "n5"): "no",
        ("n7", "n8"): "yes",
        ("n7", "n9"): "no",
    }


def test_the_extracted_diagram_generates_structured_code(document):
    code = generate_activity_code(document, "python")["generated_function.py"]

    assert "if True:" in code
    assert "else:" in code
    assert "while False:" in code
