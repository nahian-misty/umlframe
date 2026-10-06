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
    assert email.datatype == "String"  # no type info, but the name `email` says so
    assert email.visibility == Visibility.PUBLIC
    assert email.static is False

    token = _attr(user, "_token")
    assert token.visibility == Visibility.PRIVATE
    assert token.default_value == ""
    assert token.datatype == "String"  # inferred from the "" literal


def test_simple_class_methods_exclude_constructor():
    doc = parse(_load("simple_class.js"))
    user = _cls(doc, "User")
    method_names = {m.name for m in user.methods}
    assert "constructor" not in method_names

    login = _method(user, "login")
    assert login.static is False
    assert [p.name for p in login.parameters] == ["password"]
    assert login.return_type == "boolean"  # `return true`

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


# ---------------------------------------------------------------------------
# Type inference, JSDoc and relationships
# ---------------------------------------------------------------------------

LIBRARY = """
export class Library {
  /**
   * @param {string} name
   * @param {Book[]} books
   */
  constructor(name, books, max = 10) {
    this.name = name;
    this.books = books;
    this.max = max;
    this.ratio = 0.5;
    this.index = new Map();
    /** @type {Member} */
    this.curator = null;
    this.engine = new Engine();
  }
  /** @param {Member} member @returns {Loan} */
  lend(member, book) {
    this.loans = this.loans || [];
    return new Loan(member, book);
  }
  count() { return this.books.length; }
  describe() { return `Library ${this.name}`; }
  isFull() { return this.count() >= this.max; }
  reset() { this.cache = []; this.cache.push(new Loan()); }
  nothing() {}
}
class Book {}
class Member {}
class Loan {}
class Engine {}
"""


def test_attribute_types_come_from_jsdoc_literals_and_constructors():
    library = _cls(parse(LIBRARY), "Library")
    types = {a.name: a.datatype for a in library.attributes}
    assert types["name"] == "String"  # @param {string}
    assert types["books"] == "List[Book]"  # @param {Book[]}
    assert types["max"] == "int"  # default value 10
    assert types["ratio"] == "float"
    assert types["index"] == "Map"
    assert types["curator"] == "Member"  # @type
    assert types["engine"] == "Engine"


def test_method_parameter_and_return_types():
    library = _cls(parse(LIBRARY), "Library")
    lend = _method(library, "lend")
    assert [(p.name, p.datatype) for p in lend.parameters] == [("member", "Member"), ("book", "Book")]  # `book` -> class Book, by name
    assert lend.return_type == "Loan"
    assert _method(library, "count").return_type == "int"
    assert _method(library, "describe").return_type == "String"
    assert _method(library, "isFull").return_type == "boolean"
    assert _method(library, "nothing").return_type == "void"


def test_relationships_from_jsdoc_and_instantiation():
    doc = parse(LIBRARY)
    library = _cls(doc, "Library")
    aggregation = _rels(doc, library, _cls(doc, "Book"), RelationshipType.AGGREGATION)
    assert len(aggregation) == 1 and aggregation[0].multiplicity.destination == "*"
    assert len(_rels(doc, library, _cls(doc, "Member"), RelationshipType.ASSOCIATION)) == 1
    assert len(_rels(doc, library, _cls(doc, "Engine"), RelationshipType.COMPOSITION)) == 1
    pushed = _rels(doc, library, _cls(doc, "Loan"), RelationshipType.COMPOSITION)
    assert len(pushed) == 1 and pushed[0].multiplicity.destination == "*"


def test_attribute_assigned_outside_constructor_is_found():
    library = _cls(parse(LIBRARY), "Library")
    assert _attr(library, "cache").datatype == "List[Loan]"


def test_new_in_method_is_a_dependency():
    doc = parse("class A { make() { return new B(); } }\nclass B {}")
    a, b = _cls(doc, "A"), _cls(doc, "B")
    assert _method(a, "make").return_type == "B"
    assert len(_rels(doc, a, b, RelationshipType.DEPENDENCY)) == 1


def test_export_default_class_and_module_syntax_are_parsed():
    doc = parse("import x from './x.js';\nexport default class Foo {}\nexport class Bar extends Foo {}")
    assert {c.name for c in doc.classes} == {"Foo", "Bar"}
    assert len(_rels(doc, _cls(doc, "Bar"), _cls(doc, "Foo"), RelationshipType.INHERITANCE)) == 1


def test_non_identifier_method_name_is_skipped():
    doc = parse("class A { 'odd-name'() {} ok() {} }")
    assert [m.name for m in _cls(doc, "A").methods] == ["ok"]


UNTYPED_JS = """
class Teacher { constructor(name) { this.name = name; } }
class Professor {}
class Student {
  constructor(name, teacher, isActive) {
    this.name = name;
    this.teacher = teacher;
    this.isActive = isActive;
  }
}
class Department {
  constructor(name, professors) { this.name = name; this.professors = professors; }
}
"""


def test_untyped_parameter_named_after_a_class_is_an_association():
    doc = parse(UNTYPED_JS)
    student = _cls(doc, "Student")
    assert _attr(student, "teacher").datatype == "Teacher"
    assert len(_rels(doc, student, _cls(doc, "Teacher"), RelationshipType.ASSOCIATION)) == 1


def test_untyped_plural_parameter_is_an_aggregated_collection():
    doc = parse(UNTYPED_JS)
    department = _cls(doc, "Department")
    assert _attr(department, "professors").datatype == "List[Professor]"
    edges = _rels(doc, department, _cls(doc, "Professor"), RelationshipType.AGGREGATION)
    assert len(edges) == 1 and edges[0].multiplicity.destination == "*"


def test_untyped_common_names_get_plain_types_instead_of_any():
    student = _cls(parse(UNTYPED_JS), "Student")
    assert _attr(student, "name").datatype == "String"
    assert _attr(student, "isActive").datatype == "boolean"


def test_collection_filled_with_locally_created_instances_is_composition_many():
    source = """
class CartItem {}
class ShoppingCart {
    constructor() { this.items = []; }
    addProduct(product) {
        const item = new CartItem(product);
        this.items.push(item);
    }
}
"""
    doc = parse(source)
    ids = {c.name: c.id for c in doc.classes}
    edges = [
        r for r in doc.relationships
        if r.source == ids["ShoppingCart"] and r.destination == ids["CartItem"]
    ]
    assert [e.type for e in edges] == [RelationshipType.COMPOSITION]
    assert edges[0].multiplicity.destination == "*"
    cart = next(c for c in doc.classes if c.name == "ShoppingCart")
    assert next(a for a in cart.attributes if a.name == "items").datatype == "List[CartItem]"


def test_pushing_an_injected_local_is_not_composition():
    source = """
class CartItem {}
class ShoppingCart {
    constructor() { this.items = []; }
    add(item) { this.items.push(item); }
}
"""
    doc = parse(source)
    assert not [r for r in doc.relationships if r.type == RelationshipType.COMPOSITION]
