from __future__ import annotations

from backend.mermaid.class_diagram import document_to_class_diagram
from backend.schemas.uml import UmlDocument


def document_to_mermaid(document: UmlDocument) -> str:
    """Sequences schemas/ -> mermaid/ for the class-diagram direction."""
    return document_to_class_diagram(document)
