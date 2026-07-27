import pytest

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


def cls(id: str, name: str, attributes=None, methods=None) -> UmlClass:
    return UmlClass(
        id=id,
        name=name,
        attributes=attributes or [],
        methods=methods or [],
        position=Position(x=0, y=0),
        size=Size(width=160, height=120),
    )


def attr(name: str, datatype: str, visibility=Visibility.PUBLIC, **kw) -> Attribute:
    return Attribute(name=name, datatype=datatype, visibility=visibility, **kw)


def method(name: str, visibility=Visibility.PUBLIC, params=None, return_type="void", **kw) -> Method:
    return Method(
        name=name,
        visibility=visibility,
        parameters=[Parameter(name=p[0], datatype=p[1]) for p in (params or [])],
        return_type=return_type,
        **kw,
    )


def inheritance(source_id: str, dest_id: str) -> Relationship:
    return Relationship(
        id="rel_1",
        source=source_id,
        destination=dest_id,
        type=RelationshipType.INHERITANCE,
        multiplicity=Multiplicity(source="1", destination="1"),
        label="",
    )


@pytest.fixture
def simple_class() -> UmlDocument:
    return UmlDocument(
        classes=[cls("class_1", "User")],
        relationships=[],
    )


@pytest.fixture
def class_with_attrs() -> UmlDocument:
    return UmlDocument(
        classes=[
            cls(
                "class_1",
                "User",
                attributes=[
                    attr("email", "String", Visibility.PRIVATE),
                    attr("age", "int", Visibility.PROTECTED),
                    attr("MAX_SIZE", "int", Visibility.PUBLIC, static=True, default_value="100"),
                ],
            )
        ],
        relationships=[],
    )


@pytest.fixture
def class_with_methods() -> UmlDocument:
    return UmlDocument(
        classes=[
            cls(
                "class_1",
                "Service",
                methods=[
                    method("process", Visibility.PUBLIC, params=[("data", "String")], return_type="bool"),
                    method("helper", Visibility.PRIVATE),
                    method("create", Visibility.PUBLIC, static=True),
                    method("compute", Visibility.PUBLIC, abstract=True, return_type="int"),
                ],
            )
        ],
        relationships=[],
    )


@pytest.fixture
def inheritance_pair() -> UmlDocument:
    return UmlDocument(
        classes=[
            cls("class_1", "Animal"),
            cls("class_2", "Dog"),
        ],
        relationships=[inheritance("class_2", "class_1")],
    )


@pytest.fixture
def cross_class_refs() -> UmlDocument:
    return UmlDocument(
        classes=[
            cls(
                "class_1",
                "Order",
                attributes=[attr("user", "User", Visibility.PRIVATE)],
                methods=[method("getUser", Visibility.PUBLIC, return_type="User")],
            ),
            cls("class_2", "User"),
        ],
        relationships=[],
    )
