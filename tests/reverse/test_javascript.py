from pathlib import Path

import pytest

from backend.reverse.javascript.parser import parse
from backend.schemas.uml import RelationshipType, UmlClass, UmlDocument, Visibility

FIXTURES = Path(__file__).parent.parent / "fixtures" / "javascript"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


def _cls(doc: UmlDocument, name: str) -> UmlClass:
    return next(c for c in doc.classes if c.name == name)


def _attr(cls: UmlClass, name: str):
    return next(a for a in cls.attributes if a.name == name)


def _method(cls: UmlClass, name: str):
    return next(m for m in cls.methods if m.name == name)


def _rels(doc: UmlDocument, source: UmlClass, dest: UmlClass, rel_type: RelationshipType):
    return [
        r
        for r in doc.relationships
        if r.source == source.id and r.destination == dest.id and r.type == rel_type
    ]


# ---------------------------------------------------------------------------
# Attributes, methods, visibility
# ---------------------------------------------------------------------------


def test_simple_class_attributes_from_constructor():
    doc = parse(_load("simple_class.js"))
    user = _cls(doc, "User")

    email = _attr(user, "email")
    assert email.datatype == "any"
    assert email.visibility == Visibility.PUBLIC
    assert email.static is False

    token = _attr(user, "_token")
    assert token.visibility == Visibility.PRIVATE
    assert token.default_value == ""


def test_simple_class_methods_exclude_constructor():
    doc = parse(_load("simple_class.js"))
    user = _cls(doc, "User")
    method_names = {m.name for m in user.methods}
    assert "constructor" not in method_names

    login = _method(user, "login")
    assert login.static is False
    assert [p.name for p in login.parameters] == ["password"]
    assert login.return_type == "any"

    normalize = _method(user, "normalizeEmail")
    assert normalize.static is True
    assert normalize.visibility == Visibility.PUBLIC


def test_class_without_constructor_has_no_attributes():
    source = """
class Empty {
    doThing() {}
}
"""
    doc = parse(source)
    assert _cls(doc, "Empty").attributes == []


# ---------------------------------------------------------------------------
# Inheritance
# ---------------------------------------------------------------------------


def test_inheritance_edge_child_to_parent():
    doc = parse(_load("inheritance.js"))
    dog, animal = _cls(doc, "Dog"), _cls(doc, "Animal")
    edges = _rels(doc, dog, animal, RelationshipType.INHERITANCE)
    assert len(edges) == 1
    assert edges[0].multiplicity.source == "1"
    assert edges[0].multiplicity.destination == "1"


def test_unresolvable_superclass_is_skipped_not_errored():
    source = """
class Dog extends UnknownBase {
    bark() {}
}
"""
    doc = parse(source)
    assert doc.relationships == []


# ---------------------------------------------------------------------------
# Composition (the only relationship type JS's lack of static types allows
# this parser to infer -- see the scope note in backend/reverse/javascript/parser.py)
# ---------------------------------------------------------------------------


def test_composition_via_direct_instantiation():
    doc = parse(_load("composition.js"))
    car, engine = _cls(doc, "Car"), _cls(doc, "Engine")
    edges = _rels(doc, car, engine, RelationshipType.COMPOSITION)
    assert len(edges) == 1
    assert _attr(car, "engine").datatype == "Engine"


def test_param_passthrough_is_not_inferred_as_aggregation():
    # unlike Python/Java, JS has no static types, so `this.owner = owner` in
    # the constructor can't be proven to reference any particular class --
    # no relationship is fabricated for it.
    doc = parse(_load("composition.js"))
    car = _cls(doc, "Car")
    owner = _attr(car, "owner")
    assert owner.datatype == "any"
    assert doc.relationships == [r for r in doc.relationships if r.type != RelationshipType.AGGREGATION]


# ---------------------------------------------------------------------------
# Dedup, scoping limits, error handling
# ---------------------------------------------------------------------------


def test_relationship_dedup_same_type_same_pair_collapses_to_one_edge():
    source = """
class Wheel {
}

class Car {
    constructor() {
        this.wheel = new Wheel();
        this.spareWheel = new Wheel();
    }
}
"""
    doc = parse(source)
    assert len(doc.relationships) == 1
    assert doc.relationships[0].type == RelationshipType.COMPOSITION


def test_class_expression_is_not_discovered():
    source = """
const Inner = class {
};
"""
    doc = parse(source)
    assert doc.classes == []


def test_invalid_syntax_raises_value_error():
    with pytest.raises(ValueError):
        parse("class Foo {")


def test_empty_source_returns_empty_document():
    doc = parse("")
    assert doc.classes == []
    assert doc.relationships == []
