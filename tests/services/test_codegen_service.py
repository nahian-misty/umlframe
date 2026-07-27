import pytest

from backend.schemas.uml import (
    Attribute,
    Method,
    Multiplicity,
    Position,
    Relationship,
    RelationshipType,
    Size,
    UmlClass,
    UmlDocument,
    Visibility,
)
from backend.services.codegen_service import generate_code


def simple_doc() -> UmlDocument:
    return UmlDocument(
        classes=[
            UmlClass(
                id="class_1",
                name="User",
                attributes=[Attribute(name="email", datatype="String", visibility=Visibility.PRIVATE)],
                methods=[Method(name="login", visibility=Visibility.PUBLIC)],
                position=Position(x=0, y=0),
                size=Size(width=160, height=120),
            )
        ],
        relationships=[],
    )


def test_generate_python_returns_py_file():
    files = generate_code(simple_doc(), "python")
    assert set(files.keys()) == {"User.py"}


def test_generate_java_returns_java_file():
    files = generate_code(simple_doc(), "java")
    assert set(files.keys()) == {"User.java"}


def test_generate_javascript_returns_js_file():
    files = generate_code(simple_doc(), "javascript")
    assert set(files.keys()) == {"User.js"}


def test_unknown_language_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported language"):
        generate_code(simple_doc(), "cobol")


def test_empty_document_returns_empty_dict():
    assert generate_code(UmlDocument(), "python") == {}
    assert generate_code(UmlDocument(), "java") == {}
    assert generate_code(UmlDocument(), "javascript") == {}


def test_multiple_classes_produce_multiple_files():
    doc = UmlDocument(
        classes=[
            UmlClass(id="class_1", name="A", position=Position(x=0, y=0), size=Size(width=100, height=80)),
            UmlClass(id="class_2", name="B", position=Position(x=0, y=0), size=Size(width=100, height=80)),
            UmlClass(id="class_3", name="C", position=Position(x=0, y=0), size=Size(width=100, height=80)),
        ],
        relationships=[],
    )
    files = generate_code(doc, "python")
    assert set(files.keys()) == {"A.py", "B.py", "C.py"}


def test_output_is_deterministic():
    doc = simple_doc()
    assert generate_code(doc, "python") == generate_code(doc, "python")


def test_inheritance_correctly_resolved():
    doc = UmlDocument(
        classes=[
            UmlClass(id="class_1", name="Animal", position=Position(x=0, y=0), size=Size(width=100, height=80)),
            UmlClass(id="class_2", name="Dog", position=Position(x=0, y=0), size=Size(width=100, height=80)),
        ],
        relationships=[
            Relationship(
                id="rel_1",
                source="class_2",
                destination="class_1",
                type=RelationshipType.INHERITANCE,
                multiplicity=Multiplicity(source="1", destination="1"),
                label="",
            )
        ],
    )
    python_files = generate_code(doc, "python")
    assert "class Dog(Animal):" in python_files["Dog.py"]
    assert "class Animal:" in python_files["Animal.py"]
