from pydantic import BaseModel

from backend.schemas.uml import UmlDocument


class CodeGenerationResponse(BaseModel):
    files: dict[str, str]


class LanguageListResponse(BaseModel):
    languages: list[str]


class TemplateListResponse(BaseModel):
    templates: dict[str, list[str]]


class ReverseResponse(BaseModel):
    document: UmlDocument


class MermaidResponse(BaseModel):
    diagram: str


class ErrorResponse(BaseModel):
    error: str
