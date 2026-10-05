import base64

import pytest
from fastapi import HTTPException

from backend.api.controllers import activity_render_controller
from backend.models.requests import ActivityDiagramImageRequest
from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size

_POS, _SIZE = Position(x=0, y=0), Size(width=160, height=80)


def _activity_doc() -> ActivityDocument:
    return ActivityDocument(
        nodes=[
            ActivityNode(id="n1", type=ActivityNodeType.START, position=_POS, size=_SIZE),
            ActivityNode(id="n2", type=ActivityNodeType.END, position=_POS, size=_SIZE),
        ],
        edges=[ActivityEdge(id="e1", source="n1", target="n2")],
    )


async def test_success_returns_base64_png():
    result = await activity_render_controller.activity_json_to_image(
        ActivityDiagramImageRequest(activity=_activity_doc())
    )
    png_bytes = base64.b64decode(result.image_base64)
    assert png_bytes.startswith(b"\x89PNG")


async def test_structuring_failure_maps_to_422(monkeypatch):
    def _raise(_doc):
        raise ValueError("unsupported shape")

    monkeypatch.setattr(
        activity_render_controller.activity_diagram_renderer, "render_activity_diagram", _raise
    )

    with pytest.raises(HTTPException) as exc:
        await activity_render_controller.activity_json_to_image(
            ActivityDiagramImageRequest(activity=_activity_doc())
        )
    assert exc.value.status_code == 422


async def test_unexpected_error_maps_to_500(monkeypatch):
    def _raise(_doc):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        activity_render_controller.activity_diagram_renderer, "render_activity_diagram", _raise
    )

    with pytest.raises(HTTPException) as exc:
        await activity_render_controller.activity_json_to_image(
            ActivityDiagramImageRequest(activity=_activity_doc())
        )
    assert exc.value.status_code == 500
