import pytest

from backend.schemas.activity import ActivityDocument, ActivityEdge, ActivityNode, ActivityNodeType
from backend.schemas.uml import Position, Size
from backend.services.activity_codegen_service import generate_activity_code

_POS = Position(x=0, y=0)
_SIZE = Size(width=160, height=80)


def _node(node_id: str, node_type: ActivityNodeType, label: str = "") -> ActivityNode:
    return ActivityNode(id=node_id, type=node_type, label=label, position=_POS, size=_SIZE)


def _edge(edge_id: str, source: str, target: str, label: str = "") -> ActivityEdge:
    return ActivityEdge(id=edge_id, source=source, target=target, label=label)


_IF_ELSE_DOC = ActivityDocument(
    nodes=[
        _node("n1", ActivityNodeType.START),
        _node("n2", ActivityNodeType.DECISION, "x > 0"),
        _node("n3", ActivityNodeType.ACTION, "do positive"),
        _node("n4", ActivityNodeType.ACTION, "do negative"),
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

_WHILE_DOC = ActivityDocument(
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

_EMPTY_DOC = ActivityDocument(
    nodes=[_node("n1", ActivityNodeType.START), _node("n2", ActivityNodeType.END)],
    edges=[_edge("e1", "n1", "n2")],
)


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------


def test_python_if_else_placeholder_never_fabricates_condition():
    files = generate_activity_code(_IF_ELSE_DOC, "python", "classify")
    code = files["classify.py"]
    compile(code, "classify.py", "exec")
    assert "if True:  # x > 0" in code
    assert "# TODO: do positive" in code
    assert "# TODO: do negative" in code
    assert "x > 0" not in code.split("#")[0]  # never rendered as a real boolean expression


def test_python_while_defaults_to_false_not_true():
    files = generate_activity_code(_WHILE_DOC, "python", "countdown")
    code = files["countdown.py"]
    compile(code, "countdown.py", "exec")
    assert "while False:  # n > 0" in code


def test_python_empty_body_renders_pass():
    files = generate_activity_code(_EMPTY_DOC, "python", "noop")
    code = files["noop.py"]
    compile(code, "noop.py", "exec")
    assert "pass" in code


def test_python_filename_uses_function_name():
    files = generate_activity_code(_IF_ELSE_DOC, "python", "myFunc")
    assert set(files.keys()) == {"myFunc.py"}


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------


def test_java_if_else_placeholder_never_fabricates_condition():
    files = generate_activity_code(_IF_ELSE_DOC, "java", "Classify")
    code = files["Classify.java"]
    assert "if (true) {  // x > 0" in code
    assert "// TODO: do positive" in code
    assert "// TODO: do negative" in code


def test_java_while_uses_boxed_false_not_bare_literal():
    files = generate_activity_code(_WHILE_DOC, "java", "Countdown")
    code = files["Countdown.java"]
    # a bare `while (false)` literal fails javac's unreachable-statement check
    assert "while (Boolean.FALSE) {  // n > 0" in code
    assert "while (false)" not in code


def test_java_class_name_matches_filename():
    files = generate_activity_code(_IF_ELSE_DOC, "java", "Classify")
    assert "public class Classify {" in files["Classify.java"]
    assert set(files.keys()) == {"Classify.java"}


# ---------------------------------------------------------------------------
# JavaScript
# ---------------------------------------------------------------------------


def test_javascript_if_else_placeholder_never_fabricates_condition():
    files = generate_activity_code(_IF_ELSE_DOC, "javascript", "classify")
    code = files["classify.js"]
    assert "if (true) {  // x > 0" in code
    assert "// TODO: do positive" in code
    assert "// TODO: do negative" in code


def test_javascript_while_defaults_to_false():
    files = generate_activity_code(_WHILE_DOC, "javascript", "countdown")
    code = files["countdown.js"]
    assert "while (false) {  // n > 0" in code


def test_javascript_function_name_used_directly():
    files = generate_activity_code(_IF_ELSE_DOC, "javascript", "classify")
    assert "function classify() {" in files["classify.js"]


# ---------------------------------------------------------------------------
# Cross-cutting
# ---------------------------------------------------------------------------


def test_unsupported_language_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported language"):
        generate_activity_code(_IF_ELSE_DOC, "ruby", "classify")


def test_default_function_name_used_when_omitted():
    files = generate_activity_code(_EMPTY_DOC, "python")
    assert "generated_function.py" in files


def test_unsupported_shape_propagates_structuring_value_error():
    doc = ActivityDocument(
        nodes=[
            _node("n1", ActivityNodeType.START),
            _node("n2", ActivityNodeType.FORK),
            _node("n3", ActivityNodeType.END),
        ],
        edges=[_edge("e1", "n1", "n2"), _edge("e2", "n2", "n3")],
    )
    with pytest.raises(ValueError, match="fork/join"):
        generate_activity_code(doc, "python", "bad")
