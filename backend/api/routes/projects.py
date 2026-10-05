from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.controllers import project_controller
from backend.api.dependencies.auth import get_current_user
from backend.db.models import User
from backend.db.session import get_db
from backend.models.project_state import ProjectType
from backend.models.requests import CreateProjectRequest, UpdateProjectRequest
from backend.models.responses import ProjectListResponse, ProjectResponse

DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 100

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    search: str = Query("", max_length=255),
    sort: Literal["updated", "name"] = "updated",
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    project_type: ProjectType | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    return await project_controller.list_projects(
        current_user, db, search, sort, limit, offset, project_type
    )


@router.post("", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    return await project_controller.create_project(request, current_user, db)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    return await project_controller.get_project(project_id, current_user, db)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    request: UpdateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    return await project_controller.update_project(project_id, request, current_user, db)


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    return await project_controller.delete_project(project_id, current_user, db)
