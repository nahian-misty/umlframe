import pytest

from backend.reverse.python.parser import extract_control_flow
from backend.schemas.activity import ActivityNodeType


def _nodes_by_type(doc, node_type):
    return [n for n in doc.nodes if n.type == node_type]


def _edge(doc, source_id, target_id):
    return next(e for e in doc.edges if e.source == source_id and e.target == target_id)


def test_straight_line_method_collapses_to_one_action_node():
    source = """
class Calc:
    def run(self, x):
        y = x + 1
        z = y * 2
        return z
"""
    doc = extract_control_flow(source, "Calc", "run")
    actions = _nodes_by_type(doc, ActivityNodeType.ACTION)
    assert len(actions) == 1
    assert actions[0].label == "y = x + 1; z = y * 2; return z"
    start = _nodes_by_type(doc, ActivityNodeType.START)[0]
    end = _nodes_by_type(doc, ActivityNodeType.END)[0]
    assert _edge(doc, start.id, actions[0].id)
    assert _edge(doc, actions[0].id, end.id)


def test_empty_method_body_connects_start_directly_to_end():
    source = """
class Calc:
    def noop(self):
        pass
"""
    doc = extract_control_flow(source, "Calc", "noop")
    actions = _nodes_by_type(doc, ActivityNodeType.ACTION)
    assert len(actions) == 1  # `pass` still renders as a statement, not skipped
    assert actions[0].label == "pass"


def test_docstring_only_body_skips_docstring_and_connects_directly():
    source = '''
class Calc:
    def noop(self):
        """Does nothing."""
'''
    doc = extract_control_flow(source, "Calc", "noop")
    assert _nodes_by_type(doc, ActivityNodeType.ACTION) == []
    start = _nodes_by_type(doc, ActivityNodeType.START)[0]
    end = _nodes_by_type(doc, ActivityNodeType.END)[0]
    assert _edge(doc, start.id, end.id)


def test_if_else_both_branches_return():
    source = """
class Calc:
    def classify(self, x):
        if x > 0:
            return "positive"
        else:
            return "non-positive"
"""
    doc = extract_control_flow(source, "Calc", "classify")
    decisions = _nodes_by_type(doc, ActivityNodeType.DECISION)
    assert len(decisions) == 1
    assert decisions[0].label == "x > 0"

    yes_edge = next(e for e in doc.edges if e.source == decisions[0].id and e.label == "yes")
    no_edge = next(e for e in doc.edges if e.source == decisions[0].id and e.label == "no")
    end = _nodes_by_type(doc, ActivityNodeType.END)[0]
    assert _edge(doc, yes_edge.target, end.id)
    assert _edge(doc, no_edge.target, end.id)


def test_if_without_else_reconverges_after_branch():
    source = """
class Calc:
    def maybe_double(self, x):
        if x > 0:
            x = x * 2
        return x
"""
    doc = extract_control_flow(source, "Calc", "maybe_double")
    decision = _nodes_by_type(doc, ActivityNodeType.DECISION)[0]
    actions = _nodes_by_type(doc, ActivityNodeType.ACTION)
    assert len(actions) == 2  # "x = x * 2" and "return x"
    doubling = next(a for a in actions if "x * 2" in a.label)
    returning = next(a for a in actions if a.label == "return x")

    yes_edge = next(e for e in doc.edges if e.source == decision.id and e.label == "yes")
    no_edge = next(e for e in doc.edges if e.source == decision.id and e.label == "no")
    assert yes_edge.target == doubling.id
    assert no_edge.target == returning.id
    assert _edge(doc, doubling.id, returning.id)


def test_while_loop_has_back_edge_into_decision():
    source = """
class Calc:
    def countdown(self, n):
        while n > 0:
            n -= 1
        return n
"""
    doc = extract_control_flow(source, "Calc", "countdown")
    decision = _nodes_by_type(doc, ActivityNodeType.DECISION)[0]
    assert decision.label == "n > 0"

    yes_edge = next(e for e in doc.edges if e.source == decision.id and e.label == "yes")
    back_edges = [e for e in doc.edges if e.target == decision.id and e.source == yes_edge.target]
    assert len(back_edges) == 1  # body loops back into the decision, not onward


def test_for_loop_renders_as_decision_with_back_edge():
    source = """
class Calc:
    def total(self, items):
        result = 0
        for item in items:
            result += item
        return result
"""
    doc = extract_control_flow(source, "Calc", "total")
    decision = _nodes_by_type(doc, ActivityNodeType.DECISION)[0]
    assert decision.label == "for item in items"
    yes_edge = next(e for e in doc.edges if e.source == decision.id and e.label == "yes")
    assert any(e.source == yes_edge.target and e.target == decision.id for e in doc.edges)


def test_try_except_renders_as_single_opaque_action():
    source = """
class Calc:
    def safe_div(self, a, b):
        try:
            return a / b
        except ZeroDivisionError:
            return 0
"""
    doc = extract_control_flow(source, "Calc", "safe_div")
    actions = _nodes_by_type(doc, ActivityNodeType.ACTION)
    assert len(actions) == 1
    assert actions[0].label == "try"


def test_class_not_found_raises_value_error():
    with pytest.raises(ValueError, match="Class 'Nope' not found"):
        extract_control_flow("class Calc:\n    def run(self): pass\n", "Nope", "run")


def test_method_not_found_raises_value_error():
    with pytest.raises(ValueError, match="Method 'nope' not found"):
        extract_control_flow("class Calc:\n    def run(self): pass\n", "Calc", "nope")


def test_invalid_syntax_raises_value_error():
    with pytest.raises(ValueError):
        extract_control_flow("def foo(:\n    pass\n", "Calc", "run")
