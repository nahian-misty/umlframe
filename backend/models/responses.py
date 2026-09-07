from datetime import datetime

from pydantic import BaseModel

from backend.schemas.activity import ActivityDocument
from backend.schemas.uml import UmlDocument


class CodeGenerationResponse(BaseModel):
    files: dict[str, str]


class LanguageListResponse(BaseModel):
    languages: list[str]


class TemplateListResponse(BaseModel):
    templates: dict[str, list[str]]


class ReverseResponse(BaseModel):
    document: UmlDocument
    control_flow: ActivityDocument | None = None


class MermaidResponse(BaseModel):
    diagram: str


class ErrorResponse(BaseModel):
    error: str


class UserResponse(BaseModel):
    id: int
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ProjectResponse(BaseModel):
    id: int
    name: str
    document: UmlDocument
    created_at: datetime
    updated_at: datetime


class ClassBoxSummary(BaseModel):
    x: float
    y: float
    width: float
    height: float


class ProjectSummaryResponse(BaseModel):
    id: int
    name: str
    updated_at: datetime
    class_count: int
    relationship_count: int
    class_boxes: list[ClassBoxSummary]


class ProjectListResponse(BaseModel):
    projects: list[ProjectSummaryResponse]
