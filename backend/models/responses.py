from datetime import datetime

from pydantic import BaseModel

from backend.schemas.activity import ActivityDocument, MethodControlFlow
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


class ControlFlowsResponse(BaseModel):
    methods: list[MethodControlFlow]


class ActivityReverseResponse(BaseModel):
    document: ActivityDocument


class MermaidResponse(BaseModel):
    diagram: str


class ActivityDiagramImageResponse(BaseModel):
    # Base64-encoded PNG, keeping this endpoint's body JSON like every other
    # one in the API, rather than a one-off binary response type.
    image_base64: str


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
