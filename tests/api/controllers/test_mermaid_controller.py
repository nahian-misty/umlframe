import pytest
from fastapi import HTTPException

from backend.api.controllers import mermaid_controller
from backend.models.requests import JsonToMermaidRequest
from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size, UmlClass, UmlDocument

_POS, _SIZE = Position(x=0, y=0), Size(width=160, height=80)


def _class_doc() -> UmlDocument:
    return UmlDocument(
        classes=[
            UmlClass(id="class_1", name="User", attributes=[], methods=[], position=_POS, size=_SIZE)
        ],
        relationships=[],
    )


def _activity_doc() -> ActivityDocument:
    return ActivityDocument(
        nodes=[
            ActivityNode(id="n1", type=ActivityNodeType.START, position=_POS, size=_SIZE),
            ActivityNode(id="n2", type=ActivityNodeType.END, position=_POS, size=_SIZE),
        ],
        edges=[ActivityEdge(id="e1", source="n1", target="n2")],
    )


async def test_class_direction_success():
    result = await mermaid_controller.json_to_mermaid(
        JsonToMermaidRequest(diagram_type="class", document=_class_doc())
    )
    assert result.diagram.startswith("classDiagram")


async def test_activity_direction_success():
    result = await mermaid_controller.json_to_mermaid(
        JsonToMermaidRequest(diagram_type="activity", activity=_activity_doc())
    )
    assert result.diagram.startswith("flowchart TD")


async def test_service_error_maps_to_500(monkeypatch):
    def _raise(_doc):
        raise RuntimeError("boom")

    monkeypatch.setattr(mermaid_controller.mermaid_service, "document_to_mermaid", _raise)

    with pytest.raises(HTTPException) as exc:
        await mermaid_controller.json_to_mermaid(
            JsonToMermaidRequest(diagram_type="class", document=_class_doc())
        )
    assert exc.value.status_code == 500
