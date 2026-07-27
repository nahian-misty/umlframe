from pydantic import BaseModel, field_validator

from backend.generator.registry import SUPPORTED_LANGUAGES
from backend.schemas.uml import UmlDocument


class GenerateCodeRequest(BaseModel):
    document: UmlDocument
    language: str

    @field_validator("language")
    @classmethod
    def language_must_be_supported(cls, v: str) -> str:
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language '{v}'. Supported: {SUPPORTED_LANGUAGES}")
        return v


class ReverseRequest(BaseModel):
    source: str
    language: str
    filename: str = ""


class JsonToMermaidRequest(BaseModel):
    document: UmlDocument
