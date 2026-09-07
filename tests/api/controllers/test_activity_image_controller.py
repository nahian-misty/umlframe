import io

import pytest
from fastapi import HTTPException, UploadFile

from backend.api.controllers import activity_image_controller
from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size

_POS, _SIZE = Position(x=0, y=0), Size(width=160, height=80)


def _upload(content: bytes = b"\x89PNG", content_type: str | None = "image/png") -> UploadFile:
    return UploadFile(
        filename="d.png",
        file=io.BytesIO(content),
        headers={"content-type": content_type} if content_type else None,
    )


async def test_success_returns_document(monkeypatch):
    doc = ActivityDocument(
        nodes=[
            ActivityNode(id="n1", type=ActivityNodeType.START, position=_POS, size=_SIZE),
            ActivityNode(id="n2", type=ActivityNodeType.END, position=_POS, size=_SIZE),
        ],
        edges=[ActivityEdge(id="e1", source="n1", target="n2")],
    )
    monkeypatch.setattr(
        activity_image_controller.activity_image_service,
        "activity_image_to_document",
        lambda _bytes: doc,
    )

    result = await activity_image_controller.activity_image_to_json(_upload())

    assert result.document == doc


async def test_wrong_content_type_maps_to_422():
    with pytest.raises(HTTPException) as exc:
        await activity_image_controller.activity_image_to_json(_upload(content_type="text/plain"))
    assert exc.value.status_code == 422


async def test_empty_file_maps_to_422():
    with pytest.raises(HTTPException) as exc:
        await activity_image_controller.activity_image_to_json(_upload(content=b""))
    assert exc.value.status_code == 422


async def test_value_error_maps_to_422(monkeypatch):
    def _raise(_bytes):
        raise ValueError("no start node")

    monkeypatch.setattr(
        activity_image_controller.activity_image_service, "activity_image_to_document", _raise
    )

    with pytest.raises(HTTPException) as exc:
        await activity_image_controller.activity_image_to_json(_upload())
    assert exc.value.status_code == 422
    assert "no start node" in exc.value.detail


async def test_validation_error_maps_to_422(monkeypatch):
    def _raise(_bytes):
        ActivityDocument(nodes=[], edges=[])  # triggers the validator

    monkeypatch.setattr(
        activity_image_controller.activity_image_service, "activity_image_to_document", _raise
    )

    with pytest.raises(HTTPException) as exc:
        await activity_image_controller.activity_image_to_json(_upload())
    assert exc.value.status_code == 422


async def test_unexpected_error_maps_to_500(monkeypatch):
    def _raise(_bytes):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        activity_image_controller.activity_image_service, "activity_image_to_document", _raise
    )

    with pytest.raises(HTTPException) as exc:
        await activity_image_controller.activity_image_to_json(_upload())
    assert exc.value.status_code == 500
