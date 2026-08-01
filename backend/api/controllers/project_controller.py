from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.db.models import Project, User
from backend.models.requests import CreateProjectRequest, UpdateProjectRequest
from backend.models.responses import (
    ClassBoxSummary,
    ProjectListResponse,
    ProjectResponse,
    ProjectSummaryResponse,
)
from backend.schemas.uml import UmlDocument
from backend.services import project_service
from backend.services.project_service import ProjectNotFoundError


def _to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        document=UmlDocument.model_validate_json(project.document),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _to_summary(project: Project) -> ProjectSummaryResponse:
    document = UmlDocument.model_validate_json(project.document)
    return ProjectSummaryResponse(
        id=project.id,
        name=project.name,
        updated_at=project.updated_at,
        class_count=len(document.classes),
        relationship_count=len(document.relationships),
        class_boxes=[
            ClassBoxSummary(
                x=cls.position.x,
                y=cls.position.y,
                width=cls.size.width,
                height=cls.size.height,
            )
            for cls in document.classes
        ],
    )


async def list_projects(current_user: User, db: Session) -> ProjectListResponse:
    projects = project_service.list_projects(db, current_user.id)
    return ProjectListResponse(projects=[_to_summary(p) for p in projects])


async def create_project(
    request: CreateProjectRequest, current_user: User, db: Session
) -> ProjectResponse:
    try:
        project = project_service.create_project(
            db, current_user.id, request.name, request.document
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Project creation failed") from exc
    return _to_response(project)


async def get_project(project_id: int, current_user: User, db: Session) -> ProjectResponse:
    try:
        project = project_service.get_project(db, current_user.id, project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(project)


async def update_project(
    project_id: int, request: UpdateProjectRequest, current_user: User, db: Session
) -> ProjectResponse:
    try:
        project = project_service.update_project(
            db, current_user.id, project_id, request.name, request.document
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Project update failed") from exc
    return _to_response(project)


async def delete_project(project_id: int, current_user: User, db: Session) -> dict[str, str]:
    try:
        project_service.delete_project(db, current_user.id, project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted"}
