import pytest
from fastapi import HTTPException

from backend.api.controllers import activity_codegen_controller
from backend.models.requests import GenerateActivityCodeRequest
from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size

_POS, _SIZE = Position(x=0, y=0), Size(width=160, height=80)

_DOC = ActivityDocument(
    nodes=[
        ActivityNode(id="n1", type=ActivityNodeType.START, position=_POS, size=_SIZE),
        ActivityNode(id="n2", type=ActivityNodeType.END, position=_POS, size=_SIZE),
    ],
    edges=[ActivityEdge(id="e1", source="n1", target="n2")],
)


def _request(**kw) -> GenerateActivityCodeRequest:
    return GenerateActivityCodeRequest(document=_DOC, language="python", **kw)


async def test_success_returns_files():
    result = await activity_codegen_controller.generate(_request(function_name="noop"))
    assert "noop.py" in result.files


async def test_value_error_maps_to_422(monkeypatch):
    def _raise(*a, **kw):
        raise ValueError("fork/join not supported")

    monkeypatch.setattr(
        activity_codegen_controller.activity_codegen_service, "generate_activity_code", _raise
    )

    with pytest.raises(HTTPException) as exc:
        await activity_codegen_controller.generate(_request())
    assert exc.value.status_code == 422
    assert "fork/join" in exc.value.detail


async def test_unexpected_error_maps_to_500(monkeypatch):
    def _raise(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        activity_codegen_controller.activity_codegen_service, "generate_activity_code", _raise
    )

    with pytest.raises(HTTPException) as exc:
        await activity_codegen_controller.generate(_request())
    assert exc.value.status_code == 500
