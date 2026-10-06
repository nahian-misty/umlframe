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


def test_single_parameter_passthrough_is_association_not_aggregation():
    doc = parse(_load("composition_aggregation.py"))
    car, person = _cls(doc, "Car"), _cls(doc, "Person")
    edges = _rels(doc, car, person, RelationshipType.ASSOCIATION)
    assert len(edges) == 1
    assert edges[0].multiplicity.destination == "1"
    assert _rels(doc, car, person, RelationshipType.AGGREGATION) == []


def test_many_multiplicity_from_list_annotation():
    doc = parse(_load("composition_aggregation.py"))
    car, wheel = _cls(doc, "Car"), _cls(doc, "Wheel")
    edges = _rels(doc, car, wheel, RelationshipType.AGGREGATION)
    assert len(edges) == 1
    assert edges[0].multiplicity.destination == "*"
    assert _attr(car, "wheels").datatype == "List[Wheel]"


def test_annotation_only_single_reference_is_association():
    source = """
class Manager:
    pass


class Department:
    def __init__(self) -> None:
        self.manager: Manager
"""
    doc = parse(source)
    department, manager = _cls(doc, "Department"), _cls(doc, "Manager")
    edges = _rels(doc, department, manager, RelationshipType.ASSOCIATION)
    assert len(edges) == 1
    assert _attr(department, "manager").default_value is None


# ---------------------------------------------------------------------------
# Association
# ---------------------------------------------------------------------------


def test_dependency_via_method_parameter_and_return_type():
    doc = parse(_load("association.py"))
    mechanic, car = _cls(doc, "Mechanic"), _cls(doc, "Car")
    edges = _rels(doc, mechanic, car, RelationshipType.DEPENDENCY)
    # same class referenced as both param and return type -> one edge, not two
    assert len(edges) == 1


def test_attribute_and_method_param_association_collapse_to_one_edge():
    doc = parse(_load("composition_aggregation.py"))
    car, person = _cls(doc, "Car"), _cls(doc, "Person")
    # register_owner(owner: Person) repeats the association the `owner` attribute already
    # gives, so there is still exactly one Car -> Person edge.
    assert len(_rels(doc, car, person, RelationshipType.ASSOCIATION)) == 1
    assert len(doc.relationships) == 3  # composition + association + aggregation(many) only


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
    assert doc.relationships[0].type == RelationshipType.ASSOCIATION


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


def test_annotated_param_passthrough_keeps_declared_type():
    doc = parse(
        "class User:\n"
        "    def __init__(self, name: str, age: int, tags: list[str]):\n"
        "        self.name = name\n"
        "        self.age = age\n"
        "        self.tags = tags\n"
    )
    types = {a.name: a.datatype for a in doc.classes[0].attributes}
    assert types == {"name": "String", "age": "int", "tags": "List[String]"}


def test_builtin_literals_and_calls_infer_types():
    doc = parse(
        "class Bag:\n"
        "    def __init__(self, thing):\n"
        "        self.items = []\n"
        "        self.index = {}\n"
        "        self.seen = set()\n"
        "        self.title = str(thing)\n"
        "        self.greeting = f'hi {thing}'\n"
        "        self.raw = thing\n"
    )
    types = {a.name: a.datatype for a in doc.classes[0].attributes}
    assert types == {
        "items": "List",
        "index": "Map",
        "seen": "Set",
        "title": "String",
        "greeting": "String",
        "raw": "object",
    }


def test_optional_union_annotation_maps_inner_type():
    doc = parse(
        "class A:\n"
        "    def __init__(self, nick: str | None):\n"
        "        self.nick = nick\n"
    )
    assert doc.classes[0].attributes[0].datatype == "String | None"


def test_car_driver_wheels_engine_relationship_kinds():
    doc = parse(
        "class Engine:\n    pass\n\nclass Wheel:\n    pass\n\nclass Driver:\n    pass\n\n"
        "class Car:\n"
        "    def __init__(self, driver: Driver, wheels: list[Wheel]):\n"
        "        self.engine = Engine()\n"
        "        self.driver = driver\n"
        "        self.wheels = wheels\n"
    )
    names = {c.id: c.name for c in doc.classes}
    kinds = {(names[r.destination], r.type) for r in doc.relationships}
    assert kinds == {
        ("Engine", RelationshipType.COMPOSITION),
        ("Driver", RelationshipType.ASSOCIATION),
        ("Wheel", RelationshipType.AGGREGATION),
    }


