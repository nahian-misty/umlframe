from __future__ import annotations

from backend.reverse.registry import REGISTRY, SUPPORTED_LANGUAGES
from backend.schemas.uml import UmlDocument


def source_to_document(source: str, language: str, filename: str = "") -> UmlDocument:
    if language not in REGISTRY:
        raise ValueError(f"Unsupported language: '{language}'. Supported: {SUPPORTED_LANGUAGES}")
    if not source.strip():
        raise ValueError("Source code is empty.")
    return REGISTRY[language].parse(source)
