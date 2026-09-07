from pathlib import Path

import pytest

from backend.reverse.java.parser import parse
from backend.schemas.uml import RelationshipType, UmlClass, UmlDocument, Visibility

FIXTURES = Path(__file__).parent.parent / "fixtures" / "java"


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
# Attributes, methods, visibility, static/final
# ---------------------------------------------------------------------------


def test_simple_class_attributes():
    doc = parse(_load("simple_class.java"))
    user = _cls(doc, "User")

    max_attempts = _attr(user, "MAX_LOGIN_ATTEMPTS")
    assert max_attempts.datatype == "int"
    assert max_attempts.visibility == Visibility.PUBLIC
    assert max_attempts.static is True
    assert max_attempts.final is True
    assert max_attempts.default_value == "5"

    email = _attr(user, "email")
    assert email.datatype == "String"
    assert email.visibility == Visibility.PRIVATE
    assert email.static is False

    token = _attr(user, "token")
    assert token.visibility == Visibility.PROTECTED


def test_no_access_modifier_is_package_visibility():
    source = """
class Foo {
    int x;
}
"""
    doc = parse(source)
    assert _attr(_cls(doc, "Foo"), "x").visibility == Visibility.PACKAGE


def test_simple_class_methods_exclude_constructor():
    doc = parse(_load("simple_class.java"))
    user = _cls(doc, "User")
    method_names = {m.name for m in user.methods}
    assert "User" not in method_names

    normalize = _method(user, "normalizeEmail")
    assert normalize.static is True
    assert normalize.visibility == Visibility.PUBLIC
    assert [p.name for p in normalize.parameters] == ["email"]
    assert normalize.parameters[0].datatype == "String"
    assert normalize.return_type == "String"

    login = _method(user, "login")
    assert login.static is False
    assert [p.name for p in login.parameters] == ["password"]
    assert login.return_type == "bool"


def test_abstract_method_sets_abstract():
    source = """
abstract class Shape {
    public abstract double area();
}
"""
    doc = parse(source)
    shape = _cls(doc, "Shape")
    area = _method(shape, "area")
    assert area.abstract is True
    assert area.static is False


def test_method_without_body_is_abstract_even_without_keyword():
    # interfaces aren't tracked as classes, but an abstract class's
    # bodyless method (no `abstract` keyword required by javalang parsing)
    # should still be detected via a null body.
    source = """
abstract class Shape {
    abstract double area();
}
"""
    doc = parse(source)
    assert _method(_cls(doc, "Shape"), "area").abstract is True


def test_static_method_maps_to_static_true():
    source = """
class Factory {
    public static Factory make() {
        return null;
    }
}
"""
    doc = parse(source)
    factory = _cls(doc, "Factory")
    make = _method(factory, "make")
    assert make.static is True
    assert make.parameters == []
    assert make.return_type == "Factory"


# ---------------------------------------------------------------------------
# Inheritance
# ---------------------------------------------------------------------------


def test_inheritance_edge_child_to_parent():
    doc = parse(_load("inheritance.java"))
    dog, animal = _cls(doc, "Dog"), _cls(doc, "Animal")
    edges = _rels(doc, dog, animal, RelationshipType.INHERITANCE)
    assert len(edges) == 1
    assert edges[0].multiplicity.source == "1"
    assert edges[0].multiplicity.destination == "1"


def test_unresolvable_implements_is_skipped_not_errored():
    doc = parse(_load("inheritance.java"))
    # Dog implements UnknownMixin, which isn't a class defined in this file
    # (and interfaces aren't tracked as UML relationships at all) -> only the
    # Animal inheritance edge is emitted
    assert len(doc.relationships) == 1


def test_multiple_classes_each_get_their_own_edge():
    source = """
class A {
}

class B {
}

class C extends A {
}

class D extends B {
}
"""
    doc = parse(source)
    c, a = _cls(doc, "C"), _cls(doc, "A")
    d, b = _cls(doc, "D"), _cls(doc, "B")
    assert len(_rels(doc, c, a, RelationshipType.INHERITANCE)) == 1
    assert len(_rels(doc, d, b, RelationshipType.INHERITANCE)) == 1


# ---------------------------------------------------------------------------
# Aggregation / composition
# ---------------------------------------------------------------------------


def test_composition_via_direct_instantiation():
    doc = parse(_load("composition_aggregation.java"))
    car, engine = _cls(doc, "Car"), _cls(doc, "Engine")
    edges = _rels(doc, car, engine, RelationshipType.COMPOSITION)
    assert len(edges) == 1
    assert edges[0].multiplicity.destination == "1"


def test_aggregation_via_declared_field_not_instantiated():
    doc = parse(_load("composition_aggregation.java"))
    car, person = _cls(doc, "Car"), _cls(doc, "Person")
    edges = _rels(doc, car, person, RelationshipType.AGGREGATION)
    assert len(edges) == 1
    assert edges[0].multiplicity.destination == "1"


def test_many_multiplicity_from_list_field():
    doc = parse(_load("composition_aggregation.java"))
    car, wheel = _cls(doc, "Car"), _cls(doc, "Wheel")
    edges = _rels(doc, car, wheel, RelationshipType.AGGREGATION)
    assert len(edges) == 1
    assert edges[0].multiplicity.destination == "*"
    assert _attr(car, "wheels").datatype == "List[Wheel]"


# ---------------------------------------------------------------------------
# Association
# ---------------------------------------------------------------------------


def test_association_via_method_parameter_and_return_type():
    doc = parse(_load("association.java"))
    mechanic, car = _cls(doc, "Mechanic"), _cls(doc, "Car")
    edges = _rels(doc, mechanic, car, RelationshipType.ASSOCIATION)
    # same class referenced as both param and return type -> one edge, not two
    assert len(edges) == 1


def test_association_excluded_when_already_aggregated():
    doc = parse(_load("composition_aggregation.java"))
    car, person = _cls(doc, "Car"), _cls(doc, "Person")
    # registerOwner(Person owner) would otherwise imply association, but
    # Person is already owned via aggregation from the same source -> excluded
    assert _rels(doc, car, person, RelationshipType.ASSOCIATION) == []
    assert len(doc.relationships) == 3  # composition + aggregation + aggregation(many) only


# ---------------------------------------------------------------------------
# Dedup, scoping limits, error handling
# ---------------------------------------------------------------------------


def test_relationship_dedup_same_type_same_pair_collapses_to_one_edge():
    source = """
class Wheel {
}

class Car {
    private Wheel wheel;
    private Wheel spareWheel;

    public Car(Wheel spare) {
        this.wheel = spare;
        this.spareWheel = spare;
    }
}
"""
    doc = parse(source)
    assert len(doc.relationships) == 1
    assert doc.relationships[0].type == RelationshipType.AGGREGATION


def test_nested_class_is_not_discovered():
    source = """
class Outer {
    class Inner {
    }
}
"""
    doc = parse(source)
    assert [c.name for c in doc.classes] == ["Outer"]


def test_interface_is_not_discovered_as_a_class():
    source = """
interface Runnable {
    void run();
}

class Task implements Runnable {
    public void run() {
    }
}
"""
    doc = parse(source)
    assert [c.name for c in doc.classes] == ["Task"]


def test_invalid_syntax_raises_value_error():
    with pytest.raises(ValueError):
        parse("class Foo {")


def test_empty_source_returns_empty_document():
    doc = parse("")
    assert doc.classes == []
    assert doc.relationships == []
