from pydantic import BaseModel, field_validator

from backend.generator.registry import SUPPORTED_LANGUAGES
from backend.reverse.registry import SUPPORTED_LANGUAGES as REVERSE_SUPPORTED_LANGUAGES
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

    @field_validator("language")
    @classmethod
    def language_must_be_supported(cls, v: str) -> str:
        if v not in REVERSE_SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language '{v}'. Supported: {REVERSE_SUPPORTED_LANGUAGES}")
        return v


class JsonToMermaidRequest(BaseModel):
    document: UmlDocument


class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_must_look_like_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateProjectRequest(BaseModel):
    name: str
    document: UmlDocument | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    document: UmlDocument | None = None
