from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LlmCompletion(BaseModel):
    content: str
    model: str


class LlmError(Exception):
    """Base class for every failure talking to the language model."""


class LlmNotConfiguredError(LlmError):
    """No API key or model configured, or the provider rejected the key."""


class LlmRateLimitedError(LlmError):
    """Every configured model answered 429 (common for free models)."""


class LlmUpstreamError(LlmError):
    """The provider was unreachable, timed out or returned an error."""


class LlmResponseError(LlmError):
    """The provider answered, but not in the expected shape."""


class LlmClient(Protocol):
    @property
    def is_configured(self) -> bool: ...

    def complete(self, messages: list[ChatMessage], max_tokens: int) -> LlmCompletion: ...
