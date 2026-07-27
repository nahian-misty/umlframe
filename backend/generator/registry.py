from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.generator.language_maps import java, javascript, python

TEMPLATES_ROOT = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class LanguageConfig:
    type_map: dict[str, str]
    visibility_prefix: dict[str, str]
    visibility_keyword: dict[str, str]
    template_dir: str
    file_extension: str
    standard_imports: dict[str, str]


REGISTRY: dict[str, LanguageConfig] = {
    "python": LanguageConfig(
        type_map=python.TYPE_MAP,
        visibility_prefix=python.VISIBILITY_PREFIX,
        visibility_keyword=python.VISIBILITY_KEYWORD,
        template_dir=python.TEMPLATE_DIR,
        file_extension=python.FILE_EXTENSION,
        standard_imports={},
    ),
    "java": LanguageConfig(
        type_map=java.TYPE_MAP,
        visibility_prefix=java.VISIBILITY_PREFIX,
        visibility_keyword=java.VISIBILITY_KEYWORD,
        template_dir=java.TEMPLATE_DIR,
        file_extension=java.FILE_EXTENSION,
        standard_imports=java.STANDARD_IMPORTS,
    ),
    "javascript": LanguageConfig(
        type_map=javascript.TYPE_MAP,
        visibility_prefix=javascript.VISIBILITY_PREFIX,
        visibility_keyword=javascript.VISIBILITY_KEYWORD,
        template_dir=javascript.TEMPLATE_DIR,
        file_extension=javascript.FILE_EXTENSION,
        standard_imports={},
    ),
}

SUPPORTED_LANGUAGES = list(REGISTRY.keys())
