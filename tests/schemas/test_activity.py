import pytest
from pydantic import ValidationError

from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size

_POS = Position(x=0, y=0)
_SIZE = Size(width=160, height=80)


def _node(node_id: str, node_type: ActivityNodeType, label: str = "") -> ActivityNode:
    return ActivityNode(id=node_id, type=node_type, label=label, position=_POS, size=_SIZE)


def test_minimal_valid_document():
    doc = ActivityDocument(
        nodes=[_node("n1", ActivityNodeType.START), _node("n2", ActivityNodeType.END)],
        edges=[ActivityEdge(id="e1", source="n1", target="n2")],
    )
    assert len(doc.nodes) == 2
    assert doc.edges[0].label == ""


def test_edge_referencing_unknown_source_raises():
    with pytest.raises(ValidationError):
        ActivityDocument(
            nodes=[_node("n1", ActivityNodeType.START), _node("n2", ActivityNodeType.END)],
            edges=[ActivityEdge(id="e1", source="ghost", target="n2")],
        )


def test_edge_referencing_unknown_target_raises():
    with pytest.raises(ValidationError):
        ActivityDocument(
            nodes=[_node("n1", ActivityNodeType.START), _node("n2", ActivityNodeType.END)],
            edges=[ActivityEdge(id="e1", source="n1", target="ghost")],
        )


def test_zero_start_nodes_raises():
    with pytest.raises(ValidationError):
        ActivityDocument(nodes=[_node("n1", ActivityNodeType.END)], edges=[])


def test_multiple_start_nodes_raises():
    with pytest.raises(ValidationError):
        ActivityDocument(
            nodes=[
                _node("n1", ActivityNodeType.START),
                _node("n2", ActivityNodeType.START),
                _node("n3", ActivityNodeType.END),
            ],
            edges=[],
        )


def test_no_end_nodes_raises():
    with pytest.raises(ValidationError):
        ActivityDocument(nodes=[_node("n1", ActivityNodeType.START)], edges=[])


def test_multiple_end_nodes_allowed():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.END),
            _node("n3", ActivityNodeType.END),
        ],
        edges=[ActivityEdge(id="e1", source="n1", target="n2"), ActivityEdge(id="e2", source="n1", target="n3")],
    )
    assert len(doc.nodes) == 3


def test_empty_document_raises_no_start():
    with pytest.raises(ValidationError):
        ActivityDocument(nodes=[], edges=[])


def test_all_node_types_constructible():
    for node_type in ActivityNodeType:
        _node("n1", node_type)  # no error


def test_decision_and_action_and_fork_join_nodes_allowed_alongside_start_end():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.DECISION, "x > 0"),
            _node("n3", ActivityNodeType.ACTION, "do work"),
            _node("n4", ActivityNodeType.FORK),
            _node("n5", ActivityNodeType.JOIN),
            _node("n6", ActivityNodeType.END),
        ],
        edges=[],
    )
    assert len(doc.nodes) == 6
