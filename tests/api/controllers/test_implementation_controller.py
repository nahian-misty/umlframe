import pytest
from fastapi import HTTPException

from backend.api.controllers import implementation_controller
from backend.llm.types import (
    LlmNotConfiguredError,
    LlmRateLimitedError,
    LlmResponseError,
    LlmUpstreamError,
)
from backend.models.requests import ImplementCodeRequest
from backend.services.implementation_service import ImplementationResult, SkippedMethod


def _request(document) -> ImplementCodeRequest:
    return ImplementCodeRequest(document=document, language="python", instructions="x")


async def test_success_maps_the_service_result(account_document, fake_llm, monkeypatch):
    result = ImplementationResult(
        files={"Account.py": "code"},
        implemented=["Account.deposit"],
        skipped=[SkippedMethod(key="Account.getBalance", reason="no body")],
        models=["m"],
    )
    monkeypatch.setattr(
        implementation_controller.implementation_service, "implement_code", lambda *a: result
    )

    response = await implementation_controller.implement_code(_request(account_document), fake_llm(""))

    assert response.files == {"Account.py": "code"}
    assert response.implemented == ["Account.deposit"]
    assert (response.skipped[0].key, response.skipped[0].reason) == ("Account.getBalance", "no body")
    assert response.models == ["m"]


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (LlmNotConfiguredError("no key"), 503),
        (LlmRateLimitedError("slow"), 429),
        (LlmUpstreamError("down"), 502),
        (LlmResponseError("odd"), 502),
        (ValueError("too many classes"), 422),
        (RuntimeError("boom"), 500),
    ],
)
async def test_errors_map_to_http_statuses(account_document, fake_llm, monkeypatch, error, status):
    def raise_error(*args):
        raise error

    monkeypatch.setattr(
        implementation_controller.implementation_service, "implement_code", raise_error
    )

    with pytest.raises(HTTPException) as caught:
        await implementation_controller.implement_code(_request(account_document), fake_llm(""))

    assert caught.value.status_code == status
    if status == 500:
        assert "boom" not in caught.value.detail  # never leak internals


async def test_status_reports_whether_the_client_is_configured(fake_llm):
    assert (await implementation_controller.implement_status(fake_llm("", configured=True))).available
    assert not (
        await implementation_controller.implement_status(fake_llm("", configured=False))
    ).available
