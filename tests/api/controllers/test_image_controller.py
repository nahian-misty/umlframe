import io

import pytest
from fastapi import HTTPException, UploadFile

from backend.api.controllers import image_controller
from backend.schemas.uml import UmlDocument


def _upload(content: bytes = b"\x89PNG", content_type: str | None = "image/png") -> UploadFile:
    return UploadFile(
        filename="d.png",
        file=io.BytesIO(content),
        headers={"content-type": content_type} if content_type else None,
    )


async def test_success_returns_document(monkeypatch):
    doc = UmlDocument()
    monkeypatch.setattr(image_controller.image_service, "image_to_document", lambda _b: doc)

    result = await image_controller.image_to_json(_upload())

    assert result.document == doc


async def test_wrong_content_type_maps_to_422():
    with pytest.raises(HTTPException) as exc:
        await image_controller.image_to_json(_upload(content_type="application/pdf"))
    assert exc.value.status_code == 422


async def test_empty_file_maps_to_422():
    with pytest.raises(HTTPException) as exc:
        await image_controller.image_to_json(_upload(content=b""))
    assert exc.value.status_code == 422


async def test_value_error_maps_to_422(monkeypatch):
    def _raise(_b):
        raise ValueError("bad image")

    monkeypatch.setattr(image_controller.image_service, "image_to_document", _raise)

    with pytest.raises(HTTPException) as exc:
        await image_controller.image_to_json(_upload())
    assert exc.value.status_code == 422
    assert "bad image" in exc.value.detail


async def test_unexpected_error_maps_to_500(monkeypatch):
    def _raise(_b):
        raise RuntimeError("boom")

    monkeypatch.setattr(image_controller.image_service, "image_to_document", _raise)

    with pytest.raises(HTTPException) as exc:
        await image_controller.image_to_json(_upload())
    assert exc.value.status_code == 500
