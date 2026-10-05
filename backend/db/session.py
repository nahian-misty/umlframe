from __future__ import annotations

import json
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.db.models import Base

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def add_missing_project_columns(bind: Engine) -> None:
    """Add columns introduced after a database was first created (create_all never alters)."""
    existing = {column["name"] for column in inspect(bind).get_columns("projects")}
    for column_name in ("activity_document", "code_inputs"):
        if column_name not in existing:
            with bind.begin() as connection:
                connection.execute(text(f"ALTER TABLE projects ADD COLUMN {column_name} TEXT"))
    if "project_type" not in existing:
        with bind.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE projects ADD COLUMN project_type VARCHAR(16) "
                    "NOT NULL DEFAULT 'uml'"
                )
            )
        backfill_project_types(bind)


def add_missing_user_columns(bind: Engine) -> None:
    """Add user columns introduced after a database was first created."""
    existing = {column["name"] for column in inspect(bind).get_columns("users")}
    if "password_changed_at" not in existing:
        with bind.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_changed_at DATETIME"))


def backfill_project_types(bind: Engine) -> None:
    """Existing projects predate project types: one that only ever held an activity diagram
    (an activity document and no classes) is an activity project, everything else stays UML."""
    with bind.begin() as connection:
        rows = connection.execute(
            text("SELECT id, document FROM projects WHERE activity_document IS NOT NULL")
        ).all()
        for project_id, document in rows:
            if not json.loads(document).get("classes"):
                connection.execute(
                    text("UPDATE projects SET project_type = 'activity' WHERE id = :id"),
                    {"id": project_id},
                )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    add_missing_project_columns(engine)
    add_missing_user_columns(engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
