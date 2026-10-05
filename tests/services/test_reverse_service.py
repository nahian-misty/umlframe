"""Unit tests for the reverse service's sequencing + guard clauses."""
from __future__ import annotations

import pytest

from backend.schemas.activity import ActivityDocument
from backend.schemas.uml import UmlDocument
from backend.services import reverse_service

_PY_SOURCE = "class Calc:\n    def classify(self, x: int) -> str:\n        if x > 0:\n            return 'p'\n        return 'n'\n"


def test_source_to_document_happy_path():
    doc = reverse_service.source_to_document(_PY_SOURCE, "python")
    assert isinstance(doc, UmlDocument)
    assert [c.name for c in doc.classes] == ["Calc"]


def test_source_to_document_unsupported_language_raises():
    with pytest.raises(ValueError, match="Unsupported language"):
        reverse_service.source_to_document(_PY_SOURCE, "ruby")


def test_source_to_document_empty_source_raises():
    with pytest.raises(ValueError, match="empty"):
        reverse_service.source_to_document("   \n  ", "python")


def test_source_to_control_flow_happy_path():
    cfg = reverse_service.source_to_control_flow(_PY_SOURCE, "python", "Calc", "classify")
    assert isinstance(cfg, ActivityDocument)
    assert any(n.type.value == "decision" for n in cfg.nodes)


def test_source_to_control_flow_unknown_method_propagates_value_error():
    with pytest.raises(ValueError, match="not found"):
        reverse_service.source_to_control_flow(_PY_SOURCE, "python", "Calc", "nope")


def test_source_to_control_flow_unsupported_language_raises():
    with pytest.raises(ValueError, match="Unsupported language"):
        reverse_service.source_to_control_flow(_PY_SOURCE, "cobol", "Calc", "classify")


def test_source_to_control_flows_returns_one_entry_per_method():
    source = (
        "class A:\n    def one(self):\n        if x:\n            a()\n"
        "    def two(self):\n        b()\n"
    )
    results = reverse_service.source_to_control_flows(source, "python")
    assert [(r.class_name, r.method_name) for r in results] == [("A", "one"), ("A", "two")]
    assert all(r.control_flow is not None and r.error is None for r in results)


def test_source_to_control_flows_without_methods_raises():
    with pytest.raises(ValueError, match="No methods found"):
        reverse_service.source_to_control_flows("class A:\n    x = 1\n", "python")


def test_source_to_control_flows_rejects_empty_and_unknown_language():
    with pytest.raises(ValueError, match="empty"):
        reverse_service.source_to_control_flows("  ", "python")
    with pytest.raises(ValueError, match="Unsupported"):
        reverse_service.source_to_control_flows("class A: pass", "cobol")


def test_try_except_finally_control_flow_can_still_be_structured_into_code():
    from backend.services.activity_structuring import structure_activity

    source = (
        "class S:\n    def f(self):\n        try:\n            a()\n"
        "        except ValueError:\n            b()\n        finally:\n            c()\n"
    )
    flow = reverse_service.source_to_control_flows(source, "python")[0].control_flow
    assert structure_activity(flow)