def test_abc_with_abstract_method_and_state_is_an_abstract_class():
    source = """
from abc import ABC, abstractmethod

class Shape(ABC):
    def __init__(self):
        self.name = "shape"

    @abstractmethod
    def area(self) -> float:
        ...
"""
    assert parse(source).classes[0].kind.value == "abstract"


def test_abc_with_only_abstract_methods_is_an_interface():
    source = """
from abc import ABC, abstractmethod

class Owner(ABC):
    @abstractmethod
    def acquire(self, item): ...

    @abstractmethod
    def dispose(self, item): ...
"""
    assert parse(source).classes[0].kind.value == "interface"


def test_protocol_is_an_interface():
    source = """
from typing import Protocol

class Closeable(Protocol):
    def close(self) -> None: ...
"""
    assert parse(source).classes[0].kind.value == "interface"


def test_plain_class_stays_a_class():
    assert parse("class Plain:\n    pass\n").classes[0].kind.value == "class"


def test_class_deriving_from_an_interface_realizes_it():
    source = """
from abc import ABC, abstractmethod

class Owner(ABC):
    @abstractmethod
    def acquire(self, item): ...

class Person(Owner):
    def acquire(self, item):
        return item
"""
    doc = parse(source)
    ids = {c.name: c.id for c in doc.classes}
    assert [(r.source, r.destination, r.type.value) for r in doc.relationships] == [
        (ids["Person"], ids["Owner"], "realization")
    ]


# ---------------------------------------------------------------------------
# Type inference without annotations, attributes outside __init__, collections
# ---------------------------------------------------------------------------

LIBRARY = '''
from dataclasses import dataclass

class Book:
    def __init__(self, title, pages=100):
        self.title = title
        self.pages = pages
        self.available = True

    def describe(self):
        return "Book: " + self.title

    def is_long(self):
        return self.pages > 300

class Member:
    pass

class Loan:
    def __init__(self, book, member):
        self.book = book

class Library:
    def __init__(self, name: str):
        self.name = name
        self.books = []
        self.loans = [Loan(None, None)]

    def add_book(self, book: Book):
        self.books.append(book)
        self.size = len(self.books)

    def lend(self, member: Member, book: Book):
        loan = Loan(book, member)
        return loan

    def total(self):
        return len(self.books)

    def nothing(self):
        pass

@dataclass
class Point:
    x: int
    y: int = 0
'''


def test_unannotated_attribute_types_come_from_defaults_and_literals():
    book = _cls(parse(LIBRARY), "Book")
    assert _attr(book, "pages").datatype == "int"  # default value 100
    assert _attr(book, "available").datatype == "bool"


def test_unannotated_return_types_are_inferred_from_return_statements():
    doc = parse(LIBRARY)
    book, library = _cls(doc, "Book"), _cls(doc, "Library")
    assert _method(book, "describe").return_type == "String"
    assert _method(book, "is_long").return_type == "bool"
    assert _method(library, "total").return_type == "int"
    assert _method(library, "lend").return_type == "Loan"  # a local built from Loan(...)
    assert _method(library, "nothing").return_type == "void"


def test_append_of_an_annotated_parameter_makes_a_collection_aggregation():
    doc = parse(LIBRARY)
    library, book = _cls(doc, "Library"), _cls(doc, "Book")
    edges = _rels(doc, library, book, RelationshipType.AGGREGATION)
    assert len(edges) == 1 and edges[0].multiplicity.destination == "*"
    assert _attr(library, "books").datatype == "List[Book]"


def test_list_of_new_instances_is_a_composition_collection():
    doc = parse(LIBRARY)
    edges = _rels(doc, _cls(doc, "Library"), _cls(doc, "Loan"), RelationshipType.COMPOSITION)
    assert len(edges) == 1 and edges[0].multiplicity.destination == "*"


