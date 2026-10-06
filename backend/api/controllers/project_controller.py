from typing import cast

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.db.models import Project, User
from backend.models.project_state import CodeInputs, ProjectType
from backend.models.requests import CreateProjectRequest, UpdateProjectRequest
from backend.models.responses import (
    ClassBoxSummary,
    ProjectListResponse,
    ProjectResponse,
    ProjectSummaryResponse,
)
from backend.schemas.activity import ActivityDocument
from backend.schemas.uml import UmlDocument
from backend.services import project_service
from backend.services.project_service import ProjectNameTakenError, ProjectNotFoundError


def _to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        project_type=cast(ProjectType, project.project_type),
        document=UmlDocument.model_validate_json(project.document),
        activity_document=(
            ActivityDocument.model_validate_json(project.activity_document)
            if project.activity_document is not None
            else None
        ),
        code_inputs=(
            CodeInputs.model_validate_json(project.code_inputs)
            if project.code_inputs is not None
            else CodeInputs()
        ),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _to_summary(project: Project) -> ProjectSummaryResponse:
    document = UmlDocument.model_validate_json(project.document)
    activity = (
        ActivityDocument.model_validate_json(project.activity_document)
        if project.activity_document is not None
        else None
    )
    # The thumbnail draws whichever diagram the project type is about.
    shapes = (
        [(n.position, n.size) for n in activity.nodes]
        if project.project_type == "activity" and activity is not None
        else [(cls.position, cls.size) for cls in document.classes]
    )
    return ProjectSummaryResponse(
        id=project.id,
        name=project.name,
        project_type=cast(ProjectType, project.project_type),
        updated_at=project.updated_at,
        class_count=len(document.classes),
        relationship_count=len(document.relationships),
        node_count=len(activity.nodes) if activity is not None else 0,
        class_boxes=[
            ClassBoxSummary(x=pos.x, y=pos.y, width=size.width, height=size.height)
            for pos, size in shapes
        ],
    )


async def list_projects(
    current_user: User,
    db: Session,
    search: str,
    sort: str,
    limit: int,
    offset: int,
    project_type: ProjectType | None,
) -> ProjectListResponse:
    projects, total = project_service.list_projects(
        db,
        current_user.id,
        search=search,
        sort=sort,
        limit=limit,
        offset=offset,
        project_type=project_type,
    )
    return ProjectListResponse(
        projects=[_to_summary(p) for p in projects], total=total, limit=limit, offset=offset
    )


async def create_project(
    request: CreateProjectRequest, current_user: User, db: Session
) -> ProjectResponse:
    try:
        project = project_service.create_project(
            db,
            current_user.id,
            request.name,
            request.document,
            request.activity_document,
            request.code_inputs,
            request.project_type,
        )
    except ProjectNameTakenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
            db,
            current_user.id,
            project_id,
            request.name,
            request.document,
            request.activity_document,
            request.code_inputs,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProjectNameTakenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
