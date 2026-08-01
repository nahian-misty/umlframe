from __future__ import annotations

from sqlalchemy.orm import Session

from backend.db.models import Project
from backend.schemas.uml import UmlDocument

EMPTY_DOCUMENT = UmlDocument()


class ProjectNotFoundError(ValueError):
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_projects(db: Session, user_id: int) -> list[Project]:
    return (
        db.query(Project)
        .filter(Project.owner_id == user_id)
        .order_by(Project.updated_at.desc())
        .all()
    )


def create_project(
    db: Session, user_id: int, name: str, document: UmlDocument | None
) -> Project:
    doc = document if document is not None else EMPTY_DOCUMENT
    project = Project(name=name, document=doc.model_dump_json(), owner_id=user_id)
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
) -> Project:
    project = _get_owned_project(db, user_id, project_id)
    if name is not None:
        project.name = name
    if document is not None:
        project.document = document.model_dump_json()
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, user_id: int, project_id: int) -> None:
    project = _get_owned_project(db, user_id, project_id)
    db.delete(project)
    db.commit()
