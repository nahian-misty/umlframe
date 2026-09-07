from __future__ import annotations

from backend.schemas.activity import ActivityDocument, ActivityNode, ActivityNodeType

# Mermaid flowchart node-shape delimiters per node type. Shares no code path
# with class_diagram.py beyond the module boundary -- a second, independent
# transformation living alongside it.
_NODE_SHAPE: dict[ActivityNodeType, tuple[str, str]] = {
    ActivityNodeType.START: ("((", "))"),
    ActivityNodeType.END: ("((", "))"),
    ActivityNodeType.ACTION: ("[", "]"),
    ActivityNodeType.DECISION: ("{", "}"),
    ActivityNodeType.FORK: ("[[", "]]"),
    ActivityNodeType.JOIN: ("[[", "]]"),
}

_DEFAULT_LABEL: dict[ActivityNodeType, str] = {
    ActivityNodeType.START: "Start",
    ActivityNodeType.END: "End",
    ActivityNodeType.FORK: "fork",
    ActivityNodeType.JOIN: "join",
}


def document_to_activity_diagram(document: ActivityDocument) -> str:
    """Pure transformation: ActivityDocument -> Mermaid `flowchart` syntax."""
    lines = ["flowchart TD"]
    for node in document.nodes:
        lines.append(f"    {_render_node(node)}")
    for edge in document.edges:
        arrow = f'-->|"{_escape(edge.label)}"|' if edge.label else "-->"
        lines.append(f"    {edge.source} {arrow} {edge.target}")
    return "\n".join(lines)


def _render_node(node: ActivityNode) -> str:
    open_token, close_token = _NODE_SHAPE[node.type]
    label = node.label or _DEFAULT_LABEL.get(node.type, "")
    return f'{node.id}{open_token}"{_escape(label)}"{close_token}'


def _escape(text: str) -> str:
    return text.replace('"', "'")
