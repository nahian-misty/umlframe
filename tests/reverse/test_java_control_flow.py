import pytest

from backend.reverse.java.parser import extract_control_flow
from backend.schemas.activity import ActivityNodeType


def _nodes_by_type(doc, node_type):
    return [n for n in doc.nodes if n.type == node_type]

def _flow(doc):
    """The diagram as {(source label, edge label, target label)}; START/END are named."""
    names = {n.id: n.label or n.type.value for n in doc.nodes}
    return {(names[e.source], e.label, names[e.target]) for e in doc.edges}



def _edge(doc, source_id, target_id):
    return next(e for e in doc.edges if e.source == source_id and e.target == target_id)


def test_straight_line_method_collapses_to_one_action_node():
    source = """
public class Calc {
    public int run(int x) {
        int y = x + 1;
        int z = y * 2;
        return z;
    }
}
"""
    doc = extract_control_flow(source, "Calc", "run")
    actions = _nodes_by_type(doc, ActivityNodeType.ACTION)
    assert len(actions) == 1
    assert actions[0].label == "Calculate y; Calculate z; Return z"
    start = _nodes_by_type(doc, ActivityNodeType.START)[0]
    end = _nodes_by_type(doc, ActivityNodeType.END)[0]
    assert _edge(doc, start.id, actions[0].id)
    assert _edge(doc, actions[0].id, end.id)


def test_if_else_both_branches_return():
    source = """
public class Calc {
    public String classify(int x) {
        if (x > 0) {
            return "positive";
        } else {
            return "non-positive";
        }
    }
}
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
public class Calc {
    public int maybeDouble(int x) {
        if (x > 0) {
            x = x * 2;
        }
        return x;
    }
}
"""
    doc = extract_control_flow(source, "Calc", "maybeDouble")
    decision = _nodes_by_type(doc, ActivityNodeType.DECISION)[0]
    actions = _nodes_by_type(doc, ActivityNodeType.ACTION)
    assert len(actions) == 2
    doubling = next(a for a in actions if a.label == "Calculate x")
    returning = next(a for a in actions if a.label == "Return x")

    yes_edge = next(e for e in doc.edges if e.source == decision.id and e.label == "yes")
    no_edge = next(e for e in doc.edges if e.source == decision.id and e.label == "no")
    assert yes_edge.target == doubling.id
    assert no_edge.target == returning.id
    assert _edge(doc, doubling.id, returning.id)


def test_while_loop_has_back_edge_into_decision():
    source = """
public class Calc {
    public int countdown(int n) {
        while (n > 0) {
            n = n - 1;
        }
        return n;
    }
}
"""
    doc = extract_control_flow(source, "Calc", "countdown")
    decision = _nodes_by_type(doc, ActivityNodeType.DECISION)[0]
    assert decision.label == "n > 0"
    yes_edge = next(e for e in doc.edges if e.source == decision.id and e.label == "yes")
    assert any(e.source == yes_edge.target and e.target == decision.id for e in doc.edges)


def test_for_loop_renders_as_decision_with_back_edge():
    source = """
public class Calc {
    public int total(int[] items) {
        int result = 0;
        for (int i = 0; i < items.length; i++) {
            result = result + items[i];
        }
        return result;
    }
}
"""
    doc = extract_control_flow(source, "Calc", "total")
    decision = _nodes_by_type(doc, ActivityNodeType.DECISION)[0]
    yes_edge = next(e for e in doc.edges if e.source == decision.id and e.label == "yes")
    assert any(e.source == yes_edge.target and e.target == decision.id for e in doc.edges)


def test_try_catch_branches_on_the_exception_instead_of_one_opaque_action():
    source = """
public class Calc {
    public int safeDiv(int a, int b) {
        try {
            return a / b;
        } catch (ArithmeticException e) {
            return 0;
        }
    }
}
"""
    doc = extract_control_flow(source, "Calc", "safeDiv")
    assert _flow(doc) == {
        ("start", "", "catch ArithmeticException?"),
        ("catch ArithmeticException?", "yes", "Return 0"),
        ("catch ArithmeticException?", "no", "Return result"),
        ("Return 0", "", "end"),
        ("Return result", "", "end"),
    }


def test_try_multi_catch_finally_chains_handlers_and_merges_into_finally():
    source = """
class S {
    void f() {
        try { a(); }
        catch (IOException e) { b(); }
        catch (RuntimeException e) { c(); }
        finally { d(); }
        e();
    }
}
"""
    assert _flow(extract_control_flow(source, "S", "f")) == {
        ("start", "", "exception thrown?"),
        ("exception thrown?", "yes", "catch IOException?"),
        ("exception thrown?", "no", "A"),
        ("catch IOException?", "yes", "B"),
        ("catch IOException?", "no", "catch RuntimeException?"),
        ("catch RuntimeException?", "yes", "C"),
        ("catch RuntimeException?", "no", "finally"),
        ("A", "", "finally"),
        ("B", "", "finally"),
        ("C", "", "finally"),
        ("finally", "", "D"),
        ("D", "", "E"),
        ("E", "", "end"),
    }


def test_class_not_found_raises_value_error():
    source = "public class Calc { public void run() {} }"
    with pytest.raises(ValueError, match="Class 'Nope' not found"):
        extract_control_flow(source, "Nope", "run")


def test_method_not_found_raises_value_error():
    source = "public class Calc { public void run() {} }"
    with pytest.raises(ValueError, match="Method 'nope' not found"):
        extract_control_flow(source, "Calc", "nope")


def test_abstract_method_raises_value_error():
    source = "public abstract class Calc { public abstract void run(); }"
    with pytest.raises(ValueError, match="not found"):
        extract_control_flow(source, "Calc", "run")


def test_invalid_syntax_raises_value_error():
    with pytest.raises(ValueError):
        extract_control_flow("public class Calc { public void run( }", "Calc", "run")


def test_list_methods_skips_abstract_and_constructors():
    from backend.reverse.java.parser import list_methods

    source = (
        "abstract class Shape {\n  Shape() {}\n  abstract double area();\n"
        "  void draw() { }\n  void draw(int x) { }\n}\n"
        "class Circle extends Shape {\n  double area() { return 1; }\n}\n"
    )
    assert list_methods(source) == [("Shape", "draw"), ("Circle", "area")]
