from __future__ import annotations

from backend.reverse.registry import REGISTRY, SUPPORTED_LANGUAGES
from backend.schemas.activity import ActivityDocument, MethodControlFlow
from backend.schemas.uml import UmlDocument


def source_to_document(source: str, language: str, filename: str = "") -> UmlDocument:
    if language not in REGISTRY:
        raise ValueError(f"Unsupported language: '{language}'. Supported: {SUPPORTED_LANGUAGES}")
    if not source.strip():
        raise ValueError("Source code is empty.")
    return REGISTRY[language].parse(source)


def source_to_control_flow(source: str, language: str, class_name: str, method_name: str) -> ActivityDocument:
    if language not in REGISTRY:
        raise ValueError(f"Unsupported language: '{language}'. Supported: {SUPPORTED_LANGUAGES}")
    if not source.strip():
        raise ValueError("Source code is empty.")
    return REGISTRY[language].extract_control_flow(source, class_name, method_name)


def source_to_control_flows(source: str, language: str) -> list[MethodControlFlow]:
    """Control flow of every method found in `source`, so callers need not name one."""
    if language not in REGISTRY:
        raise ValueError(f"Unsupported language: '{language}'. Supported: {SUPPORTED_LANGUAGES}")
    if not source.strip():
        raise ValueError("Source code is empty.")
    config = REGISTRY[language]
    methods = config.list_methods(source)
    if not methods:
        raise ValueError("No methods found in the source.")

    results: list[MethodControlFlow] = []
    for class_name, method_name in methods:
        try:
            flow = config.extract_control_flow(source, class_name, method_name)
            results.append(MethodControlFlow(class_name=class_name, method_name=method_name, control_flow=flow))
        except ValueError as exc:
            results.append(MethodControlFlow(class_name=class_name, method_name=method_name, error=str(exc)))
    return results
