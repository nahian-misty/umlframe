from pathlib import Path

import pytest

from backend.reverse.python.parser import parse
from backend.schemas.uml import RelationshipType, UmlClass, UmlDocument, Visibility

FIXTURES = Path(__file__).parent.parent / "fixtures" / "python"


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
    doc = parse(_load("simple_class.py"))
    user = _cls(doc, "User")

    max_attempts = _attr(user, "MAX_LOGIN_ATTEMPTS")
    assert max_attempts.datatype == "int"
    assert max_attempts.visibility == Visibility.PUBLIC
    assert max_attempts.static is True
    assert max_attempts.final is True
    assert max_attempts.default_value == "5"

    email = _attr(user, "email")
    assert email.datatype == "String"
    assert email.visibility == Visibility.PUBLIC
    assert email.static is False

    token = _attr(user, "_token")
    assert token.visibility == Visibility.PROTECTED

    secret = _attr(user, "__secret")
    assert secret.visibility == Visibility.PRIVATE


def test_simple_class_methods_exclude_init():
    doc = parse(_load("simple_class.py"))
    user = _cls(doc, "User")
    method_names = {m.name for m in user.methods}
    assert "__init__" not in method_names

    normalize = _method(user, "normalize_email")
    assert normalize.static is True
    assert normalize.visibility == Visibility.PUBLIC
    assert [p.name for p in normalize.parameters] == ["email"]
    assert normalize.parameters[0].datatype == "String"
    assert normalize.return_type == "String"

    login = _method(user, "login")
    assert login.static is False
    assert [p.name for p in login.parameters] == ["password"]
    assert login.return_type == "bool"


def test_dunder_method_is_public_not_mangled_private():
    doc = parse(_load("simple_class.py"))
    user = _cls(doc, "User")
    eq_method = _method(user, "__eq__")
    assert eq_method.visibility == Visibility.PUBLIC
    assert eq_method.parameters[0].datatype == "Object"


def test_abstractmethod_decorator_sets_abstract():
    source = """
from abc import ABC, abstractmethod


class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        ...
"""
    doc = parse(source)
    shape = _cls(doc, "Shape")
    area = _method(shape, "area")
    assert area.abstract is True
    assert area.static is False
    # ABC is not a class defined in this file -> silently skipped, not fabricated
    assert doc.relationships == []


def test_raise_not_implemented_sets_abstract():
    source = """
class Base:
    def compute(self) -> int:
        raise NotImplementedError
"""
    doc = parse(source)
    base = _cls(doc, "Base")
    assert _method(base, "compute").abstract is True


def test_plain_stub_body_is_not_abstract():
    source = """
class Base:
    def compute(self) -> int:
        pass
"""
    doc = parse(source)
    assert _method(_cls(doc, "Base"), "compute").abstract is False


def test_classmethod_and_staticmethod_map_to_static_true():
    source = '''
class Factory:
    @staticmethod
    def make() -> "Factory":
        ...

    @classmethod
    def create(cls) -> "Factory":
        ...
'''
    doc = parse(source)
    factory = _cls(doc, "Factory")

    make = _method(factory, "make")
    assert make.static is True
    assert make.parameters == []
    assert make.return_type == "Factory"

    create = _method(factory, "create")
    assert create.static is True
    assert create.parameters == []  # cls dropped like self


# ---------------------------------------------------------------------------
# Inheritance
# ---------------------------------------------------------------------------


def test_inheritance_edge_child_to_parent():
    doc = parse(_load("inheritance.py"))
    dog, animal = _cls(doc, "Dog"), _cls(doc, "Animal")
    edges = _rels(doc, dog, animal, RelationshipType.INHERITANCE)
    assert len(edges) == 1
    assert edges[0].multiplicity.source == "1"
    assert edges[0].multiplicity.destination == "1"


def test_unresolvable_base_is_skipped_not_errored():
    doc = parse(_load("inheritance.py"))
    # Dog(Animal, UnknownMixin) -> only the Animal edge is emitted
    assert len(doc.relationships) == 1


