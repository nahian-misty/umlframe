"""Unit tests for the mermaid service's class-diagram sequencing entrypoint."""
from __future__ import annotations

from backend.schemas.uml import Position, Size, UmlClass, UmlDocument
from backend.services import mermaid_service

_POS = Position(x=0, y=0)
_SIZE = Size(width=160, height=80)


def test_document_to_mermaid_renders_class_diagram():
    doc = UmlDocument(
        classes=[
            UmlClass(id="class_1", name="User", attributes=[], methods=[], position=_POS, size=_SIZE)
        ],
        relationships=[],
    )
    out = mermaid_service.document_to_mermaid(doc)
    assert out.startswith("classDiagram")
    assert "class User" in out
