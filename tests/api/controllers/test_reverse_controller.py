import pytest
from fastapi import HTTPException

from backend.api.controllers import reverse_controller
from backend.models.requests import ReverseRequest
from backend.schemas.uml import UmlDocument


async def test_reverse_source_success(monkeypatch):
    doc = UmlDocument()
    monkeypatch.setattr(reverse_controller.reverse_service, "source_to_document", lambda *a, **kw: doc)

    result = await reverse_controller.reverse_source(
        ReverseRequest(source="class Foo: pass", language="python")
    )

    assert result.document == doc


async def test_reverse_source_value_error_maps_to_422(monkeypatch):
    def _raise(*a, **kw):
        raise ValueError("bad source")

    monkeypatch.setattr(reverse_controller.reverse_service, "source_to_document", _raise)

    with pytest.raises(HTTPException) as exc_info:
        await reverse_controller.reverse_source(ReverseRequest(source="x", language="python"))

    assert exc_info.value.status_code == 422
    assert "bad source" in exc_info.value.detail


async def test_reverse_source_unexpected_error_maps_to_500(monkeypatch):
    def _raise(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(reverse_controller.reverse_service, "source_to_document", _raise)

    with pytest.raises(HTTPException) as exc_info:
        await reverse_controller.reverse_source(ReverseRequest(source="x", language="python"))

    assert exc_info.value.status_code == 500


async def test_reverse_source_empty_source_short_circuits_without_calling_service(monkeypatch):
    called = False

    def _spy(*a, **kw):
        nonlocal called
        called = True

    monkeypatch.setattr(reverse_controller.reverse_service, "source_to_document", _spy)

    with pytest.raises(HTTPException) as exc_info:
        await reverse_controller.reverse_source(ReverseRequest(source="   ", language="python"))

    assert exc_info.value.status_code == 422
    assert called is False
