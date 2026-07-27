from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, model_validator


class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"
    PACKAGE = "package"


class RelationshipType(str, Enum):
    ASSOCIATION = "association"
    AGGREGATION = "aggregation"
    COMPOSITION = "composition"
    INHERITANCE = "inheritance"
    DEPENDENCY = "dependency"


class Parameter(BaseModel):
    name: str
    datatype: str


class Attribute(BaseModel):
    name: str
    datatype: str
    visibility: Visibility
    default_value: str | None = None
    static: bool = False
    final: bool = False


class Method(BaseModel):
    name: str
    visibility: Visibility
    parameters: list[Parameter] = []
    return_type: str = "void"
    static: bool = False
    abstract: bool = False


class Position(BaseModel):
    x: float
    y: float


class Size(BaseModel):
    width: float
    height: float


class UmlClass(BaseModel):
    id: str
    name: str
    attributes: list[Attribute] = []
    methods: list[Method] = []
    position: Position
    size: Size


class Multiplicity(BaseModel):
    source: str
    destination: str


class Relationship(BaseModel):
    id: str
    source: str
    destination: str
    type: RelationshipType
    multiplicity: Multiplicity
    label: str = ""


class UmlDocument(BaseModel):
    classes: list[UmlClass] = []
    relationships: list[Relationship] = []

    @model_validator(mode="after")
    def validate_relationship_references(self) -> UmlDocument:
        class_ids = {cls.id for cls in self.classes}
        for rel in self.relationships:
            if rel.source not in class_ids:
                raise ValueError(
                    f"Relationship '{rel.id}' references unknown source class '{rel.source}'"
                )
            if rel.destination not in class_ids:
                raise ValueError(
                    f"Relationship '{rel.id}' references unknown destination class '{rel.destination}'"
                )
        return self
