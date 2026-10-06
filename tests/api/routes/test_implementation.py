import json

import pytest

from backend.api.dependencies.llm import get_llm_client
from backend.main import app


@pytest.fixture
def auth_headers(client):
    body = client.post(
        "/api/auth/register", json={"email": "alice@example.com", "password": "password123"}
    ).json()
    return {"Authorization": f"Bearer {body['access_token']}"}


@pytest.fixture
def use_llm(client):
    def install(fake):
        app.dependency_overrides[get_llm_client] = lambda: fake
        return fake

    yield install
    app.dependency_overrides.pop(get_llm_client, None)


def _payload(document, **extra) -> dict:
    return {"document": document.model_dump(mode="json"), "language": "python", **extra}


def test_implement_code_returns_files_and_what_was_implemented(
    client, auth_headers, use_llm, fake_llm, account_document
):
    reply = json.dumps(
        {"methods": {"Account.deposit": "self.__balance += amount", "Account.getBalance": "return 1"}}
    )
    use_llm(fake_llm(reply))

    resp = client.post(
        "/api/implement-code",
        json=_payload(account_document, instructions="plain arithmetic"),
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["implemented"] == ["Account.deposit", "Account.getBalance"]
    assert body["skipped"] == []
    assert body["models"] == ["fake/model"]
    assert "        self.__balance += amount\n" in body["files"]["Account.py"]


def test_requires_authentication(client, use_llm, fake_llm, account_document):
    use_llm(fake_llm("{}"))
    resp = client.post("/api/implement-code", json=_payload(account_document))
    assert resp.status_code in (401, 403)
    assert client.get("/api/implement-code/status").status_code in (401, 403)


def test_unconfigured_llm_returns_503(client, auth_headers, use_llm, fake_llm, account_document):
    use_llm(fake_llm("{}", configured=False))
    resp = client.post("/api/implement-code", json=_payload(account_document), headers=auth_headers)
    assert resp.status_code == 503


def test_validation_errors_return_422(client, auth_headers, use_llm, fake_llm, account_document):
    use_llm(fake_llm("{}"))
    bad_language = {**_payload(account_document), "language": "cobol"}
    too_long = _payload(account_document, instructions="x" * 2001)
    assert client.post("/api/implement-code", json=bad_language, headers=auth_headers).status_code == 422
    assert client.post("/api/implement-code", json=too_long, headers=auth_headers).status_code == 422


def test_status_endpoint(client, auth_headers, use_llm, fake_llm):
    use_llm(fake_llm("{}", configured=True))
    assert client.get("/api/implement-code/status", headers=auth_headers).json() == {"available": True}
    use_llm(fake_llm("{}", configured=False))
    assert client.get("/api/implement-code/status", headers=auth_headers).json() == {"available": False}
