"""A diagram whose connectors carry captions and guards over the line itself
(the text interrupts the stroke) must still be one connected graph."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from backend.schemas.activity import ActivityNodeType
from backend.services.activity_image_service import activity_image_to_document

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract-ocr binary not found"
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "activity_labelled_lines.png"
EXPECTED_NODE_COUNT = 7
EXPECTED_EDGE_COUNT = 7


def test_labelled_lines_form_a_connected_graph() -> None:
    document = activity_image_to_document(FIXTURE.read_bytes())

    assert len(document.nodes) == EXPECTED_NODE_COUNT
    assert len(document.edges) == EXPECTED_EDGE_COUNT
    assert [n.type for n in document.nodes].count(ActivityNodeType.DECISION) == 1


def test_loop_back_edge_points_at_the_earlier_action() -> None:
    document = activity_image_to_document(FIXTURE.read_bytes())
    labels = {n.id: n.label for n in document.nodes}

    pairs = {(labels[e.source], labels[e.target]) for e in document.edges}

    assert ("Rejected", "Get details") in pairs


def test_guards_on_the_decision_branches_are_read() -> None:
    document = activity_image_to_document(FIXTURE.read_bytes())
    labels = {n.id: n.label for n in document.nodes}
    guards = {labels[e.target]: e.label for e in document.edges if e.label}

    assert guards == {"Rejected": "no", "Accepted": "yes"}
