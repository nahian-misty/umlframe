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
