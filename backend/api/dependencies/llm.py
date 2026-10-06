from __future__ import annotations

from backend.llm.openrouter_client import build_client_from_settings
from backend.llm.types import LlmClient


def get_llm_client() -> LlmClient:
    """The configured language-model client; overridden with a fake in tests."""
    return build_client_from_settings()
