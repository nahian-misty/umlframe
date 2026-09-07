from backend.mermaid.class_diagram import document_to_class_diagram
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

_POSITION = Position(x=0, y=0)
_SIZE = Size(width=200, height=140)


def _empty_class(class_id: str, name: str) -> UmlClass:
    return UmlClass(id=class_id, name=name, attributes=[], methods=[], position=_POSITION, size=_SIZE)


def test_empty_document_renders_bare_header():
    doc = UmlDocument(classes=[], relationships=[])
    assert document_to_class_diagram(doc) == "classDiagram"


def test_class_with_no_members_renders_empty_braces():
    doc = UmlDocument(classes=[_empty_class("class_1", "Empty")], relationships=[])
    assert document_to_class_diagram(doc) == "classDiagram\n    class Empty {\n    }"


def test_attribute_visibility_symbols_and_static_marker():
    cls = UmlClass(
        id="class_1",
        name="Config",
        attributes=[
            Attribute(name="publicField", datatype="String", visibility=Visibility.PUBLIC),
            Attribute(name="privateField", datatype="int", visibility=Visibility.PRIVATE),
            Attribute(name="protectedField", datatype="int", visibility=Visibility.PROTECTED),
            Attribute(name="packageField", datatype="int", visibility=Visibility.PACKAGE),
            Attribute(name="MAX", datatype="int", visibility=Visibility.PUBLIC, static=True),
        ],
        methods=[],
        position=_POSITION,
        size=_SIZE,
    )
    doc = UmlDocument(classes=[cls], relationships=[])
    diagram = document_to_class_diagram(doc)
    assert "+String publicField" in diagram
    assert "-int privateField" in diagram
    assert "#int protectedField" in diagram
    assert "~int packageField" in diagram
    assert "+int MAX$" in diagram


def test_method_params_static_and_abstract_markers():
    cls = UmlClass(
        id="class_1",
        name="Shape",
        attributes=[],
        methods=[
            Method(
                name="area",
                visibility=Visibility.PUBLIC,
                parameters=[],
                return_type="float",
                abstract=True,
            ),
            Method(
                name="create",
                visibility=Visibility.PUBLIC,
                parameters=[Parameter(name="sides", datatype="int")],
                return_type="Shape",
                static=True,
            ),
        ],
        position=_POSITION,
        size=_SIZE,
    )
    doc = UmlDocument(classes=[cls], relationships=[])
    diagram = document_to_class_diagram(doc)
    assert "+area() float*" in diagram
    assert "+create(sides: int) Shape$" in diagram


# ---------------------------------------------------------------------------
# One case per relationship type
# ---------------------------------------------------------------------------


def _two_class_doc(rel: Relationship) -> UmlDocument:
    return UmlDocument(
        classes=[_empty_class("class_1", "Dog"), _empty_class("class_2", "Animal")],
        relationships=[rel],
    )


def test_inheritance_renders_hollow_triangle_no_multiplicity():
    rel = Relationship(
        id="rel_1",
        source="class_1",
        destination="class_2",
        type=RelationshipType.INHERITANCE,
        multiplicity=Multiplicity(source="1", destination="1"),
    )
    diagram = document_to_class_diagram(_two_class_doc(rel))
    assert "Dog --|> Animal" in diagram
    assert '"1"' not in diagram


def test_composition_renders_filled_diamond_with_multiplicity():
    rel = Relationship(
        id="rel_1",
        source="class_1",
        destination="class_2",
        type=RelationshipType.COMPOSITION,
        multiplicity=Multiplicity(source="1", destination="1"),
    )
    diagram = document_to_class_diagram(_two_class_doc(rel))
    assert 'Dog "1" *-- "1" Animal' in diagram


def test_aggregation_renders_hollow_diamond_with_many_multiplicity():
    rel = Relationship(
        id="rel_1",
        source="class_1",
        destination="class_2",
        type=RelationshipType.AGGREGATION,
        multiplicity=Multiplicity(source="1", destination="*"),
    )
    diagram = document_to_class_diagram(_two_class_doc(rel))
    assert 'Dog "1" o-- "*" Animal' in diagram


def test_association_renders_plain_arrow_with_multiplicity():
    rel = Relationship(
        id="rel_1",
        source="class_1",
        destination="class_2",
        type=RelationshipType.ASSOCIATION,
        multiplicity=Multiplicity(source="1", destination="1"),
    )
    diagram = document_to_class_diagram(_two_class_doc(rel))
    assert 'Dog "1" --> "1" Animal' in diagram


def test_dependency_renders_dashed_arrow_no_multiplicity_with_label():
    rel = Relationship(
        id="rel_1",
        source="class_1",
        destination="class_2",
        type=RelationshipType.DEPENDENCY,
        multiplicity=Multiplicity(source="1", destination="1"),
        label="uses",
    )
    diagram = document_to_class_diagram(_two_class_doc(rel))
    assert "Dog ..> Animal : uses" in diagram
    assert '"1"' not in diagram
