import pytest
from fastapi import HTTPException

from backend.api.controllers import reverse_controller
from backend.models.requests import ReverseRequest
from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size, UmlDocument


async def test_reverse_source_success(monkeypatch):
    doc = UmlDocument()
    monkeypatch.setattr(reverse_controller.reverse_service, "source_to_document", lambda *a, **kw: doc)

    result = await reverse_controller.reverse_source(ReverseRequest(source="class Foo: pass", language="python"))

    assert result.document == doc
    assert result.control_flow is None


async def test_reverse_source_with_class_and_method_name_includes_control_flow(monkeypatch):
    doc = UmlDocument()
    pos, size = Position(x=0, y=0), Size(width=160, height=80)
    cfg = ActivityDocument(
        nodes=[
            ActivityNode(id="n1", type=ActivityNodeType.START, position=pos, size=size),
            ActivityNode(id="n2", type=ActivityNodeType.END, position=pos, size=size),
        ],
        edges=[ActivityEdge(id="e1", source="n1", target="n2")],
    )
    monkeypatch.setattr(reverse_controller.reverse_service, "source_to_document", lambda *a, **kw: doc)
    monkeypatch.setattr(reverse_controller.reverse_service, "source_to_control_flow", lambda *a, **kw: cfg)

    result = await reverse_controller.reverse_source(
        ReverseRequest(source="class Foo:\n    def run(self): pass\n", language="python", class_name="Foo", method_name="run")
    )

    assert result.control_flow == cfg


async def test_reverse_source_control_flow_value_error_maps_to_422(monkeypatch):
    doc = UmlDocument()
    monkeypatch.setattr(reverse_controller.reverse_service, "source_to_document", lambda *a, **kw: doc)

    def _raise(*a, **kw):
        raise ValueError("method not found")

    monkeypatch.setattr(reverse_controller.reverse_service, "source_to_control_flow", _raise)

    with pytest.raises(HTTPException) as exc_info:
        await reverse_controller.reverse_source(
            ReverseRequest(source="class Foo: pass", language="python", class_name="Foo", method_name="nope")
        )

    assert exc_info.value.status_code == 422
    assert "method not found" in exc_info.value.detail


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
