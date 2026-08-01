import pytest

from backend.schemas.uml import Position, Size, UmlClass, UmlDocument
from backend.services import auth_service, project_service
from backend.services.project_service import ProjectNotFoundError


def _make_user(db_session, email: str):
    return auth_service.register_user(db_session, email, "password123")


def _sample_document() -> UmlDocument:
    return UmlDocument(
        classes=[
            UmlClass(
                id="class_1",
                name="User",
                position=Position(x=0, y=0),
                size=Size(width=160, height=120),
            )
        ],
        relationships=[],
    )


def test_create_project_defaults_to_empty_document(db_session):
    user = _make_user(db_session, "alice@example.com")
    project = project_service.create_project(db_session, user.id, "My Project", None)
    assert project.id is not None
    assert project.name == "My Project"


def test_create_project_with_document(db_session):
    user = _make_user(db_session, "alice@example.com")
    project = project_service.create_project(db_session, user.id, "My Project", _sample_document())
    fetched = project_service.get_project(db_session, user.id, project.id)
    assert fetched.name == "My Project"


def test_list_projects_scoped_to_owner(db_session):
    alice = _make_user(db_session, "alice@example.com")
    bob = _make_user(db_session, "bob@example.com")
    project_service.create_project(db_session, alice.id, "Alice Project", None)
    project_service.create_project(db_session, bob.id, "Bob Project", None)

    alice_projects = project_service.list_projects(db_session, alice.id)
    assert [p.name for p in alice_projects] == ["Alice Project"]


def test_get_project_not_found_raises(db_session):
    user = _make_user(db_session, "alice@example.com")
    with pytest.raises(ProjectNotFoundError):
        project_service.get_project(db_session, user.id, 999999)


def test_get_other_users_project_raises_not_found(db_session):
    alice = _make_user(db_session, "alice@example.com")
    bob = _make_user(db_session, "bob@example.com")
    project = project_service.create_project(db_session, alice.id, "Alice Project", None)

    with pytest.raises(ProjectNotFoundError):
        project_service.get_project(db_session, bob.id, project.id)


def test_update_project_name_and_document(db_session):
    user = _make_user(db_session, "alice@example.com")
    project = project_service.create_project(db_session, user.id, "Old Name", None)

    updated = project_service.update_project(
        db_session, user.id, project.id, "New Name", _sample_document()
    )
    assert updated.name == "New Name"


def test_update_other_users_project_raises_not_found(db_session):
    alice = _make_user(db_session, "alice@example.com")
    bob = _make_user(db_session, "bob@example.com")
    project = project_service.create_project(db_session, alice.id, "Alice Project", None)

    with pytest.raises(ProjectNotFoundError):
        project_service.update_project(db_session, bob.id, project.id, "Hacked", None)


def test_delete_project(db_session):
    user = _make_user(db_session, "alice@example.com")
    project = project_service.create_project(db_session, user.id, "To Delete", None)

    project_service.delete_project(db_session, user.id, project.id)

    with pytest.raises(ProjectNotFoundError):
        project_service.get_project(db_session, user.id, project.id)


def test_delete_other_users_project_raises_not_found(db_session):
    alice = _make_user(db_session, "alice@example.com")
    bob = _make_user(db_session, "bob@example.com")
    project = project_service.create_project(db_session, alice.id, "Alice Project", None)

    with pytest.raises(ProjectNotFoundError):
        project_service.delete_project(db_session, bob.id, project.id)
