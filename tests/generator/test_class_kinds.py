"""Interfaces and abstract classes: kind drives the declaration keyword, which methods
are abstract, and how inheritance edges are spelled (implements vs extends)."""

import pytest

from backend.schemas.uml import ClassKind, UmlDocument
from backend.services.codegen_service import generate_code
from tests.generator.conftest import cls, inheritance, method


@pytest.fixture
def document() -> UmlDocument:
    return UmlDocument(
        classes=[
            cls(
                "class_1",
                "Owner",
                methods=[method("acquire", params=[("item", "String")]), method("dispose")],
                kind=ClassKind.INTERFACE,
            ),
            cls(
                "class_2",
                "Shape",
                methods=[
                    method("area", return_type="double", abstract=True),
                    method("name", return_type="String"),
                ],
                kind=ClassKind.ABSTRACT,
            ),
            cls("class_3", "Person", methods=[method("acquire", params=[("item", "String")])]),
            cls("class_4", "Circle", methods=[method("area", return_type="double")]),
        ],
        relationships=[inheritance("class_3", "class_1"), inheritance("class_4", "class_2")],
    )


PYTHON_OWNER = "from abc import ABC, abstractmethod\n\n\nclass Owner(ABC):\n    @abstractmethod\n    def acquire(self, item: str) -> None:\n        ...\n\n    @abstractmethod\n    def dispose(self) -> None:\n        ...\n\n"

PYTHON_SHAPE = "from abc import ABC, abstractmethod\n\n\nclass Shape(ABC):\n    def __init__(self) -> None:\n        pass\n\n    @abstractmethod\n    def area(self) -> float:\n        ...\n\n    def name(self) -> str:\n        ...\n\n"

PYTHON_PERSON = "from .Owner import Owner\n\n\nclass Person(Owner):\n    def __init__(self) -> None:\n        pass\n\n    def acquire(self, item: str) -> None:\n        ...\n\n    def dispose(self) -> None:\n        ...\n\n"

PYTHON_CIRCLE = "from .Shape import Shape\n\n\nclass Circle(Shape):\n    def __init__(self) -> None:\n        super().__init__()\n        pass\n\n    def area(self) -> float:\n        ...\n\n"

JAVA_OWNER = (
    "public interface Owner {\n\n    void acquire(String item);\n\n    void dispose();\n\n}\n"
)

JAVA_SHAPE = 'public abstract class Shape {\n\n    public Shape() {\n    }\n\n    public abstract double area();\n    public String name() {\n        throw new UnsupportedOperationException("Not implemented");\n    }\n}\n'

JAVA_PERSON = 'public class Person implements Owner {\n\n    public Person() {\n    }\n\n    public void acquire(String item) {\n        throw new UnsupportedOperationException("Not implemented");\n    }\n    public void dispose() {\n        throw new UnsupportedOperationException("Not implemented");\n    }\n}\n'

JAVA_CIRCLE = 'public class Circle extends Shape {\n\n    public Circle() {\n    }\n\n    public double area() {\n        throw new UnsupportedOperationException("Not implemented");\n    }\n}\n'

JAVASCRIPT_OWNER = "class Owner {\n    constructor() {\n        // initialise fields above\n        if (new.target === Owner) {\n            throw new TypeError('Owner is abstract and cannot be instantiated');\n        }\n    }\n\n    acquire(item) {\n        throw new Error('Not implemented');\n    }\n\n    dispose() {\n        throw new Error('Not implemented');\n    }\n\n}\n\nexport { Owner };\n"

JAVASCRIPT_SHAPE = "class Shape {\n    constructor() {\n        // initialise fields above\n        if (new.target === Shape) {\n            throw new TypeError('Shape is abstract and cannot be instantiated');\n        }\n    }\n\n    area() {\n        throw new Error('Not implemented');\n    }\n\n    name() {\n        throw new Error('Not implemented');\n    }\n\n}\n\nexport { Shape };\n"

JAVASCRIPT_PERSON = "class Person {\n    constructor() {\n        // initialise fields above\n    }\n\n    acquire(item) {\n        throw new Error('Not implemented');\n    }\n\n    dispose() {\n        throw new Error('Not implemented');\n    }\n\n}\n\nexport { Person };\n"

JAVASCRIPT_CIRCLE = "import { Shape } from './Shape.js';\n\nclass Circle extends Shape {\n    constructor() {\n        super();\n    }\n\n    area() {\n        throw new Error('Not implemented');\n    }\n\n}\n\nexport { Circle };\n"


def test_python_kinds(document):
    files = generate_code(document, "python")
    assert files["Owner.py"] == PYTHON_OWNER
    assert files["Shape.py"] == PYTHON_SHAPE
    assert files["Person.py"] == PYTHON_PERSON
    assert files["Circle.py"] == PYTHON_CIRCLE


def test_java_kinds(document):
    files = generate_code(document, "java")
    assert files["Owner.java"] == JAVA_OWNER
    assert files["Shape.java"] == JAVA_SHAPE
    assert files["Person.java"] == JAVA_PERSON
    assert files["Circle.java"] == JAVA_CIRCLE


def test_javascript_kinds(document):
    files = generate_code(document, "javascript")
    assert files["Owner.js"] == JAVASCRIPT_OWNER
    assert files["Shape.js"] == JAVASCRIPT_SHAPE
    assert files["Person.js"] == JAVASCRIPT_PERSON
    assert files["Circle.js"] == JAVASCRIPT_CIRCLE


def test_concrete_class_defines_the_methods_its_interface_promises(document):
    person = generate_code(document, "java")["Person.java"]

    assert "public void dispose()" in person
    assert person.count("public void acquire(String item)") == 1


def test_realization_is_spelled_like_inheritance_in_generated_code(document):
    from backend.schemas.uml import RelationshipType

    document.relationships[0].type = RelationshipType.REALIZATION
    files = generate_code(document, "java")

    assert "public class Person implements Owner {" in files["Person.java"]
