import httpx
import pytest

from backend.llm.openrouter_client import OpenRouterClient
from backend.llm.types import (
    ChatMessage,
    LlmNotConfiguredError,
    LlmRateLimitedError,
    LlmResponseError,
    LlmUpstreamError,
)

MESSAGES = [ChatMessage(role="user", content="hi")]
BASE_URL = "https://openrouter.test/api/v1"


def _client(handler, models=("free/a", "free/b"), api_key="sk-test") -> OpenRouterClient:
    return OpenRouterClient(
        api_key=api_key,
        models=models,
        base_url=BASE_URL,
        transport=httpx.MockTransport(handler),
    )


def _ok(content: str = "answer", model: str = "free/a") -> httpx.Response:
    return httpx.Response(200, json={"model": model, "choices": [{"message": {"content": content}}]})


def test_success_sends_bearer_key_model_and_messages():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = request.read()
        return _ok("hello")

    completion = _client(handler).complete(MESSAGES, max_tokens=123)

    assert completion.content == "hello"
    assert seen["url"] == f"{BASE_URL}/chat/completions"
    assert seen["auth"] == "Bearer sk-test"
    assert b'"model":"free/a"' in seen["body"].replace(b" ", b"")
    assert b'"max_tokens":123' in seen["body"].replace(b" ", b"")


def test_rate_limited_model_falls_back_to_the_next_one():
    def handler(request: httpx.Request) -> httpx.Response:
        model = request.read().decode()
        return httpx.Response(429) if "free/a" in model else _ok("from b", "free/b")

    completion = _client(handler).complete(MESSAGES, max_tokens=10)

    assert (completion.content, completion.model) == ("from b", "free/b")


def test_every_model_rate_limited_raises_rate_limited():
    with pytest.raises(LlmRateLimitedError):
        _client(lambda request: httpx.Response(429)).complete(MESSAGES, max_tokens=10)


def test_every_model_failing_differently_raises_upstream():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429) if "free/a" in request.read().decode() else httpx.Response(500)

    with pytest.raises(LlmUpstreamError):
        _client(handler).complete(MESSAGES, max_tokens=10)


def test_timeout_moves_on_then_reports_upstream():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(LlmUpstreamError):
        _client(handler).complete(MESSAGES, max_tokens=10)


def test_rejected_key_is_reported_as_not_configured_without_trying_other_models():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.read().decode())
        return httpx.Response(401)

    with pytest.raises(LlmNotConfiguredError):
        _client(handler).complete(MESSAGES, max_tokens=10)
    assert len(calls) == 1


def test_provider_error_body_with_200_status_tries_the_next_model():
    def handler(request: httpx.Request) -> httpx.Response:
        if "free/a" in request.read().decode():
            return httpx.Response(200, json={"error": {"message": "overloaded"}})
        return _ok("b answers", "free/b")

    assert _client(handler).complete(MESSAGES, max_tokens=10).content == "b answers"


def test_unexpected_response_shape_raises_response_error():
    with pytest.raises(LlmResponseError):
        _client(lambda request: httpx.Response(200, json={"choices": []})).complete(
            MESSAGES, max_tokens=10
        )


def test_empty_reply_counts_as_a_failed_model():
    def handler(request: httpx.Request) -> httpx.Response:
        return _ok("   ") if "free/a" in request.read().decode() else _ok("real", "free/b")

    assert _client(handler).complete(MESSAGES, max_tokens=10).content == "real"


@pytest.mark.parametrize(("api_key", "models"), [("", ("free/a",)), ("sk-test", ())])
def test_missing_key_or_models_is_not_configured(api_key, models):
    client = _client(lambda request: _ok(), models=models, api_key=api_key)
    assert client.is_configured is False
    with pytest.raises(LlmNotConfiguredError):
        client.complete(MESSAGES, max_tokens=10)
