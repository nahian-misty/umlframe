from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.db.usernames import MAX_USERNAME_LENGTH, MIN_USERNAME_LENGTH, USERNAME_PATTERN
from backend.generator.registry import SUPPORTED_LANGUAGES
from backend.llm.prompts import MAX_INSTRUCTIONS_LENGTH
from backend.models.project_state import DEFAULT_PROJECT_TYPE, CodeInputs, ProjectType
from backend.reverse.registry import SUPPORTED_LANGUAGES as REVERSE_SUPPORTED_LANGUAGES
from backend.schemas.activity import ActivityDocument
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


class ImplementCodeRequest(BaseModel):
    document: UmlDocument
    language: str
    instructions: str = Field(default="", max_length=MAX_INSTRUCTIONS_LENGTH)

    @field_validator("language")
    @classmethod
    def language_must_be_supported(cls, v: str) -> str:
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language '{v}'. Supported: {SUPPORTED_LANGUAGES}")
        return v


class GenerateActivityCodeRequest(BaseModel):
    document: ActivityDocument
    language: str
    function_name: str = "generated_function"

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
    # When both are set, the response also includes that method's control-flow
    # graph (Milestone 6's activity-diagram extension) alongside the class
    # structure -- a second, optional extraction path, not a mode switch.
    class_name: str | None = None
    method_name: str | None = None

    @field_validator("language")
    @classmethod
    def language_must_be_supported(cls, v: str) -> str:
        if v not in REVERSE_SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language '{v}'. Supported: {REVERSE_SUPPORTED_LANGUAGES}")
        return v


class ControlFlowsRequest(BaseModel):
    source: str
    language: str

    @field_validator("language")
    @classmethod
    def language_must_be_supported(cls, v: str) -> str:
        if v not in REVERSE_SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language '{v}'. Supported: {REVERSE_SUPPORTED_LANGUAGES}")
        return v


class JsonToMermaidRequest(BaseModel):
    diagram_type: Literal["class", "activity"] = "class"
    document: UmlDocument | None = None
    activity: ActivityDocument | None = None

    @model_validator(mode="after")
    def payload_matches_diagram_type(self) -> JsonToMermaidRequest:
        if self.diagram_type == "class" and self.document is None:
            raise ValueError("'document' is required when diagram_type is 'class'")
        if self.diagram_type == "activity" and self.activity is None:
            raise ValueError("'activity' is required when diagram_type is 'activity'")
        return self


class ActivityDiagramImageRequest(BaseModel):
    activity: ActivityDocument


MIN_PASSWORD_LENGTH = 8


def _check_password_length(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    return value


class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str | None = None

    @field_validator("username")
    @classmethod
    def username_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return None
        name = v.strip()
        if not MIN_USERNAME_LENGTH <= len(name) <= MAX_USERNAME_LENGTH:
            raise ValueError(
                f"Username must be {MIN_USERNAME_LENGTH}-{MAX_USERNAME_LENGTH} characters"
            )
        if not USERNAME_PATTERN.match(name):
            raise ValueError("Username may only contain letters, numbers, '.', '_' and '-'")
        return name

    @field_validator("email")
    @classmethod
    def email_must_look_like_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        return _check_password_length(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: str) -> str:
        return _check_password_length(v)


class LoginRequest(BaseModel):
    email: str
    password: str


PROJECT_NAME_MAX_LENGTH = 255


def _clean_project_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise ValueError("Project name must not be blank")
    if len(name) > PROJECT_NAME_MAX_LENGTH:
        raise ValueError(f"Project name must be at most {PROJECT_NAME_MAX_LENGTH} characters")
    return name


class CreateProjectRequest(BaseModel):
    name: str
    project_type: ProjectType = DEFAULT_PROJECT_TYPE
    document: UmlDocument | None = None
    activity_document: ActivityDocument | None = None
    code_inputs: CodeInputs | None = None

    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, v: str) -> str:
        return _clean_project_name(v)


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    document: UmlDocument | None = None
    activity_document: ActivityDocument | None = None
    code_inputs: CodeInputs | None = None

    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, v: str | None) -> str | None:
        return None if v is None else _clean_project_name(v)
