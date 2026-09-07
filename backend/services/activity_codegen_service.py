from __future__ import annotations

from pathlib import Path

import jinja2

from backend.generator import registry as reg
from backend.schemas.activity import ActivityDocument
from backend.services.activity_structuring import (
    IRAction,
    IRIf,
    IRNode,
    IRWhile,
    structure_activity,
)

TEMPLATES_ROOT = Path(__file__).parent.parent / "generator" / "templates"


def _ir_to_context(nodes: list[IRNode]) -> list[dict[str, object]]:
    context: list[dict[str, object]] = []
    for node in nodes:
        if isinstance(node, IRAction):
            context.append({"kind": "action", "label": node.label})
        elif isinstance(node, IRIf):
            context.append(
                {
                    "kind": "if",
                    "label": node.condition_label,
                    "then": _ir_to_context(node.then_body),
                    "else": _ir_to_context(node.else_body),
                }
            )
        elif isinstance(node, IRWhile):
            context.append({"kind": "while", "label": node.condition_label, "body": _ir_to_context(node.body)})
    return context


def generate_activity_code(document: ActivityDocument, language: str, function_name: str = "generated_function") -> dict[str, str]:
    if language not in reg.REGISTRY:
        raise ValueError(f"Unsupported language: '{language}'. Supported: {reg.SUPPORTED_LANGUAGES}")

    ir = structure_activity(document)
    config = reg.REGISTRY[language]
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_ROOT / config.template_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = env.get_template("activity.j2")
    content = template.render(function_name=function_name, body=_ir_to_context(ir))

    filename = function_name + config.file_extension
    return {filename: content}
