"""Unit tests for the mermaid service's two sequencing entrypoints. Real
Pydantic documents in, Mermaid text out -- no mocks."""
from __future__ import annotations

from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
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


def test_activity_to_mermaid_renders_flowchart():
    doc = ActivityDocument(
        nodes=[
            ActivityNode(id="n1", type=ActivityNodeType.START, position=_POS, size=_SIZE),
            ActivityNode(
                id="n2", type=ActivityNodeType.ACTION, label="do work", position=_POS, size=_SIZE
            ),
            ActivityNode(id="n3", type=ActivityNodeType.END, position=_POS, size=_SIZE),
        ],
        edges=[
            ActivityEdge(id="e1", source="n1", target="n2"),
            ActivityEdge(id="e2", source="n2", target="n3"),
        ],
    )
    out = mermaid_service.activity_to_mermaid(doc)
    assert out.startswith("flowchart TD")
    assert 'n2["do work"]' in out
    assert "n1 --> n2" in out
