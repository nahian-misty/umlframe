from __future__ import annotations

from pydantic import BaseModel


class AttributeDescription(BaseModel):
    name: str
    type: str
    access: str  # how generated code refers to it, e.g. "self.__email" or "this.email"
    static: bool = False
    final: bool = False


class MethodDescription(BaseModel):
    index: int  # position in UmlClass.methods; stable even when names repeat
    key: str  # unique "Class.method" (with "#n" for overloads) used to address the method
    name: str
    signature: str  # as it appears in the generated scaffold
    access: str  # how other methods call it, e.g. "self.save" or "Account.open"
    return_type: str
    static: bool = False
    abstract: bool = False


class CollaboratorDescription(BaseModel):
    kind: str  # association | aggregation | composition | inheritance | realization | dependency
    role: str  # "this class uses/owns/extends it" or "it uses/owns/extends this class"
    class_name: str
    methods: list[str]  # public signatures only


class ClassDescription(BaseModel):
    """Everything a code-writing model needs to know about one class, derived from the same
    template context as the scaffold so names and types match the generated code exactly."""

    class_name: str
    language: str
    parent: str | None = None
    attributes: list[AttributeDescription]
    methods: list[MethodDescription]
    collaborators: list[CollaboratorDescription]
