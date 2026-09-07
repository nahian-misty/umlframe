from __future__ import annotations

from backend.mermaid.activity_diagram import document_to_activity_diagram
from backend.mermaid.class_diagram import document_to_class_diagram
from backend.schemas.activity import ActivityDocument
from backend.schemas.uml import UmlDocument


def document_to_mermaid(document: UmlDocument) -> str:
    """Sequences schemas/ -> mermaid/ for the class-diagram direction."""
    return document_to_class_diagram(document)


def activity_to_mermaid(document: ActivityDocument) -> str:
    """Sequences schemas/ -> mermaid/ for the activity-diagram direction."""
    return document_to_activity_diagram(document)