def test_multiple_inheritance_emits_multiple_edges():
    source = """
class A:
    pass


class B:
    pass


class C(A, B):
    pass
"""
    doc = parse(source)
    c, a, b = _cls(doc, "C"), _cls(doc, "A"), _cls(doc, "B")
    assert len(_rels(doc, c, a, RelationshipType.INHERITANCE)) == 1
    assert len(_rels(doc, c, b, RelationshipType.INHERITANCE)) == 1


# ---------------------------------------------------------------------------
# Aggregation / composition
# ---------------------------------------------------------------------------


def test_composition_via_direct_instantiation():
    doc = parse(_load("composition_aggregation.py"))
    car, engine = _cls(doc, "Car"), _cls(doc, "Engine")
    edges = _rels(doc, car, engine, RelationshipType.COMPOSITION)
    assert len(edges) == 1
    assert edges[0].multiplicity.destination == "1"


def test_aggregation_via_parameter_passthrough():
    doc = parse(_load("composition_aggregation.py"))
    car, person = _cls(doc, "Car"), _cls(doc, "Person")
    edges = _rels(doc, car, person, RelationshipType.AGGREGATION)
    assert len(edges) == 1
    assert edges[0].multiplicity.destination == "1"


def test_many_multiplicity_from_list_annotation():
    doc = parse(_load("composition_aggregation.py"))
    car, wheel = _cls(doc, "Car"), _cls(doc, "Wheel")
    edges = _rels(doc, car, wheel, RelationshipType.AGGREGATION)
    assert len(edges) == 1
    assert edges[0].multiplicity.destination == "*"
    assert _attr(car, "wheels").datatype == "List[Wheel]"


def test_aggregation_via_annotation_only_no_instantiation():
    source = """
class Manager:
    pass


class Department:
    def __init__(self) -> None:
        self.manager: Manager
"""
    doc = parse(source)
    department, manager = _cls(doc, "Department"), _cls(doc, "Manager")
    edges = _rels(doc, department, manager, RelationshipType.AGGREGATION)
    assert len(edges) == 1
    assert _attr(department, "manager").default_value is None


# ---------------------------------------------------------------------------
# Association
# ---------------------------------------------------------------------------


def test_association_via_method_parameter_and_return_type():
    doc = parse(_load("association.py"))
    mechanic, car = _cls(doc, "Mechanic"), _cls(doc, "Car")
    edges = _rels(doc, mechanic, car, RelationshipType.ASSOCIATION)
    # same class referenced as both param and return type -> one edge, not two
    assert len(edges) == 1


def test_association_excluded_when_already_aggregated():
    doc = parse(_load("composition_aggregation.py"))
    car, person = _cls(doc, "Car"), _cls(doc, "Person")
    # register_owner(owner: Person) would otherwise imply association, but
    # Person is already owned via aggregation from the same source -> excluded
    assert _rels(doc, car, person, RelationshipType.ASSOCIATION) == []
    assert len(doc.relationships) == 3  # composition + aggregation + aggregation(many) only


# ---------------------------------------------------------------------------
# Dedup, scoping limits, error handling
# ---------------------------------------------------------------------------


def test_relationship_dedup_same_type_same_pair_collapses_to_one_edge():
    source = """
class Wheel:
    pass


class Car:
    def __init__(self, spare: Wheel) -> None:
        self.wheel: Wheel = spare
        self.spare_wheel: Wheel = spare
"""
    doc = parse(source)
    assert len(doc.relationships) == 1
    assert doc.relationships[0].type == RelationshipType.AGGREGATION


def test_nested_class_is_not_discovered():
    source = """
class Outer:
    def make(self):
        class Inner:
            pass
        return Inner()
"""
    doc = parse(source)
    assert [c.name for c in doc.classes] == ["Outer"]


def test_invalid_syntax_raises_value_error():
    with pytest.raises(ValueError):
        parse("def foo(:\n    pass\n")


def test_empty_source_returns_empty_document():
    doc = parse("")
    assert doc.classes == []
    assert doc.relationships == []
