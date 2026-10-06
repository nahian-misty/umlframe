from __future__ import annotations

import httpx

from backend.config import settings
from backend.llm.types import (
    ChatMessage,
    LlmCompletion,
    LlmNotConfiguredError,
    LlmRateLimitedError,
    LlmResponseError,
    LlmUpstreamError,
)

REQUEST_TIMEOUT_SECONDS = 60.0
TEMPERATURE = 0.2
APP_TITLE = "UMLFrame"
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_RATE_LIMITED = 429


class OpenRouterClient:
    """Minimal OpenRouter chat-completions client that walks a list of models in order,
    moving on when one is rate-limited, missing, erroring or timing out."""

    def __init__(
        self,
        api_key: str,
        models: tuple[str, ...],
        base_url: str,
        transport: httpx.BaseTransport | None = None,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._api_key = api_key
        self._models = models
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key) and bool(self._models)

    def complete(self, messages: list[ChatMessage], max_tokens: int) -> LlmCompletion:
        if not self.is_configured:
            raise LlmNotConfiguredError(
                "The LLM is not configured: set OPENROUTER_API_KEY and OPENROUTER_MODELS."
            )
        last_error: Exception | None = None
        rate_limited = 0
        with httpx.Client(transport=self._transport, timeout=self._timeout) as http:
            for model in self._models:
                try:
                    return self._request(http, model, messages, max_tokens)
                except _TryNextModelError as exc:
                    last_error = exc
                    rate_limited += exc.status == HTTP_RATE_LIMITED
        if rate_limited == len(self._models):
            raise LlmRateLimitedError("Every configured model is rate-limited; try again shortly.")
        raise LlmUpstreamError(f"No model could answer: {last_error}")

    def _request(
        self, http: httpx.Client, model: str, messages: list[ChatMessage], max_tokens: int
    ) -> LlmCompletion:
        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "max_tokens": max_tokens,
            "temperature": TEMPERATURE,
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "X-Title": APP_TITLE}
        try:
            response = http.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise _TryNextModelError(f"{model}: {type(exc).__name__}") from exc

        if response.status_code in (HTTP_UNAUTHORIZED, HTTP_FORBIDDEN):
            raise LlmNotConfiguredError("OpenRouter rejected the API key.")
        if response.status_code != httpx.codes.OK:
            raise _TryNextModelError(f"{model}: HTTP {response.status_code}", response.status_code)
        return self._read_completion(response, model)

    @staticmethod
    def _read_completion(response: httpx.Response, model: str) -> LlmCompletion:
        try:
            body = response.json()
        except ValueError as exc:
            raise _TryNextModelError(f"{model}: reply was not JSON") from exc
        if not isinstance(body, dict) or "error" in body:
            raise _TryNextModelError(f"{model}: provider reported an error")
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmResponseError(f"{model}: unexpected response shape") from exc
        if not isinstance(content, str) or not content.strip():
            raise _TryNextModelError(f"{model}: empty reply")
        return LlmCompletion(content=content, model=str(body.get("model") or model))


class _TryNextModelError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def build_client_from_settings() -> OpenRouterClient:
    return OpenRouterClient(
        api_key=settings.openrouter_api_key,
        models=settings.openrouter_models,
        base_url=settings.openrouter_base_url,
    )
