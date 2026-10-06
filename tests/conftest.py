import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.models import Base
from backend.db.session import get_db
from backend.main import app


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Not using TestClient as a context manager: that would trigger the app's
    # lifespan (init_db) against the real configured engine/sqlite file
    # instead of the in-memory test engine set up above.
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# LLM method implementation helpers (no real network)
# ---------------------------------------------------------------------------

from collections.abc import Callable  # noqa: E402

from backend.llm.types import ChatMessage, LlmCompletion  # noqa: E402
from backend.schemas.uml import (  # noqa: E402
    Attribute,
    Method,
    Parameter,
    Position,
    Size,
    UmlClass,
    UmlDocument,
    Visibility,
)


class FakeLlmClient:
    """Stands in for the OpenRouter client: replies come from a function (or fixed text) and
    every prompt is recorded; an Exception reply is raised instead of returned."""

    def __init__(
        self,
        reply: str | Exception | Callable[[list[ChatMessage]], str | Exception],
        configured: bool = True,
        model: str = "fake/model",
    ) -> None:
        self._reply = reply
        self._configured = configured
        self._model = model
        self.prompts: list[list[ChatMessage]] = []

    @property
    def is_configured(self) -> bool:
        return self._configured

    def complete(self, messages: list[ChatMessage], max_tokens: int) -> LlmCompletion:
        self.prompts.append(messages)
        reply = self._reply(messages) if callable(self._reply) else self._reply
        if isinstance(reply, Exception):
            raise reply
        return LlmCompletion(content=reply, model=self._model)


@pytest.fixture
def fake_llm():
    return FakeLlmClient


def _class(class_id: str, name: str, attributes=None, methods=None) -> UmlClass:
    return UmlClass(
        id=class_id,
        name=name,
        attributes=attributes or [],
        methods=methods or [],
        position=Position(x=0, y=0),
        size=Size(width=160, height=120),
    )


@pytest.fixture
def account_document() -> UmlDocument:
    """One Account class: a private balance, two concrete methods and one abstract one."""
    return UmlDocument(
        classes=[
            _class(
                "class_1",
                "Account",
                attributes=[Attribute(name="balance", datatype="int", visibility=Visibility.PRIVATE)],
                methods=[
                    Method(
                        name="deposit",
                        visibility=Visibility.PUBLIC,
                        parameters=[Parameter(name="amount", datatype="int")],
                        return_type="void",
                    ),
                    Method(
                        name="getBalance",
                        visibility=Visibility.PUBLIC,
                        parameters=[],
                        return_type="int",
                    ),
                    Method(
                        name="audit",
                        visibility=Visibility.PUBLIC,
                        parameters=[],
                        return_type="void",
                        abstract=True,
                    ),
                ],
            )
        ],
        relationships=[],
    )
