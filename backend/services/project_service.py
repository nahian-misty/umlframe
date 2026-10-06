from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db.models import Project
from backend.models.project_state import DEFAULT_PROJECT_TYPE, CodeInputs, ProjectType
from backend.schemas.activity import ActivityDocument
from backend.schemas.uml import UmlDocument

EMPTY_DOCUMENT = UmlDocument()

SORT_UPDATED = "updated"
SORT_NAME = "name"
LIKE_ESCAPE = "\\"


class ProjectNotFoundError(ValueError):
    pass


class ProjectNameTakenError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_owned_project(db: Session, user_id: int, project_id: int) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user_id)
        .first()
    )
    if project is None:
        raise ProjectNotFoundError(f"Project '{project_id}' not found")
    return project


def _ensure_name_available(
    db: Session, user_id: int, name: str, exclude_project_id: int | None = None
) -> None:
    """A user's project names are unique, ignoring case and surrounding whitespace."""
    query = db.query(Project.id).filter(
        Project.owner_id == user_id,
        func.lower(func.trim(Project.name)) == name.strip().lower(),
    )
    if exclude_project_id is not None:
        query = query.filter(Project.id != exclude_project_id)
    if query.first() is not None:
        raise ProjectNameTakenError(f"You already have a project named '{name.strip()}'")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _escape_like(term: str) -> str:
    return (
        term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", f"{LIKE_ESCAPE}%")
        .replace("_", f"{LIKE_ESCAPE}_")
    )


def list_projects(
    db: Session,
    user_id: int,
    search: str = "",
    sort: str = SORT_UPDATED,
    limit: int = 12,
    offset: int = 0,
    project_type: ProjectType | None = None,
) -> tuple[list[Project], int]:
    """One page of the user's projects plus the total number matching the filters."""
    query = db.query(Project).filter(Project.owner_id == user_id)
    if project_type is not None:
        query = query.filter(Project.project_type == project_type)
    term = search.strip()
    if term:
        pattern = f"%{_escape_like(term.lower())}%"
        query = query.filter(func.lower(Project.name).like(pattern, escape=LIKE_ESCAPE))
    total = query.count()
    if sort == SORT_NAME:
        order = (func.lower(Project.name).asc(), Project.id.asc())
    else:
        order = (Project.updated_at.desc(), Project.id.desc())
    return query.order_by(*order).offset(offset).limit(limit).all(), total


def create_project(
    db: Session,
    user_id: int,
    name: str,
    document: UmlDocument | None,
    activity_document: ActivityDocument | None = None,
    code_inputs: CodeInputs | None = None,
    project_type: ProjectType = DEFAULT_PROJECT_TYPE,
) -> Project:
    _ensure_name_available(db, user_id, name)
    doc = document if document is not None else EMPTY_DOCUMENT
    project = Project(
        name=name,
        project_type=project_type,
        document=doc.model_dump_json(),
        activity_document=(
            activity_document.model_dump_json() if activity_document is not None else None
        ),
        code_inputs=code_inputs.model_dump_json() if code_inputs is not None else None,
        owner_id=user_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, user_id: int, project_id: int) -> Project:
    return _get_owned_project(db, user_id, project_id)


def update_project(
    db: Session,
    user_id: int,
    project_id: int,
    name: str | None,
    document: UmlDocument | None,
    activity_document: ActivityDocument | None = None,
    code_inputs: CodeInputs | None = None,
) -> Project:
    project = _get_owned_project(db, user_id, project_id)
    if name is not None:
        _ensure_name_available(db, user_id, name, exclude_project_id=project_id)
        project.name = name
    if document is not None:
        project.document = document.model_dump_json()
    if activity_document is not None:
        project.activity_document = activity_document.model_dump_json()
    if code_inputs is not None:
        project.code_inputs = code_inputs.model_dump_json()
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, user_id: int, project_id: int) -> None:
    project = _get_owned_project(db, user_id, project_id)
    db.delete(project)
    db.commit()
