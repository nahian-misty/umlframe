from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from backend.reverse.java import parser as java_parser
from backend.reverse.javascript import parser as javascript_parser
from backend.reverse.python import parser as python_parser
from backend.schemas.activity import ActivityDocument
from backend.schemas.uml import UmlDocument


@dataclass(frozen=True)
class ReverseLanguageConfig:
    parse: Callable[[str], UmlDocument]
    extract_control_flow: Callable[[str, str, str], ActivityDocument]


REGISTRY: dict[str, ReverseLanguageConfig] = {
    "python": ReverseLanguageConfig(
        parse=python_parser.parse, extract_control_flow=python_parser.extract_control_flow
    ),
    "java": ReverseLanguageConfig(
        parse=java_parser.parse, extract_control_flow=java_parser.extract_control_flow
    ),
    "javascript": ReverseLanguageConfig(
        parse=javascript_parser.parse, extract_control_flow=javascript_parser.extract_control_flow
    ),
}

SUPPORTED_LANGUAGES = list(REGISTRY.keys())
