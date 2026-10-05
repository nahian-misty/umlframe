"""The real guarantee this module provides is a round-trip: an ActivityDocument
rendered to PNG must be re-ingestible by the actual CV pipeline
(detect_activity_shapes -> detect_activity_connectors -> activity_image_to_document)
and must structure (activity_structuring) into the same shape it started
from. Pixel-level assertions on the drawing itself would be brittle and
wouldn't catch the real failure mode this module exists to prevent (shapes or
connector lines silently fusing or going undetected) -- so these tests always
go through the real detector and structurer, not mocks."""
from __future__ import annotations

from backend.reverse.python.parser import extract_control_flow
from backend.services.activity_diagram_renderer import render_activity_diagram
from backend.services.activity_image_service import activity_image_to_document
from backend.services.activity_structuring import IRAction, IRIf, IRWhile, structure_activity


def _roundtrip(document):
    png = render_activity_diagram(document)
    return activity_image_to_document(png)


def _doc_from_source(source: str, class_name: str, method_name: str):
    return extract_control_flow(source, class_name, method_name)


def test_linear_sequence_roundtrips():
    doc = _doc_from_source(
        """
class B:
    def run(self):
        x = 1
        return x
""",
        "B",
        "run",
    )
    recovered = _roundtrip(doc)
    ir = structure_activity(recovered)
    assert len(ir) == 1
    assert isinstance(ir[0], IRAction)


def test_if_else_roundtrips():
    doc = _doc_from_source(
        """
class A:
    def check(self, amount):
        if amount > 100:
            status = "approved"
        else:
            status = "rejected"
        return status
""",
        "A",
        "check",
    )
    recovered = _roundtrip(doc)
    ir = structure_activity(recovered)
    kinds = [type(n).__name__ for n in ir]
    assert "IRIf" in kinds
    if_node = next(n for n in ir if isinstance(n, IRIf))
    assert len(if_node.then_body) == 1
    assert len(if_node.else_body) == 1


def test_while_loop_roundtrips():
    doc = _doc_from_source(
        """
class C:
    def process(self, quantity):
        total = 0
        while quantity > 0:
            total = total + 10
            quantity = quantity - 1
        return total
""",
        "C",
        "process",
    )
    recovered = _roundtrip(doc)
    ir = structure_activity(recovered)
    kinds = [type(n).__name__ for n in ir]
    assert "IRWhile" in kinds
    while_node = next(n for n in ir if isinstance(n, IRWhile))
    assert len(while_node.body) == 1


def test_while_then_if_else_roundtrips():
    # The original failure mode this module was built to fix: a loop body
    # placed in its own offset column, immediately followed by an if/else --
    # both a back edge and a branch merge present in the same diagram.
    doc = _doc_from_source(
        """
class D:
    def process_order(self, quantity):
        total = 0
        while quantity > 0:
            total = total + 10
            quantity = quantity - 1
        if total > 50:
            status = "approved"
        else:
            status = "rejected"
        return status
""",
        "D",
        "process_order",
    )
    recovered = _roundtrip(doc)
    ir = structure_activity(recovered)
    kinds = [type(n).__name__ for n in ir]
    assert kinds.count("IRWhile") == 1
    assert kinds.count("IRIf") == 1
    # Confirms the back edge survived as a real graph cycle, not a dropped
    # edge papered over by the exit edge alone.
    while_node = next(n for n in ir if isinstance(n, IRWhile))
    assert len(while_node.body) == 1
