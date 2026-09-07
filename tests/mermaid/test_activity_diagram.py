from backend.mermaid.activity_diagram import document_to_activity_diagram
from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size

_POS = Position(x=0, y=0)
_SIZE = Size(width=160, height=80)


def _node(node_id: str, node_type: ActivityNodeType, label: str = "") -> ActivityNode:
    return ActivityNode(id=node_id, type=node_type, label=label, position=_POS, size=_SIZE)


def test_start_and_end_render_as_circles_with_default_labels():
    doc = ActivityDocument(
        nodes=[_node("n1", ActivityNodeType.START), _node("n2", ActivityNodeType.END)],
        edges=[ActivityEdge(id="e1", source="n1", target="n2")],
    )
    diagram = document_to_activity_diagram(doc)
    assert diagram.startswith("flowchart TD")
    assert 'n1(("Start"))' in diagram
    assert 'n2(("End"))' in diagram
    assert "n1 --> n2" in diagram


def test_action_renders_as_rectangle():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.ACTION, "do work"),
            _node("n3", ActivityNodeType.END),
        ],
        edges=[ActivityEdge(id="e1", source="n1", target="n2"), ActivityEdge(id="e2", source="n2", target="n3")],
    )
    diagram = document_to_activity_diagram(doc)
    assert 'n2["do work"]' in diagram


def test_decision_renders_as_diamond_with_labeled_edges():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.DECISION, "x > 0"),
            _node("n3", ActivityNodeType.END),
            _node("n4", ActivityNodeType.END),
        ],
        edges=[
            ActivityEdge(id="e1", source="n1", target="n2"),
            ActivityEdge(id="e2", source="n2", target="n3", label="yes"),
            ActivityEdge(id="e3", source="n2", target="n4", label="no"),
        ],
    )
    diagram = document_to_activity_diagram(doc)
    assert 'n2{"x > 0"}' in diagram
    assert 'n2 -->|"yes"| n3' in diagram
    assert 'n2 -->|"no"| n4' in diagram


def test_fork_and_join_render_as_subroutine_shape_with_default_labels():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.FORK),
            _node("n3", ActivityNodeType.JOIN),
            _node("n4", ActivityNodeType.END),
        ],
        edges=[
            ActivityEdge(id="e1", source="n1", target="n2"),
            ActivityEdge(id="e2", source="n2", target="n3"),
            ActivityEdge(id="e3", source="n3", target="n4"),
        ],
    )
    diagram = document_to_activity_diagram(doc)
    assert 'n2[["fork"]]' in diagram
    assert 'n3[["join"]]' in diagram


def test_quotes_in_labels_are_escaped():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.ACTION, 'say "hi"'),
            _node("n3", ActivityNodeType.END),
        ],
        edges=[ActivityEdge(id="e1", source="n1", target="n2"), ActivityEdge(id="e2", source="n2", target="n3")],
    )
    diagram = document_to_activity_diagram(doc)
    assert "say 'hi'" in diagram
    assert '"say "hi""' not in diagram
