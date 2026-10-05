import pytest
from sqlalchemy import create_engine, inspect, text

from backend.db.session import add_missing_project_columns
from backend.models.project_state import CodeInputs, CodeToUmlInput
from backend.schemas.activity import (
    ActivityDocument,
    ActivityEdge,
    ActivityNode,
    ActivityNodeType,
)
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

    alice_projects, total = project_service.list_projects(db_session, alice.id)
    assert [p.name for p in alice_projects] == ["Alice Project"]
    assert total == 1


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


def _sample_activity() -> ActivityDocument:
    return ActivityDocument(
        nodes=[
            ActivityNode(
                id="node_1",
                type=ActivityNodeType.START,
                position=Position(x=0, y=0),
                size=Size(width=40, height=40),
            ),
            ActivityNode(
                id="node_2",
                type=ActivityNodeType.END,
                position=Position(x=0, y=100),
                size=Size(width=40, height=40),
            ),
        ],
        edges=[ActivityEdge(id="edge_1", source="node_1", target="node_2")],
    )


def test_project_without_activity_document_has_none(db_session):
    user = _make_user(db_session, "alice@example.com")
    project = project_service.create_project(db_session, user.id, "P", None)
    assert project.activity_document is None


def test_create_project_with_activity_document_round_trips(db_session):
    user = _make_user(db_session, "alice@example.com")
    project = project_service.create_project(db_session, user.id, "P", None, _sample_activity())
    fetched = project_service.get_project(db_session, user.id, project.id)
    assert fetched.activity_document is not None
    assert ActivityDocument.model_validate_json(fetched.activity_document) == _sample_activity()


def test_update_project_sets_activity_document_and_keeps_it_when_omitted(db_session):
    user = _make_user(db_session, "alice@example.com")
    project = project_service.create_project(db_session, user.id, "P", None)
    project_service.update_project(db_session, user.id, project.id, None, None, _sample_activity())
    renamed = project_service.update_project(db_session, user.id, project.id, "Q", None)
    assert renamed.name == "Q"
    assert renamed.activity_document is not None


def test_add_missing_project_columns_upgrades_old_schema():
    old_engine = create_engine("sqlite://")
    with old_engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects (id INTEGER PRIMARY KEY, document TEXT)"))
    add_missing_project_columns(old_engine)
    add_missing_project_columns(old_engine)
    columns = {column["name"] for column in inspect(old_engine).get_columns("projects")}
    assert {"activity_document", "code_inputs", "project_type"} <= columns


def test_old_schema_backfill_marks_activity_only_projects_as_activity():
    old_engine = create_engine("sqlite://")
    empty = '{"classes": [], "relationships": []}'
    with old_engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE projects (id INTEGER PRIMARY KEY, document TEXT, activity_document TEXT)")
        )
        for project_id, document, activity in [
            (1, empty, None),  # plain UML project
            (2, empty, '{"nodes": [], "edges": []}'),  # activity only
            (3, '{"classes": [{"id": "class_1"}], "relationships": []}', '{"nodes": [], "edges": []}'),
        ]:
            connection.execute(
                text("INSERT INTO projects VALUES (:id, :d, :a)"),
                {"id": project_id, "d": document, "a": activity},
            )
    add_missing_project_columns(old_engine)
    with old_engine.connect() as connection:
        types = dict(connection.execute(text("SELECT id, project_type FROM projects")).all())
    assert types == {1: "uml", 2: "activity", 3: "uml"}


def test_projects_default_to_uml_and_can_be_filtered_by_type(db_session):
    user = _make_user(db_session, "alice@example.com")
    project_service.create_project(db_session, user.id, "Classes", None)
    project_service.create_project(db_session, user.id, "Flow", None, project_type="activity")

    assert project_service.get_project(db_session, user.id, 1).project_type == "uml"
    uml, uml_total = project_service.list_projects(db_session, user.id, project_type="uml")
    activity, activity_total = project_service.list_projects(
        db_session, user.id, project_type="activity"
    )
    everything, all_total = project_service.list_projects(db_session, user.id)
    assert ([p.name for p in uml], uml_total) == (["Classes"], 1)
    assert ([p.name for p in activity], activity_total) == (["Flow"], 1)
    assert all_total == 2 and len(everything) == 2


def _seed_named_projects(db_session, user_id: int, names: list[str]) -> None:
    for name in names:
        project_service.create_project(db_session, user_id, name, None)


def test_list_projects_search_is_case_insensitive_substring(db_session):
    user = _make_user(db_session, "alice@example.com")
    _seed_named_projects(db_session, user.id, ["Billing API", "Order Service", "billing ui"])
    found, total = project_service.list_projects(db_session, user.id, search="BILL", sort="name")
    assert [p.name for p in found] == ["Billing API", "billing ui"]
    assert total == 2


def test_list_projects_search_treats_like_wildcards_literally(db_session):
    user = _make_user(db_session, "alice@example.com")
    _seed_named_projects(db_session, user.id, ["100% done", "plain", "a_b"])
    assert project_service.list_projects(db_session, user.id, search="%")[1] == 1
    assert [p.name for p in project_service.list_projects(db_session, user.id, search="_")[0]] == [
        "a_b"
    ]


def test_list_projects_paginates_by_offset_and_reports_total(db_session):
    user = _make_user(db_session, "alice@example.com")
    _seed_named_projects(db_session, user.id, [f"P{i}" for i in range(5)])
    first, total = project_service.list_projects(db_session, user.id, sort="name", limit=2)
    second, _ = project_service.list_projects(db_session, user.id, sort="name", limit=2, offset=2)
    last, _ = project_service.list_projects(db_session, user.id, sort="name", limit=2, offset=4)
    assert total == 5
    assert [p.name for p in first] == ["P0", "P1"]
    assert [p.name for p in second] == ["P2", "P3"]
    assert [p.name for p in last] == ["P4"]


def test_code_inputs_round_trip_and_survive_unrelated_update(db_session):
    user = _make_user(db_session, "alice@example.com")
    project = project_service.create_project(db_session, user.id, "P", None)
    assert project.code_inputs is None
    inputs = CodeInputs(code_to_uml=CodeToUmlInput(language="java", source="class A {}"))
    saved = project_service.update_project(db_session, user.id, project.id, None, None, None, inputs)
    assert CodeInputs.model_validate_json(saved.code_inputs) == inputs
    renamed = project_service.update_project(db_session, user.id, project.id, "Q", None)
    assert CodeInputs.model_validate_json(renamed.code_inputs) == inputs


def test_add_missing_user_columns_upgrades_old_schema():
    from backend.db.session import add_missing_user_columns

    old_engine = create_engine("sqlite://")
    with old_engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)"))
    add_missing_user_columns(old_engine)
    add_missing_user_columns(old_engine)
    columns = {column["name"] for column in inspect(old_engine).get_columns("users")}
    assert "password_changed_at" in columns
