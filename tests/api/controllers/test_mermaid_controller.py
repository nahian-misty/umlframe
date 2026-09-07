import pytest
from fastapi import HTTPException

from backend.api.controllers import mermaid_controller
from backend.models.requests import JsonToMermaidRequest
from backend.schemas.uml import Position, Size, UmlClass, UmlDocument

_POS, _SIZE = Position(x=0, y=0), Size(width=160, height=80)


def _class_doc() -> UmlDocument:
    return UmlDocument(
        classes=[
            UmlClass(id="class_1", name="User", attributes=[], methods=[], position=_POS, size=_SIZE)
        ],
        relationships=[],
    )


async def test_success():
    result = await mermaid_controller.json_to_mermaid(JsonToMermaidRequest(document=_class_doc()))
    assert result.diagram.startswith("classDiagram")


async def test_service_error_maps_to_500(monkeypatch):
    def _raise(_doc):
        raise RuntimeError("boom")

    monkeypatch.setattr(mermaid_controller.mermaid_service, "document_to_mermaid", _raise)

    with pytest.raises(HTTPException) as exc:
        await mermaid_controller.json_to_mermaid(JsonToMermaidRequest(document=_class_doc()))
    assert exc.value.status_code == 500
