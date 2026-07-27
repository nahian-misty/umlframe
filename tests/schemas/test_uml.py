import pytest
from pydantic import ValidationError

from backend.schemas.uml import (
    Attribute,
    Method,
    Multiplicity,
    Parameter,
    Position,
    Relationship,
    RelationshipType,
    Size,
    UmlClass,
    UmlDocument,
    Visibility,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_class(id: str = "class_1", name: str = "User") -> UmlClass:
    return UmlClass(
        id=id,
        name=name,
        position=Position(x=0, y=0),
        size=Size(width=160, height=120),
    )


def make_relationship(
    id: str = "rel_1",
    source: str = "class_1",
    destination: str = "class_2",
    type: RelationshipType = RelationshipType.ASSOCIATION,
) -> Relationship:
    return Relationship(
        id=id,
        source=source,
        destination=destination,
        type=type,
        multiplicity=Multiplicity(source="1", destination="*"),
        label="",
    )


# ---------------------------------------------------------------------------
# Attribute
# ---------------------------------------------------------------------------


def test_attribute_defaults():
    attr = Attribute(name="email", datatype="String", visibility=Visibility.PRIVATE)
    assert attr.default_value is None
    assert attr.static is False
    assert attr.final is False


def test_attribute_full():
    attr = Attribute(
        name="count",
        datatype="int",
        visibility=Visibility.PUBLIC,
        default_value="0",
        static=True,
        final=True,
    )
    assert attr.default_value == "0"
    assert attr.static is True
    assert attr.final is True


def test_attribute_invalid_visibility():
    with pytest.raises(ValidationError):
        Attribute(name="x", datatype="int", visibility="invalid")


# ---------------------------------------------------------------------------
# Method
# ---------------------------------------------------------------------------


def test_method_defaults():
    method = Method(name="login", visibility=Visibility.PUBLIC)
    assert method.parameters == []
    assert method.return_type == "void"
    assert method.static is False
    assert method.abstract is False


def test_method_with_parameters():
    method = Method(
        name="find",
        visibility=Visibility.PUBLIC,
        parameters=[Parameter(name="id", datatype="int")],
        return_type="User",
    )
    assert len(method.parameters) == 1
    assert method.parameters[0].name == "id"


# ---------------------------------------------------------------------------
# UmlClass
# ---------------------------------------------------------------------------


def test_uml_class_empty_compartments():
    cls = make_class()
    assert cls.attributes == []
    assert cls.methods == []


def test_uml_class_with_members():
    cls = UmlClass(
        id="class_1",
        name="Order",
        attributes=[Attribute(name="total", datatype="float", visibility=Visibility.PRIVATE)],
        methods=[Method(name="submit", visibility=Visibility.PUBLIC)],
        position=Position(x=10, y=20),
        size=Size(width=200, height=150),
    )
    assert len(cls.attributes) == 1
    assert len(cls.methods) == 1


# ---------------------------------------------------------------------------
# UmlDocument — happy path
# ---------------------------------------------------------------------------


def test_document_empty():
    doc = UmlDocument()
    assert doc.classes == []
    assert doc.relationships == []


def test_document_two_classes_with_relationship():
    c1 = make_class("class_1", "User")
    c2 = make_class("class_2", "Order")
    rel = make_relationship("rel_1", "class_1", "class_2")
    doc = UmlDocument(classes=[c1, c2], relationships=[rel])
    assert len(doc.classes) == 2
    assert len(doc.relationships) == 1


def test_document_all_relationship_types():
    c1 = make_class("class_1", "A")
    c2 = make_class("class_2", "B")
    for rt in RelationshipType:
        rel = make_relationship(type=rt)
        doc = UmlDocument(classes=[c1, c2], relationships=[rel])
        assert doc.relationships[0].type == rt


# ---------------------------------------------------------------------------
# UmlDocument — validator: unknown relationship references
# ---------------------------------------------------------------------------


def test_document_rejects_unknown_source():
    c1 = make_class("class_1", "User")
    rel = make_relationship(source="class_99", destination="class_1")
    with pytest.raises(ValidationError, match="unknown source class"):
        UmlDocument(classes=[c1], relationships=[rel])


def test_document_rejects_unknown_destination():
    c1 = make_class("class_1", "User")
    rel = make_relationship(source="class_1", destination="class_99")
    with pytest.raises(ValidationError, match="unknown destination class"):
        UmlDocument(classes=[c1], relationships=[rel])


def test_document_allows_self_referential_relationship():
    c1 = make_class("class_1", "Node")
    rel = make_relationship(source="class_1", destination="class_1")
    doc = UmlDocument(classes=[c1], relationships=[rel])
    assert doc.relationships[0].source == "class_1"
