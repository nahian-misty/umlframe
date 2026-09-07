import pytest

from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size
from backend.services.activity_structuring import IRAction, IRIf, IRWhile, structure_activity

_POS = Position(x=0, y=0)
_SIZE = Size(width=160, height=80)


def _node(node_id: str, node_type: ActivityNodeType, label: str = "") -> ActivityNode:
    return ActivityNode(id=node_id, type=node_type, label=label, position=_POS, size=_SIZE)


def _edge(edge_id: str, source: str, target: str, label: str = "") -> ActivityEdge:
    return ActivityEdge(id=edge_id, source=source, target=target, label=label)


# ---------------------------------------------------------------------------
# Supported shapes
# ---------------------------------------------------------------------------


def test_straight_line_sequence():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.ACTION, "do work"),
            _node("n3", ActivityNodeType.END),
        ],
        edges=[_edge("e1", "n1", "n2"), _edge("e2", "n2", "n3")],
    )
    ir = structure_activity(doc)
    assert ir == [IRAction(label="do work")]


def test_if_else_both_branches_converge_at_shared_end():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.DECISION, "x > 0"),
            _node("n3", ActivityNodeType.ACTION, "positive branch"),
            _node("n4", ActivityNodeType.ACTION, "negative branch"),
            _node("n5", ActivityNodeType.END),
        ],
        edges=[
            _edge("e1", "n1", "n2"),
            _edge("e2", "n2", "n3", "yes"),
            _edge("e3", "n2", "n4", "no"),
            _edge("e4", "n3", "n5"),
            _edge("e5", "n4", "n5"),
        ],
    )
    ir = structure_activity(doc)
    assert ir == [
        IRIf(
            condition_label="x > 0",
            then_body=[IRAction(label="positive branch")],
            else_body=[IRAction(label="negative branch")],
        )
    ]


def test_if_without_else_reconverges_and_continues_sequence():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.DECISION, "x > 0"),
            _node("n3", ActivityNodeType.ACTION, "double x"),
            _node("n4", ActivityNodeType.ACTION, "return x"),
            _node("n5", ActivityNodeType.END),
        ],
        edges=[
            _edge("e1", "n1", "n2"),
            _edge("e2", "n2", "n3", "yes"),
            _edge("e3", "n2", "n4", "no"),  # empty else -> straight to the merge node
            _edge("e4", "n3", "n4"),
            _edge("e5", "n4", "n5"),
        ],
    )
    ir = structure_activity(doc)
    assert ir == [
        IRIf(condition_label="x > 0", then_body=[IRAction(label="double x")], else_body=[]),
        IRAction(label="return x"),
    ]


def test_while_loop_back_edge_into_decision():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.DECISION, "n > 0"),
            _node("n3", ActivityNodeType.ACTION, "n -= 1"),
            _node("n4", ActivityNodeType.END),
        ],
        edges=[
            _edge("e1", "n1", "n2"),
            _edge("e2", "n2", "n3", "yes"),
            _edge("e3", "n3", "n2"),
            _edge("e4", "n2", "n4", "no"),
        ],
    )
    ir = structure_activity(doc)
    assert ir == [IRWhile(condition_label="n > 0", body=[IRAction(label="n -= 1")])]


def test_nested_if_inside_while_body():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.DECISION, "n > 0"),
            _node("n3", ActivityNodeType.DECISION, "n % 2 == 0"),
            _node("n4", ActivityNodeType.ACTION, "halve n"),
            _node("n5", ActivityNodeType.ACTION, "decrement n"),
            _node("n6", ActivityNodeType.END),
        ],
        edges=[
            _edge("e1", "n1", "n2"),
            _edge("e2", "n2", "n3", "yes"),
            _edge("e3", "n3", "n4", "yes"),
            _edge("e4", "n3", "n5", "no"),
            _edge("e5", "n4", "n2"),
            _edge("e6", "n5", "n2"),
            _edge("e7", "n2", "n6", "no"),
        ],
    )
    ir = structure_activity(doc)
    assert len(ir) == 1
    loop = ir[0]
    assert isinstance(loop, IRWhile)
    assert loop.condition_label == "n > 0"
    assert loop.body == [
        IRIf(
            condition_label="n % 2 == 0",
            then_body=[IRAction(label="halve n")],
            else_body=[IRAction(label="decrement n")],
        )
    ]


