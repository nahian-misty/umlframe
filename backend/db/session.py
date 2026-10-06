from __future__ import annotations

import json
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.db.models import Base
from backend.db.usernames import derive_username

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

USERNAME_INDEX_NAME = "ix_users_username"


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
    if "username" not in existing:
        with bind.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(30)"))
        backfill_usernames(bind)
    if USERNAME_INDEX_NAME not in {i["name"] for i in inspect(bind).get_indexes("users")}:
        with bind.begin() as connection:
            connection.execute(text(f"CREATE UNIQUE INDEX {USERNAME_INDEX_NAME} ON users (username)"))


def backfill_usernames(bind: Engine) -> None:
    """Existing accounts predate usernames: derive each one from its email."""
    with bind.begin() as connection:
        rows = connection.execute(text("SELECT id, email FROM users ORDER BY id")).all()
        taken: set[str] = set()
        for user_id, email in rows:
            username = derive_username(email, taken)
            taken.add(username.lower())
            connection.execute(
                text("UPDATE users SET username = :username WHERE id = :id"),
                {"username": username, "id": user_id},
            )


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