def test_attribute_assigned_in_another_method_is_found():
    assert _attr(_cls(parse(LIBRARY), "Library"), "size").datatype == "int"


def test_method_parameter_not_held_is_a_dependency():
    doc = parse(LIBRARY)
    assert len(_rels(doc, _cls(doc, "Library"), _cls(doc, "Member"), RelationshipType.DEPENDENCY)) == 1


def test_dataclass_fields_are_instance_attributes_not_static():
    point = _cls(parse(LIBRARY), "Point")
    assert [(a.name, a.datatype, a.static) for a in point.attributes] == [
        ("x", "int", False),
        ("y", "int", False),
    ]


def test_class_level_declaration_and_self_assignment_are_one_attribute():
    source = "class P:\n    name: str\n    def __init__(self, name: str):\n        self.name = name\n"
    assert [a.name for a in _cls(parse(source), "P").attributes] == ["name"]


def test_qualified_and_generic_bases_are_inheritance():
    source = "class A: pass\nclass B(mod.A): pass\nclass C(Generic[T], A): pass\n"
    doc = parse(source)
    a = _cls(doc, "A")
    assert len(_rels(doc, _cls(doc, "B"), a, RelationshipType.INHERITANCE)) == 1
    assert len(_rels(doc, _cls(doc, "C"), a, RelationshipType.INHERITANCE)) == 1


# ---------------------------------------------------------------------------
# Untyped code: parameter names are the last-resort type hint
# ---------------------------------------------------------------------------

UNTYPED = '''
class Teacher:
    def __init__(self, name):
        self.name = name

class Professor:
    pass

class Student:
    def __init__(self, name, teacher, is_active, home_address):
        self.name = name
        self.teacher = teacher
        self.is_active = is_active
        self.home_address = home_address

class Department:
    def __init__(self, name, professors):
        self.name = name
        self.professors = professors
'''


def test_untyped_parameter_named_after_a_class_is_an_association():
    doc = parse(UNTYPED)
    student, teacher = _cls(doc, "Student"), _cls(doc, "Teacher")
    assert _attr(student, "teacher").datatype == "Teacher"
    assert len(_rels(doc, student, teacher, RelationshipType.ASSOCIATION)) == 1


def test_untyped_plural_parameter_is_an_aggregated_collection():
    doc = parse(UNTYPED)
    department, professor = _cls(doc, "Department"), _cls(doc, "Professor")
    assert _attr(department, "professors").datatype == "List[Professor]"
    edges = _rels(doc, department, professor, RelationshipType.AGGREGATION)
    assert len(edges) == 1 and edges[0].multiplicity.destination == "*"


def test_untyped_common_names_get_plain_types_instead_of_object():
    student = _cls(parse(UNTYPED), "Student")
    assert _attr(student, "name").datatype == "String"
    assert _attr(student, "is_active").datatype == "bool"
    assert _attr(student, "home_address").datatype == "String"


def test_unrecognised_untyped_parameter_stays_object():
    source = "class A:\n    def __init__(self, thing):\n        self.thing = thing\n"
    assert _attr(_cls(parse(source), "A"), "thing").datatype == "object"


def test_collection_filled_with_locally_created_instances_is_composition_many():
    source = """
class CartItem:
    pass

class ShoppingCart:
    def __init__(self):
        self.items = []

    def add_product(self, product):
        item = CartItem(product)
        self.items.append(item)
"""
    doc = parse(source)
    cart, item = _cls(doc, "ShoppingCart"), _cls(doc, "CartItem")
    edges = _rels(doc, cart, item, RelationshipType.COMPOSITION)
    assert len(edges) == 1 and edges[0].multiplicity.destination == "*"
    assert _attr(cart, "items").datatype == "List[CartItem]"


def test_appending_an_unannotated_parameter_is_not_composition():
    source = """
class CartItem:
    pass

class ShoppingCart:
    def __init__(self):
        self.items = []

    def add(self, item):
        self.items.append(item)
"""
    doc = parse(source)
    assert not [r for r in doc.relationships if r.type == RelationshipType.COMPOSITION]