def test_multiple_end_nodes_that_still_converge_upstream():
    """Both branches pass through a shared action before reaching their own
    END nodes -- the nearest common node (the shared action) is the correct
    reconvergence point, not either END."""
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.DECISION, "x > 0"),
            _node("n3", ActivityNodeType.ACTION, "log positive"),
            _node("n4", ActivityNodeType.ACTION, "log negative"),
            _node("n5", ActivityNodeType.ACTION, "cleanup"),
            _node("n6", ActivityNodeType.END),
        ],
        edges=[
            _edge("e1", "n1", "n2"),
            _edge("e2", "n2", "n3", "yes"),
            _edge("e3", "n2", "n4", "no"),
            _edge("e4", "n3", "n5"),
            _edge("e5", "n4", "n5"),
            _edge("e6", "n5", "n6"),
        ],
    )
    ir = structure_activity(doc)
    assert ir == [
        IRIf(
            condition_label="x > 0",
            then_body=[IRAction(label="log positive")],
            else_body=[IRAction(label="log negative")],
        ),
        IRAction(label="cleanup"),
    ]


# ---------------------------------------------------------------------------
# Unsupported shapes -- each must raise ValueError, never produce wrong IR
# ---------------------------------------------------------------------------


def test_fork_node_present_raises():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.FORK),
            _node("n3", ActivityNodeType.END),
        ],
        edges=[_edge("e1", "n1", "n2"), _edge("e2", "n2", "n3")],
    )
    with pytest.raises(ValueError, match="fork/join"):
        structure_activity(doc)


def test_join_node_present_raises():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.JOIN),
            _node("n3", ActivityNodeType.END),
        ],
        edges=[_edge("e1", "n1", "n2"), _edge("e2", "n2", "n3")],
    )
    with pytest.raises(ValueError, match="fork/join"):
        structure_activity(doc)


def test_decision_with_three_outgoing_edges_raises():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.DECISION, "x"),
            _node("n3", ActivityNodeType.END),
            _node("n4", ActivityNodeType.END),
            _node("n5", ActivityNodeType.END),
        ],
        edges=[
            _edge("e1", "n1", "n2"),
            _edge("e2", "n2", "n3"),
            _edge("e3", "n2", "n4"),
            _edge("e4", "n2", "n5"),
        ],
    )
    with pytest.raises(ValueError, match="exactly 2 outgoing edges"):
        structure_activity(doc)


def test_decision_with_one_outgoing_edge_raises():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.DECISION, "x"),
            _node("n3", ActivityNodeType.END),
        ],
        edges=[_edge("e1", "n1", "n2"), _edge("e2", "n2", "n3")],
    )
    with pytest.raises(ValueError, match="exactly 2 outgoing edges"):
        structure_activity(doc)


def test_no_reconvergence_point_raises():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.DECISION, "x"),
            _node("n3", ActivityNodeType.END),
            _node("n4", ActivityNodeType.END),
        ],
        edges=[_edge("e1", "n1", "n2"), _edge("e2", "n2", "n3", "yes"), _edge("e3", "n2", "n4", "no")],
    )
    with pytest.raises(ValueError, match="no reconvergence point"):
        structure_activity(doc)


def test_both_branches_loop_back_raises():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.DECISION, "x"),
            _node("n3", ActivityNodeType.ACTION, "a"),
            _node("n4", ActivityNodeType.ACTION, "b"),
            _node("n5", ActivityNodeType.END),  # unreachable, but satisfies "at least one END"
        ],
        edges=[
            _edge("e1", "n1", "n2"),
            _edge("e2", "n2", "n3", "yes"),
            _edge("e3", "n2", "n4", "no"),
            _edge("e4", "n3", "n2"),
            _edge("e5", "n4", "n2"),
        ],
    )
    with pytest.raises(ValueError, match="back edge on both branches"):
        structure_activity(doc)


def test_action_with_two_outgoing_edges_raises():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.ACTION, "a"),
            _node("n3", ActivityNodeType.END),
            _node("n4", ActivityNodeType.END),
        ],
        edges=[_edge("e1", "n1", "n2"), _edge("e2", "n2", "n3"), _edge("e3", "n2", "n4")],
    )
    with pytest.raises(ValueError, match="exactly one outgoing edge"):
        structure_activity(doc)


def test_action_with_no_outgoing_edge_raises():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.ACTION, "dead end"),
            _node("n3", ActivityNodeType.END),
        ],
        edges=[_edge("e1", "n1", "n2")],
    )
    with pytest.raises(ValueError, match="exactly one outgoing edge"):
        structure_activity(doc)
